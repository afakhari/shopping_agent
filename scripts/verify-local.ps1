[CmdletBinding()]
param(
    [switch]$SkipPython,
    [switch]$SkipFrontend,
    [switch]$WithDocker,
    [switch]$ImportDataset
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$DatasetPath = Join-Path $Root 'data\starcoach-dataset-v16-cap300-csv.zip'
$ReportsPath = Join-Path $Root 'reports'
New-Item -ItemType Directory -Force -Path $ReportsPath | Out-Null

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $false)][string[]]$CommandArgs = @()
    )
    Write-Host "`n>>> $Label" -ForegroundColor Cyan
    & $Command @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE. See the output immediately above."
    }
}

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host 'Bazaar Compass local verification' -ForegroundColor Green
Write-Host "Project: $Root"
Write-Host 'This script runs local checks first. Docker deployment and dataset writes require explicit flags.'

if (-not $SkipPython) {
    if (-not (Test-CommandExists 'py')) {
        throw 'Python launcher (py) is missing. Install Python 3.13 x64 from https://www.python.org/downloads/windows/ and enable the Python Launcher.'
    }
    Invoke-Checked -Label 'Check Python 3.13' -Command 'py' -CommandArgs @('-3.13', '--version')

    $BackendPath = Join-Path $Root 'backend'
    $VenvPath = Join-Path $BackendPath '.venv'
    $VenvPython = Join-Path $VenvPath 'Scripts\python.exe'
    if (-not (Test-Path $VenvPython)) {
        Invoke-Checked -Label 'Create backend virtual environment' -Command 'py' -CommandArgs @('-3.13', '-m', 'venv', $VenvPath)
    }
    Invoke-Checked -Label 'Upgrade pip' -Command $VenvPython -CommandArgs @('-m', 'pip', 'install', '--upgrade', 'pip')
    Invoke-Checked -Label 'Install backend development dependencies' -Command $VenvPython -CommandArgs @('-m', 'pip', 'install', '-r', (Join-Path $BackendPath 'requirements-dev.txt'))

    $PreviousDatabaseUrl = $env:DATABASE_URL
    $PreviousDebug = $env:DJANGO_DEBUG
    $PreviousSettings = $env:DJANGO_SETTINGS_MODULE
    $env:DATABASE_URL = 'sqlite:///:memory:'
    $env:DJANGO_DEBUG = '1'
    $env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
    try {
        Push-Location $BackendPath
        Invoke-Checked -Label 'Django system checks' -Command $VenvPython -CommandArgs @('manage.py', 'check')
        Invoke-Checked -Label 'Check migration/model consistency' -Command $VenvPython -CommandArgs @('manage.py', 'makemigrations', '--check', '--dry-run')
        Invoke-Checked -Label 'Backend test suite' -Command $VenvPython -CommandArgs @('-m', 'pytest', '-q')
        Invoke-Checked -Label 'Backend lint' -Command $VenvPython -CommandArgs @('-m', 'ruff', 'check', '.')
        if (Test-Path $DatasetPath) {
            Invoke-Checked -Label 'Dataset importer dry-run (strict JSON)' -Command $VenvPython -CommandArgs @('manage.py', 'import_dataset', '--archive', $DatasetPath, '--dry-run', '--strict-json', '--report-dir', $ReportsPath)
        } else {
            Write-Warning "Dataset ZIP not found at $DatasetPath. Importer dry-run skipped; place the supplied ZIP there to enable it."
        }
    } finally {
        Pop-Location
        $env:DATABASE_URL = $PreviousDatabaseUrl
        $env:DJANGO_DEBUG = $PreviousDebug
        $env:DJANGO_SETTINGS_MODULE = $PreviousSettings
    }

    if (Test-Path $DatasetPath) {
        Invoke-Checked -Label 'Independent dataset audit (Python standard library)' -Command $VenvPython -CommandArgs @((Join-Path $Root 'scripts\audit_dataset.py'), $DatasetPath, '--report-dir', $ReportsPath)
    }
}

if (-not $SkipFrontend) {
    if (-not (Test-CommandExists 'node') -or -not (Test-CommandExists 'npm.cmd')) {
        throw 'Node.js/npm is missing. Install Node.js 22.12+ LTS from https://nodejs.org/ and reopen PowerShell.'
    }
    Invoke-Checked -Label 'Check Node.js version' -Command 'node' -CommandArgs @('--version')
    Invoke-Checked -Label 'Check npm version' -Command 'npm.cmd' -CommandArgs @('--version')

    $FrontendPath = Join-Path $Root 'frontend'
    Push-Location $FrontendPath
    try {
        if (Test-Path (Join-Path $FrontendPath 'package-lock.json')) {
            Invoke-Checked -Label 'Install exact frontend lockfile dependencies' -Command 'npm.cmd' -CommandArgs @('ci', '--no-audit', '--no-fund')
        } else {
            Write-Warning 'package-lock.json does not exist yet; npm install will create it. Keep and commit the resulting lockfile in your own repository.'
            Invoke-Checked -Label 'Install frontend dependencies and generate lockfile' -Command 'npm.cmd' -CommandArgs @('install', '--no-audit', '--no-fund')
        }
        Invoke-Checked -Label 'Frontend lint' -Command 'npm.cmd' -CommandArgs @('run', 'lint')
        Invoke-Checked -Label 'Frontend TypeScript typecheck' -Command 'npm.cmd' -CommandArgs @('run', 'typecheck')
        Invoke-Checked -Label 'Frontend unit tests' -Command 'npm.cmd' -CommandArgs @('test')
        Invoke-Checked -Label 'Frontend production build' -Command 'npm.cmd' -CommandArgs @('run', 'build')
    } finally {
        Pop-Location
    }
}

