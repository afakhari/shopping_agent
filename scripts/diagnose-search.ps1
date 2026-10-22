<#
.SYNOPSIS
  Non-destructive Windows troubleshooting of search through Django and nginx.
  Does not import data, modify the database, or run GitHub Actions.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose-search.ps1
#>
[CmdletBinding()]
param([string]$Query = '', [switch]$RebuildBackend)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Push-Location $Root
try {
    Write-Host '>>> Compose status' -ForegroundColor Cyan
    & docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'Docker compose status unavailable.' }

    # Rebuild only when backend Python code changes; plain diagnosis is fast.
    if ($RebuildBackend) {
        Write-Host '>>> Rebuild backend (explicitly requested)' -ForegroundColor Cyan
        & docker compose up -d --build backend
    } else {
        Write-Host '>>> Ensure existing backend is started (no rebuild)' -ForegroundColor Cyan
        & docker compose up -d backend
    }
    if ($LASTEXITCODE -ne 0) { throw 'Backend start failed.' }

    Write-Host '>>> Database counters and direct Django API' -ForegroundColor Cyan
    # A blank Query uses the UTF-8 default defined in Python on Linux.
    # Windows PowerShell 5.1 decodes UTF-8 scripts without BOM as ANSI.
    if ([string]::IsNullOrWhiteSpace($Query)) {
        & docker compose exec -T backend python manage.py diagnose_search
    } else {
        & docker compose exec -T backend python manage.py diagnose_search --query $Query
    }
    if ($LASTEXITCODE -ne 0) { throw 'Django diagnostic command failed.' }

    $port = 8080
    $envFile = Join-Path $Root '.env'
    if (Test-Path $envFile) {
        $line = Get-Content -LiteralPath $envFile |
            Where-Object { $_ -match '^APP_PORT=' } |
            Select-Object -First 1
        if ($line -match '^APP_PORT=(\d+)$') { $port = [int]$Matches[1] }
    }
    # This ASCII-only literal is the UTF-8 percent encoding of the default query.
    # Never embed Persian characters directly in a Windows PowerShell 5.1 .ps1.
    $q = if ([string]::IsNullOrWhiteSpace($Query)) {
        '%D9%87%D8%AF%D9%81%D9%88%D9%86'
    } else {
        [Uri]::EscapeDataString($Query)
    }
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
