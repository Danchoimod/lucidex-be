#!/usr/bin/env bash
set -Eeuo pipefail

# Lucidex one-file deployment helper
#
# Run with Git Bash, WSL, Linux, macOS, or Google Cloud Shell.
# Do not run directly in Windows PowerShell.
#
# Examples:
#   ./lucidex-deploy.sh setup
#   ./lucidex-deploy.sh check
#   ./lucidex-deploy.sh build
#   ./lucidex-deploy.sh staging 1 2
#   ./lucidex-deploy.sh production 1 1
#
# Optional environment overrides:
#   PROJECT_ID=lucidex-502504
#   REGION=asia-southeast1
#   REPOSITORY=lucidex

PROJECT_ID="${PROJECT_ID:-lucidex-502504}"
REGION="${REGION:-asia-southeast1}"
REPOSITORY="${REPOSITORY:-lucidex}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
DEPLOY_DIR="$BACKEND_DIR/deploy"

LAST_IMAGE_FILE="$DEPLOY_DIR/.last-image"
STAGING_IMAGE_FILE="$DEPLOY_DIR/.staging-image"

STAGING_SERVICE="lucidex-api-staging"
PRODUCTION_SERVICE="lucidex-api-production"

STAGING_SA="lucidex-api-staging@${PROJECT_ID}.iam.gserviceaccount.com"
PRODUCTION_SA="lucidex-api-production@${PROJECT_ID}.iam.gserviceaccount.com"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

require_file() {
  [[ -f "$1" ]] || die "Missing file: $1"
}

confirm() {
  local prompt="$1"
  read -r -p "$prompt [y/N]: " answer
  [[ "$answer" =~ ^[Yy]$ ]]
}

check_tools() {
  require_command git
  require_command gcloud
}

setup_gcp() {
  check_tools

  echo "Project: $PROJECT_ID"
  echo "Region:  $REGION"

  gcloud config set project "$PROJECT_ID"
  gcloud config set run/region "$REGION"

  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project="$PROJECT_ID"

  if ! gcloud artifacts repositories describe "$REPOSITORY" \
      --location="$REGION" \
      --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud artifacts repositories create "$REPOSITORY" \
      --repository-format=docker \
      --location="$REGION" \
      --description="Lucidex backend images" \
      --project="$PROJECT_ID"
  else
    echo "Artifact Registry already exists: $REPOSITORY"
  fi

  for account in lucidex-api-staging lucidex-api-production; do
    email="${account}@${PROJECT_ID}.iam.gserviceaccount.com"

    if ! gcloud iam service-accounts describe "$email" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
      gcloud iam service-accounts create "$account" \
        --display-name="$account" \
        --project="$PROJECT_ID"
    else
      echo "Service account already exists: $email"
    fi
  done

  cat <<EOF

Google Cloud base setup completed.

Create these secrets manually in Secret Manager:
  lucidex-staging-mongodb-uri
  lucidex-staging-jwt-secret
  lucidex-production-mongodb-uri
  lucidex-production-jwt-secret

Then grant secretAccessor to the matching service account.
EOF
}

quality_check() {
  require_command uv

  cd "$BACKEND_DIR"

  uv run ruff check app scripts tests
  uv run pytest

  echo "Quality checks passed."
}

build_image() {
  check_tools

  cd "$ROOT_DIR"

  if [[ -n "$(git status --porcelain)" ]]; then
    die "Git working tree is not clean. Commit or stash changes before building."
  fi

  local commit_sha
  commit_sha="$(git rev-parse --short HEAD)"

  local image
  image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/api:${commit_sha}"

  echo "Building image:"
  echo "$image"

  gcloud builds submit "$BACKEND_DIR" \
    --tag="$image" \
    --project="$PROJECT_ID" \
    --region="$REGION"

  printf '%s' "$image" > "$LAST_IMAGE_FILE"

  echo "Build completed."
  echo "Saved image to: $LAST_IMAGE_FILE"
}

validate_env_file() {
  local env_file="$1"
  require_file "$env_file"

  if grep -Eq 'example\.com|<[^>]+>' "$env_file"; then
    die "Environment file still contains placeholder values: $env_file"
  fi
}

