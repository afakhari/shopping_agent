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
    # A persisted PostgreSQL volume retains the original role password.
    # Recreating .env or changing POSTGRES_PASSWORD never updates that role.
    Invoke-Checked 'Start PostgreSQL and wait until healthy' @('compose','up','--wait','-d','db')
    $testTcp = @('compose','exec','-T','db','sh','-ec',
        'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1"')
    if (-not (Test-DockerCommand -Arguments $testTcp)) {
        if (-not $RepairDbPassword) {
            throw "Stored PostgreSQL credentials differ from .env (or TCP authentication failed). To repair the LOCAL role password without deleting data, rerun this script with -RepairDbPassword."
        }

        # Require both an existing local-socket administrator login and the
        # exact role/database created by this project's automatic setup.
        $localAdmin = @('compose','exec','-T','db','sh','-ec',
            'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1"')
        if (-not (Test-DockerCommand -Arguments $localAdmin)) {
            throw 'Local PostgreSQL administrator access failed. Database volume was left untouched; inspect the existing role/database manually.'
        }

        $localConfig = @{}
        foreach ($line in [System.IO.File]::ReadAllLines((Join-Path $Root '.env'))) {
            if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)
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
) {
                $localConfig[$Matches[1]] = $Matches[2]
            }
        }
        $role = $localConfig['POSTGRES_USER']
        $database = $localConfig['POSTGRES_DB']
        $password = $localConfig['POSTGRES_PASSWORD']
        if ($role -cne 'bazaar_compass' -or $database -cne 'bazaar_compass' -or
            -not $password -or $password -cnotmatch '^[0-9a-fA-F]{32}
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
) {
            throw 'Automatic password repair is restricted to the auto-generated local .env credentials. Database left unchanged.'
        }

        Write-Host 'Repairing the local PostgreSQL role password to match .env, preserving all databases and rows.' -ForegroundColor Yellow
        Invoke-Checked 'Stop restarting backend before database repair' @('compose','stop','backend')
        # SQL is sent on stdin, never included in process arguments, source,
        # GitHub logs, or displayed console output.
        $sql = 'ALTER ROLE "' + $role + '" WITH PASSWORD ''' + $password + ''';'
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $sql | & docker compose exec -T db psql -X -U $role -d $database -v ON_ERROR_STOP=1 -q -f -
            $repairExitCode = $LASTEXITCODE
        } finally {
            $sql = $null
            $password = $null
            $ErrorActionPreference = $previousPreference
        }
        if ($repairExitCode -ne 0) {
            throw 'PostgreSQL role password repair failed. Data and volumes were not deleted.'
        }
        if (-not (Test-DockerCommand -Arguments $testTcp)) {
            throw 'Database authentication still fails after repair. Check the PostgreSQL role configuration; volumes were preserved.'
        }
        Write-Host 'PostgreSQL password now matches the private .env file.' -ForegroundColor Green
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