if ($ImportDataset -and -not $WithDocker) {
    throw 'ImportDataset writes to the local Docker PostgreSQL database; pass -WithDocker -ImportDataset together to make this explicit.'
}

if ($WithDocker) {
    if (-not (Test-CommandExists 'docker')) {
        throw 'Docker CLI is missing. Install Docker Desktop for Windows, start it, reopen PowerShell, and run docker version.'
    }
    Invoke-Checked -Label 'Validate Docker Compose config' -Command 'docker' -CommandArgs @('compose', 'config', '--quiet')

    if (-not (Test-Path (Join-Path $Root '.env'))) {
        Copy-Item (Join-Path $Root '.env.example') (Join-Path $Root '.env')
        Write-Warning 'Created .env from .env.example with local-only defaults. Do not use these default secrets in any public deployment.'
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $Root 'data'), $ReportsPath | Out-Null
    if ($ImportDataset -and -not (Test-Path $DatasetPath)) {
        throw "Dataset import requested, but archive is missing: $DatasetPath"
    }

    Push-Location $Root
    try {
        Invoke-Checked -Label 'Build and start services' -Command 'docker' -CommandArgs @('compose', 'up', '--build', '-d')
        $port = 8080
        $portLine = Get-Content (Join-Path $Root '.env') | Where-Object { $_ -match '^APP_PORT\s*=' } | Select-Object -First 1
        if ($portLine -and $portLine -match '^APP_PORT\s*=\s*(\d+)') { $port = [int]$Matches[1] }
        $readyUrl = "http://localhost:$port/api/v1/health/ready/"
        $ready = $false
        for ($i = 0; $i -lt 45; $i++) {
            try {
                $payload = Invoke-RestMethod -Uri $readyUrl -TimeoutSec 3
                if ($payload.status -eq 'ready') { $ready = $true; break }
            } catch { Start-Sleep -Seconds 2 }
        }
        if (-not $ready) {
            Write-Host '--- Recent Docker logs ---' -ForegroundColor Yellow
            & docker compose logs --tail 100
            throw "Backend readiness failed at $readyUrl. Inspect logs above before retrying."
        }
        Write-Host "Backend ready: $readyUrl" -ForegroundColor Green

        if (Test-Path $DatasetPath) {
            Invoke-Checked -Label 'Docker dataset preflight (dry-run)' -Command 'docker' -CommandArgs @('compose', 'exec', '-T', 'backend', 'python', 'manage.py', 'import_dataset', '--archive', '/app/data/starcoach-dataset-v16-cap300-csv.zip', '--dry-run', '--strict-json', '--report-dir', '/app/reports')
            if ($ImportDataset) {
                Invoke-Checked -Label 'Import dataset into local Docker PostgreSQL' -Command 'docker' -CommandArgs @('compose', 'exec', '-T', 'backend', 'python', 'manage.py', 'import_dataset', '--archive', '/app/data/starcoach-dataset-v16-cap300-csv.zip', '--strict-json', '--report-dir', '/app/reports')
            }
        } elseif ($ImportDataset) {
            throw "Dataset ZIP not found at $DatasetPath. Copy the supplied dataset there and rerun."
        } else {
            Write-Warning "Dataset is not present at $DatasetPath; database will remain empty."
        }

        if ($ImportDataset) {
            $escapedQuery = [uri]::EscapeDataString('هدفون')
            $searchUrl = "http://localhost:$port/api/v1/catalog/search/?q=$escapedQuery&page=1&page_size=1"
            $searchPayload = Invoke-RestMethod -Uri $searchUrl -TimeoutSec 20
            if ($null -eq $searchPayload.total -or [int]$searchPayload.total -lt 0) {
                throw 'Catalog smoke test returned an invalid total value.'
            }
            Write-Host ("Catalog smoke test succeeded. total=" + $searchPayload.total) -ForegroundColor Green
        } else {
            Write-Warning 'Search smoke test skipped because -ImportDataset was not requested; the database may be empty.'
        }
        Write-Host "Frontend: http://localhost:$port" -ForegroundColor Green
        Write-Host 'Services remain running. Stop them with: docker compose down' -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

Write-Host "`nAll requested verification stages completed successfully." -ForegroundColor Green
