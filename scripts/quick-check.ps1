# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/quick-check.ps1
# Optional: -Frontend (also run frontend TypeScript checks if dependencies are installed)
param([switch]$Frontend)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Write-Host "Local fast checks - no GitHub Actions usage"
& py -3.13 -m compileall -q (Join-Path $root "backend") (Join-Path $root "scripts")
if ($LASTEXITCODE -ne 0) { throw "Python compileall failed." }
& py -3.13 (Join-Path $root "scripts/verify_scaffold.py")
if ($LASTEXITCODE -ne 0) { throw "Scaffold verification failed." }
if ($Frontend) {
    if (!(Test-Path (Join-Path $root "frontend/node_modules"))) {
        throw "Install frontend dependencies once via: cd frontend; npm ci"
    }
    Push-Location (Join-Path $root "frontend")
    try {
        & npm run typecheck
        if ($LASTEXITCODE -ne 0) { throw "Frontend TypeScript failed." }
    }
    finally { Pop-Location }
}
Write-Host "Fast local checks passed. Full integration tests were NOT run."
