<#
.SYNOPSIS
  Non-destructive Windows troubleshooting of search through Django and nginx.
  Does not import data, modify the database, or run GitHub Actions.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose-search.ps1
#>
[CmdletBinding()]
param([string]$Query = 'هدفون')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Push-Location $Root
try {
    Write-Host '>>> Compose status' -ForegroundColor Cyan
    & docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'Docker compose status unavailable.' }

    Write-Host '>>> Build backend source updates (no dataset reimport)' -ForegroundColor Cyan
    & docker compose up -d --build backend
    if ($LASTEXITCODE -ne 0) { throw 'Backend build/start failed.' }

    Write-Host '>>> Database counters and direct Django API' -ForegroundColor Cyan
    & docker compose exec -T backend python manage.py diagnose_search --query $Query
    if ($LASTEXITCODE -ne 0) { throw 'Django diagnostic command failed.' }

    $port = 8080
    $envFile = Join-Path $Root '.env'
    if (Test-Path $envFile) {
        $line = Get-Content -LiteralPath $envFile |
            Where-Object { $_ -match '^APP_PORT=' } |
            Select-Object -First 1
        if ($line -match '^APP_PORT=(\d+)$') { $port = [int]$Matches[1] }
    }
    $q = [Uri]::EscapeDataString($Query)
    $uri = "http://127.0.0.1:$port/api/v1/catalog/search/?q=$q"
    Write-Host '>>> Gateway API response (search query is URL-encoded)' -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri $uri -TimeoutSec 120 -ErrorAction Stop
        if ($null -eq $response.total) {
            Write-Host 'WARNING: HTTP JSON is missing the expected total field.' -ForegroundColor Yellow
            $response | ConvertTo-Json -Depth 4 | Write-Host
        } else {
            $n = if ($null -eq $response.results) { 0 } else { @($response.results).Count }
            Write-Host ("Gateway total={0}, results_on_page={1}, query={2}" -f $response.total, $n, $response.query) -ForegroundColor Green
        }
    } catch {
        Write-Host ('Gateway API failed: ' + $_.Exception.Message) -ForegroundColor Yellow
        Write-Host 'Use the Django API figures above to distinguish the backend from nginx/network issues.'
    }
    Write-Host 'Diagnostics done; existing database and Docker volumes preserved.' -ForegroundColor Green
} finally {
    Pop-Location
}