deploy_staging() {
  check_tools
  require_command curl

  local mongo_version="${1:-}"
  local jwt_version="${2:-}"

  [[ "$mongo_version" =~ ^[0-9]+$ ]] || die "Mongo secret version must be numeric."
  [[ "$jwt_version" =~ ^[0-9]+$ ]] || die "JWT secret version must be numeric."

  require_file "$LAST_IMAGE_FILE"

  local image
  image="$(tr -d '\r\n' < "$LAST_IMAGE_FILE")"

  local env_file="$DEPLOY_DIR/staging.env.yaml"
  validate_env_file "$env_file"

  gcloud run deploy "$STAGING_SERVICE" \
    --image="$image" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --allow-unauthenticated \
    --service-account="$STAGING_SA" \
    --env-vars-file="$env_file" \
    --set-secrets="MONGODB_URI=lucidex-staging-mongodb-uri:${mongo_version},JWT_SECRET_KEY=lucidex-staging-jwt-secret:${jwt_version}" \
    --cpu=1 \
    --memory=512Mi \
    --max-instances=3 \
    --concurrency=20

  local url
  url="$(gcloud run services describe "$STAGING_SERVICE" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format='value(status.url)')"

  curl --fail --silent --show-error "$url/health" >/dev/null

  printf '%s' "$image" > "$STAGING_IMAGE_FILE"

  echo "Staging deployment healthy."
  echo "API:     $url"
  echo "Swagger: $url/docs"
  echo "OpenAPI: $url/openapi.json"
}

deploy_production() {
  check_tools
  require_command curl

  local mongo_version="${1:-}"
  local jwt_version="${2:-}"

  [[ "$mongo_version" =~ ^[0-9]+$ ]] || die "Mongo secret version must be numeric."
  [[ "$jwt_version" =~ ^[0-9]+$ ]] || die "JWT secret version must be numeric."

  require_file "$STAGING_IMAGE_FILE"

  local image
  image="$(tr -d '\r\n' < "$STAGING_IMAGE_FILE")"

  [[ "$image" != *"-dirty-"* ]] || die "Dirty image cannot be deployed to production."

  local env_file="$DEPLOY_DIR/production.env.yaml"
  validate_env_file "$env_file"

  echo "Production image:"
  echo "$image"

  confirm "Deploy this staging-tested image to production?" || die "Production deployment cancelled."

  gcloud run deploy "$PRODUCTION_SERVICE" \
    --image="$image" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --allow-unauthenticated \
    --service-account="$PRODUCTION_SA" \
    --env-vars-file="$env_file" \
    --set-secrets="MONGODB_URI=lucidex-production-mongodb-uri:${mongo_version},JWT_SECRET_KEY=lucidex-production-jwt-secret:${jwt_version}" \
    --cpu=1 \
    --memory=512Mi \
    --max-instances=3 \
    --concurrency=20

  local url
  url="$(gcloud run services describe "$PRODUCTION_SERVICE" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format='value(status.url)')"

  curl --fail --silent --show-error "$url/health" >/dev/null

  echo "Production deployment healthy."
  echo "API:     $url"
  echo "Swagger: $url/docs"
  echo "OpenAPI: $url/openapi.json"
}

show_logs() {
  check_tools

  local environment="${1:-staging}"
  local service="$STAGING_SERVICE"

  if [[ "$environment" == "production" ]]; then
    service="$PRODUCTION_SERVICE"
  fi

  gcloud run services logs read "$service" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --limit=100
}

usage() {
  cat <<EOF
Usage:
  $0 setup
  $0 check
  $0 build
  $0 staging <mongo-secret-version> <jwt-secret-version>
  $0 production <mongo-secret-version> <jwt-secret-version>
  $0 logs [staging|production]

Examples:
  $0 setup
  $0 check
  $0 build
  $0 staging 1 2
  $0 production 1 1
  $0 logs staging
EOF
}

main() {
  local command="${1:-}"
  shift || true

  case "$command" in
    setup)
      setup_gcp
      ;;
    check)
      quality_check
      ;;
    build)
      build_image
      ;;
    staging)
      deploy_staging "$@"
      ;;
    production)
      deploy_production "$@"
      ;;
    logs)
      show_logs "$@"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
