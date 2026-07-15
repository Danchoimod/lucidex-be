param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^\d+$")]
    [string]$MongoSecretVersion,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^\d+$")]
    [string]$JwtSecretVersion,

    [string]$Region = "asia-southeast1",

    [string]$Image
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI is not installed or is not available in PATH."
}

$ActiveAccount = (
    & gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null |
    Select-Object -First 1
)
if (-not $ActiveAccount) {
    throw "Google Cloud CLI is not authenticated. Run 'gcloud auth login'."
}

$LastImageFile = Join-Path $PSScriptRoot ".last-image"
if (-not $Image) {
    if (-not (Test-Path -LiteralPath $LastImageFile)) {
        throw "No image was supplied and $LastImageFile does not exist."
    }
    $Image = (Get-Content -LiteralPath $LastImageFile -Raw).Trim()
}

$ExpectedImagePrefix = "${Region}-docker.pkg.dev/${ProjectId}/"
if (-not $Image.StartsWith($ExpectedImagePrefix)) {
    throw "Image '$Image' does not belong to project '$ProjectId' in '$Region'."
}

$EnvironmentFile = Join-Path $PSScriptRoot "staging.env.yaml"
$EnvironmentFileContent = Get-Content -LiteralPath $EnvironmentFile -Raw
if ($EnvironmentFileContent -match "example\.com|<[^>]+>") {
    throw "Replace placeholder values in $EnvironmentFile before deploying."
}

$Service = "lucidex-api-staging"
$ServiceAccount = "$Service@${ProjectId}.iam.gserviceaccount.com"
$Secrets = (
    "MONGODB_URI=lucidex-staging-mongodb-uri:{0}," +
    "JWT_SECRET_KEY=lucidex-staging-jwt-secret:{1}"
) -f (
    $MongoSecretVersion,
    $JwtSecretVersion
)

Write-Host "Deploying QA staging service" -ForegroundColor Cyan
Write-Host "Image: $Image"

& gcloud run deploy $Service `
    --project=$ProjectId `
    --image=$Image `
    --region=$Region `
    --allow-unauthenticated `
    --service-account=$ServiceAccount `
    --env-vars-file=$EnvironmentFile `
    --set-secrets=$Secrets `
    --cpu=1 `
    --memory=512Mi `
    --min-instances=0 `
    --max-instances=3 `
    --concurrency=20 `
    --timeout=300

if ($LASTEXITCODE -ne 0) {
    throw "Cloud Run deployment failed."
}

$ServiceUrl = (& gcloud run services describe $Service `
    --project=$ProjectId `
    --region=$Region `
    --format="value(status.url)").Trim()

if ($LASTEXITCODE -ne 0 -or -not $ServiceUrl) {
    throw "Deployment completed, but the service URL could not be resolved."
}

Write-Host "Running health check: $ServiceUrl/health"
$HealthResponse = Invoke-RestMethod -Uri "$ServiceUrl/health" -Method Get

Write-Host "QA staging deployment is healthy." -ForegroundColor Green
Write-Host "Service URL: $ServiceUrl"
Write-Host "Share this URL with FE/QA."
Write-Output $HealthResponse
