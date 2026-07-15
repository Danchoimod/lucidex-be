param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Region = "asia-southeast1",

    [string]$Repository = "lucidex",

    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"

$BackendDirectory = Split-Path $PSScriptRoot -Parent
$RepositoryRoot = Split-Path $BackendDirectory -Parent
$LastImageFile = Join-Path $PSScriptRoot ".last-image"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or is not available in PATH."
}

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

$GitStatus = & git -C $RepositoryRoot status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the Git working tree status."
}

$IsDirty = [bool]$GitStatus
if ($IsDirty -and -not $AllowDirty) {
    throw (
        "The working tree has uncommitted changes. Commit them before " +
        "building, or pass -AllowDirty for a temporary staging build."
    )
}

$CommitSha = (& git -C $RepositoryRoot rev-parse --short HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $CommitSha) {
    throw "Unable to determine the current Git commit."
}

$ImageTag = if ($IsDirty) {
    $Timestamp = Get-Date -Format "yyyyMMddHHmmss"
    "$CommitSha-dirty-$Timestamp"
} else {
    $CommitSha
}

$Image = (
    "{0}-docker.pkg.dev/{1}/{2}/api:{3}" -f
    $Region,
    $ProjectId,
    $Repository,
    $ImageTag
)

Write-Host "Building Lucidex image:" -ForegroundColor Cyan
Write-Host $Image

& gcloud builds submit $BackendDirectory `
    --project=$ProjectId `
    --region=$Region `
    --tag=$Image

if ($LASTEXITCODE -ne 0) {
    throw "Cloud Build failed."
}

Set-Content -LiteralPath $LastImageFile -Value $Image -Encoding utf8

Write-Host "Build completed." -ForegroundColor Green
Write-Host "Image reference saved to $LastImageFile"
Write-Host "Next: deploy-cloud-run.ps1 -ProjectId <project-id> ..."
