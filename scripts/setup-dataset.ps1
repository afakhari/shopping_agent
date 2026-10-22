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
    [switch]$SkipFrontend,
    [switch]$RepairDbPassword
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

# Windows PowerShell 5.1 promotes native stderr to ErrorRecord when redirected.
# A transient "connection refused" during readiness is expected, not a fatal error.
# Temporarily allow native stderr, then decide by the real process exit code.
function Test-DockerCommand {
    param([string[]]$Arguments)
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker @Arguments 2>&1 | Out-Null
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    return ($exitCode -eq 0)
}

function Invoke-Checked {
    param([string]$Label, [string[]]$Arguments)
    Write-Host ">>> $Label" -ForegroundColor Cyan
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker @Arguments
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "$Label failed (exit code $exitCode). See the output above."
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop is required. Install/start Docker Desktop, reopen PowerShell and rerun.'
}
if (-not (Test-DockerCommand -Arguments @('info','--format','{{.ServerVersion}}'))) {
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
    # Avoid recopying the large archive on every retry.
    $destinationMatches = (Test-Path -LiteralPath $ArchiveDest -PathType Leaf) -and
        ((Get-FileHash -Algorithm SHA256 -LiteralPath $ArchiveDest).Hash.ToLowerInvariant() -eq $ExpectedHash)
    if (-not $destinationMatches) {
        Copy-Item -LiteralPath $ArchivePath -Destination $ArchiveDest -Force
    }
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
    # PostgreSQL persists the original password in its named volume.
    # A newly generated .env does NOT change the role password in existing data.
    Invoke-Checked 'Start PostgreSQL and wait for healthcheck' @('compose','up','--wait','-d','db')
    $tcpProbe = @('compose','exec','-T','db','sh','-ec',
        'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1"')
    if (-not (Test-DockerCommand -Arguments $tcpProbe)) {
        if (-not $RepairDbPassword) {
            throw 'PostgreSQL password in the existing volume differs from the local .env (or authentication failed). For an opt-in local repair, rerun with -RepairDbPassword. No data was deleted.'
        }
        # Only repair a database whose local socket is accessible and whose
        # credentials match the autogenerated local development format.
        $socketProbe = @('compose','exec','-T','db','sh','-ec',
            'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1"')
        if (-not (Test-DockerCommand -Arguments $socketProbe)) {
            throw 'Cannot authenticate as local PostgreSQL administrator. No changes were made; investigate the existing database credentials.'
        }
        $conf = @{}
        foreach ($item in [System.IO.File]::ReadAllLines((Join-Path $Root '.env'))) {
            if ($item -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
                $conf[$Matches[1]] = $Matches[2]
            }
        }
        $dbUser = $conf['POSTGRES_USER']
        $dbName = $conf['POSTGRES_DB']
        $dbPassword = $conf['POSTGRES_PASSWORD']
        if ($dbUser -cne 'bazaar_compass' -or $dbName -cne 'bazaar_compass' -or
            [string]::IsNullOrEmpty($dbPassword) -or $dbPassword -cnotmatch '^[0-9a-fA-F]{32}$') {
            throw 'Password repair only supports credentials generated by setup-dataset.ps1. Existing database left unchanged.'
        }
        Write-Host 'Synchronizing local DB role password with .env. All tables and Docker volumes are preserved.' -ForegroundColor Yellow
        Invoke-Checked 'Stop backend during credential repair' @('compose','stop','backend')
        # Pass the SQL through stdin, NOT a process argument or logged command.
        $sql = 'ALTER ROLE "' + $dbUser + '" WITH PASSWORD ''' + $dbPassword + ''';'
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $sql | & docker compose exec -T db psql -X -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -q -f -
            $sqlExitCode = $LASTEXITCODE
        } finally {
            $sql = $null
            $dbPassword = $null
            $ErrorActionPreference = $previousPreference
        }
        if ($sqlExitCode -ne 0) {
            throw 'Local role password repair failed; database contents were not deleted.'
        }
        if (-not (Test-DockerCommand -Arguments $tcpProbe)) {
            throw 'The updated password could not authenticate over TCP. Data/volumes have been preserved.'
        }
        Write-Host 'Local PostgreSQL credentials are now consistent.' -ForegroundColor Green
    }
    Invoke-Checked 'Build and start Django' @('compose','up','-d','--build','backend')
    $ready = $false
    for ($n=0; $n -lt 45; $n++) {
        $ready = Test-DockerCommand -Arguments @(
            'compose','exec','-T','backend','python','-c',
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready/',timeout=3).status)"
        )
        if ($ready) { break }
        if ($n -eq 0 -or ($n % 10) -eq 9) {
            Write-Host "Django is starting (readiness probe $($n + 1)/45)." -ForegroundColor DarkGray
        }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        Write-Host 'Django readiness did not succeed. Docker status and recent logs:' -ForegroundColor Yellow
        Invoke-Checked 'Show Compose service status' @('compose','ps','-a')
        Invoke-Checked 'Show backend and database logs' @('compose','logs','--tail','100','backend','db')
        throw 'Django failed readiness. See errors above; do not delete Docker volumes.'
    }

    $counts = @(
        'verify_dataset','--products',"$ExpectedProducts",'--shops',"$ExpectedShops",
        '--offers',"$ExpectedOffers",'--sample-product','product_47796232454501a5e8179e26',
        '--sample-shop','shop_3f93a30a9e66c6dece07cdff',
        '--sample-offer','offer_98512b2127469a2d20a64b3b'
    )
    $alreadyImported = Test-DockerCommand -Arguments (@('compose','exec','-T','backend','python','manage.py') + $counts)
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
        # ASCII-only UTF-8 percent encoding for the default Persian query:
        # Avoid Windows PowerShell 5.1 misreading UTF-8 .ps1 files without BOM.
        $encodedQuery = '%D9%87%D8%AF%D9%81%D9%88%D9%86'
        $searchUrl = "http://127.0.0.1:$appPort/api/v1/catalog/search/?q=$encodedQuery" + '&page=1&page_size=2'
        $result = Invoke-RestMethod -Uri $searchUrl -TimeoutSec 120
        $hasTotal = $null -ne $result -and $result.PSObject.Properties.Name -contains 'total'
        if (-not $hasTotal -or [int]$result.total -lt 1) {
            Write-Host 'Search smoke test failed. Inspecting the actual PostgreSQL and Django API state:' -ForegroundColor Yellow
            Invoke-Checked 'Read-only DB and search diagnostics' @(
                'compose','exec','-T','backend','python','manage.py','diagnose_search'
            )
            throw 'The real catalog search returned zero results or unexpected JSON. Use the diagnostics above; do not reimport the dataset.'
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
