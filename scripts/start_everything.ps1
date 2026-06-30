param(
    [switch]$SkipFrontendBuild,
    [string]$Domain = "default",
    [int]$TopK = 5,
    [string]$GenerationMode = "extractive"
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

if (-not $SkipFrontendBuild) {
    Write-Host "Building frontend assets..."
    Set-Location "$repoRoot/frontend"
    npm install
    npm run build
    Set-Location $repoRoot
}

Write-Host "Starting SCARAG API..."
.venv\Scripts\python -m uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
