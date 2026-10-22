<#
.SYNOPSIS
  Import the verified hackathon dataset into local Docker PostgreSQL and smoke-test search.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dataset.ps1 -ArchivePath "$env:USERPROFILE\Downloads\starcoach-dataset-v16-cap300-csv.zip"
#>
[CmdletBinding()]
param(
    [string]$ArchivePath = '',
    [switch]$ForceReimport,
    [switch]$SkipFrontend
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ExpectedHash = 'b0afb47b2b70f65c6d8ec07b7423dcc49efc71cd7a27e95606fb81da008c210d'
$ExpectedProducts = 225903
$ExpectedShops = 6476
$ExpectedOffers = 331506
$ArchiveName = 'starcoach-dataset-v16-cap300-csv.zip'
$ArchiveDest = Join-Path $Root "data\$ArchiveName"

function Invoke-Checked {
    param([string]$Label, [string[]]$Arguments)
    Write-Host ">>> $Label" -ForegroundColor Cyan
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed (exit code $LASTEXITCODE). See the output above."
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop is required. Install/start Docker Desktop, reopen PowerShell and rerun.'
}
& docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Desktop is installed but its engine is not running. Start Docker Desktop.'
}
if ([string]::IsNullOrWhiteSpace($ArchivePath)) { $ArchivePath = $ArchiveDest }
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "Dataset ZIP not found at: $ArchivePath. Download it from Sources and pass -ArchivePath."
}
$ArchivePath = (Resolve-Path -LiteralPath $ArchivePath).Path
$ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ArchivePath).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) {
    throw 'Dataset SHA256 does not match the audited competition ZIP. No import attempted.'
}
Write-Host 'Archive SHA256 matches the audited competition dataset.' -ForegroundColor Green

New-Item -ItemType Directory -Force -Path (Join-Path $Root 'data'), (Join-Path $Root 'reports') | Out-Null
if (-not [string]::Equals($ArchivePath, $ArchiveDest, [StringComparison]::OrdinalIgnoreCase)) {
    Copy-Item -LiteralPath $ArchivePath -Destination $ArchiveDest -Force
}
if (-not (Test-Path (Join-Path $Root '.env'))) {
    $secret = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
    $dbpass = [Guid]::NewGuid().ToString('N')
    $configLines = @(
        "DJANGO_SECRET_KEY=$secret", 'DJANGO_DEBUG=0', 'POSTGRES_DB=bazaar_compass',
        'POSTGRES_USER=bazaar_compass', "POSTGRES_PASSWORD=$dbpass", 'LLM_ENABLED=0', 'APP_PORT=8080'
    )
    [System.IO.File]::WriteAllLines(
        (Join-Path $Root '.env'), $configLines,
        (New-Object System.Text.UTF8Encoding($false))
    )
    Write-Host 'Created a private local .env with random credentials; never commit it.' -ForegroundColor Green
}

Push-Location $Root
try {
    Invoke-Checked 'Validate Compose configuration' @('compose','config','--quiet')
    Invoke-Checked 'Build and start PostgreSQL and Django' @('compose','up','-d','--build','db','backend')
    $ready = $false
    for ($n=0; $n -lt 45; $n++) {
        & docker compose exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready/',timeout=3).status)" *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        & docker compose logs --tail 80 backend
        throw 'Django failed to become ready.'
    }

    $counts = @(
        'verify_dataset','--products',"$ExpectedProducts",'--shops',"$ExpectedShops",
        '--offers',"$ExpectedOffers",'--sample-product','product_47796232454501a5e8179e26',
        '--sample-shop','shop_3f93a30a9e66c6dece07cdff',
        '--sample-offer','offer_98512b2127469a2d20a64b3b'
    )
    & docker compose exec -T backend python manage.py @counts *> $null
    $alreadyImported = $LASTEXITCODE -eq 0
    if ($alreadyImported -and -not $ForceReimport) {
        Write-Host 'Dataset already imported and verified; skipping repeated import.' -ForegroundColor Green
    } else {
        Invoke-Checked 'Preflight without DB writes' @(
            'compose','exec','-T','backend','python','manage.py','import_dataset',
            '--archive',"/app/data/$ArchiveName",'--dry-run','--strict-json','--report-dir','/tmp/bazaar-import-reports'
        )
        Invoke-Checked 'Import ZIP into PostgreSQL' @(
            'compose','exec','-T','backend','python','manage.py','import_dataset',
            '--archive',"/app/data/$ArchiveName",'--strict-json','--report-dir','/tmp/bazaar-import-reports'
        )
    }
    Invoke-Checked 'Check actual imported counts and sample IDs' (@('compose','exec','-T','backend','python','manage.py') + $counts)

    if (-not $SkipFrontend) {
        $appPort = 8080
        $portLine = Get-Content (Join-Path $Root '.env') |
            Where-Object { $_ -match '^APP_PORT\s*=' } | Select-Object -First 1
        if ($portLine -match '^APP_PORT\s*=\s*(\d+)') { $appPort = [int]$Matches[1] }
        Invoke-Checked 'Start frontend' @('compose','up','-d','--build','frontend')
        $webReady = $false
        for ($n=0; $n -lt 30; $n++) {
            try {
                $h = Invoke-RestMethod -Uri "http://127.0.0.1:$appPort/api/v1/health/ready/" -TimeoutSec 4
                if ($h.status -eq 'ready') { $webReady = $true; break }
            } catch { Start-Sleep -Seconds 2 }
        }
        if (-not $webReady) {
            & docker compose logs --tail 80 frontend backend
            throw 'Web gateway did not become ready.'
        }
        $query = [Uri]::EscapeDataString('هدفون')
        $result = Invoke-RestMethod -Uri "http://127.0.0.1:$appPort/api/v1/catalog/search/?q=$query&page=1&page_size=2" -TimeoutSec 60
        if ([int]$result.total -lt 1) {
            throw 'Catalog search returned no result for the known sample query.'
        }
        Write-Host "Search smoke test passed: $($result.total) matching products." -ForegroundColor Green
        Write-Host "Application: http://localhost:$appPort" -ForegroundColor Green
    } else {
        Write-Host 'Django and dataset are ready; frontend skipped.' -ForegroundColor Green
    }
    Write-Host 'Raw ZIP remains local in ignored data folder. No CI was used.' -ForegroundColor Green
} finally {
    Pop-Location
}
