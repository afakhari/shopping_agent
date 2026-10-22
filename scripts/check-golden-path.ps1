<#
.SYNOPSIS
  Validate the implemented shopping mission against real local PostgreSQL.
  Uses Docker, without importing data again or invoking GitHub Actions.
#>
[CmdletBinding()]
param([switch]$SkipBackendTests)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Invoke-Docker {
    param([string]$Label, [string[]]$Arguments)
    Write-Host ">>> $Label" -ForegroundColor Cyan
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker @Arguments
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode. No PostgreSQL volumes were deleted."
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop must be installed and running.'
}

Push-Location $root
try {
    Invoke-Docker 'Rebuild/start current backend + frontend; preserve DB volume' @(
        'compose','up','-d','--build','backend','frontend'
    )
    Invoke-Docker 'Django system check' @(
        'compose','exec','-T','backend','python','manage.py','check'
    )
    Invoke-Docker 'Confirm migrations are in sync' @(
        'compose','exec','-T','backend','python','manage.py','makemigrations','--check','--dry-run'
    )
    Invoke-Docker 'Confirm real PostgreSQL rows' @(
        'compose','exec','-T','backend','python','manage.py','verify_dataset',
        '--products','225903','--shops','6476','--offers','331506'
    )
    if (-not $SkipBackendTests) {
        # Django uses an isolated test database and never wipes the imported catalogue.
        Invoke-Docker 'Mission, agent, search, health, catalog tests in isolated test database' @(
            'compose','exec','-T','backend','python','manage.py','test',
            'apps.missions','apps.agent','apps.search','apps.health','apps.catalog','--noinput'
        )
    }
    # Compose understands service names directly. Avoid resolving container IDs:
    # Windows PowerShell 5.1 can treat a single/empty native pipeline value
    # inconsistently, and Compose is already managing backend container identity.
    # 'compose cp' transfers the raw UTF-8 bytes without recoding Persian text.
    Invoke-Docker 'Copy UTF-8 golden path smoke helper into backend' @(
        'compose','cp',(Join-Path $root 'scripts\smoke-golden-path.py'),
        'backend:/tmp/smoke-golden-path.py'
    )
    Invoke-Docker 'Copy smoke transport regression tests into backend' @(
        'compose','cp',(Join-Path $root 'scripts\test_golden_path_smoke.py'),
        'backend:/tmp/test_golden_path_smoke.py'
    )
    Invoke-Docker 'Check JSON + SSE share one session-aware HTTP transport' @(
        'compose','exec','-T','backend','python',
        '/tmp/test_golden_path_smoke.py'
    )
    Invoke-Docker 'Real HTTP mission + SSE + seller simulation through frontend gateway' @(
        'compose','exec','-T','backend','python',
        '/tmp/smoke-golden-path.py','--base-url','http://frontend',
        '--query',[string]::Concat([char]0x0647,[char]0x062F,[char]0x0641,[char]0x0648,[char]0x0646)
    )
    Write-Host 'ALL REQUESTED LOCAL CHECKS PASSED. No CI used; DB volume preserved.' -ForegroundColor Green
} finally {
    Pop-Location
}
