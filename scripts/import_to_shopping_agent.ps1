#Requires -Version 5.1
<#
.SYNOPSIS
  Safely imports the extracted Bazaar Compass baseline into afakhari/shopping_agent.
.DESCRIPTION
  Dry-run by default. With -Push, clones the existing repo, creates a feature branch,
  copies only reviewed files, checks for common secrets, commits and pushes that branch.
  Never force-pushes or edits main. Does not require Python.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\import_to_shopping_agent.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\import_to_shopping_agent.ps1 -Push
#>
[CmdletBinding()]
param([switch]$Push)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Repo = 'https://github.com/afakhari/shopping_agent.git'
$Branch = 'bootstrap/import-existing-code'
$BlockParts = @('.git','.venv','venv','node_modules','__pycache__','.pytest_cache','.ruff_cache','.mypy_cache','dist','build','.next','.idea','.vscode','data','.secrets','private')
$BlockExtensions = @('.pem','.p12','.pfx','.key','.sqlite3','.db','.dump','.zip','.csv','.log')
$RootExclusions = @('AGENTS.md','README.md','CONTRIBUTING.md','.gitignore','.env.example','LICENSE')
$BlockedName = '^(\.env(?!\.example$)|id_rsa|id_ed25519)$'
$SecretPattern = '(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)'
$items = [System.Collections.Generic.List[object]]::new()

foreach ($src in Get-ChildItem -LiteralPath $Root -File -Recurse -Force) {
    $relative = $src.FullName.Substring($Root.Length).TrimStart([char]'\', [char]'/').Replace('\', '/')
    $parts = $relative.Split('/')
    $blocked = $false
    foreach ($part in $parts) {
        if ($BlockParts -contains $part) { $blocked = $true; break }
    }
    if ($blocked -or $src.Name -match $BlockedName -or ($BlockExtensions -contains $src.Extension.ToLowerInvariant())) { continue }
    if ($parts.Count -eq 1 -and $RootExclusions -contains $src.Name) { continue }
    if ($relative -eq '.github/pull_request_template.md' -or $relative -eq '.github/ISSUE_TEMPLATE/feature.md') { continue }
    if ($relative -eq 'scripts/publish-new-repo.sh') { continue }
    if ($parts.Count -eq 1 -and ($src.Name -like 'APPLY-*' -or @('FIX-INSTRUCTIONS.fa.md','DESIGN-SYSTEM-APPLY.fa.md','UX-UI-UPDATE-INSTRUCTIONS.fa.md') -contains $src.Name)) { continue }

    $targetRelative = $relative
    if ($parts[0] -eq 'docs') {
        $targetRelative = 'docs/legacy-baseline/' + $relative.Substring(5)
    }
    # Avoid accidental credential publication. This conservative scan can stop on false positives.
    $raw = [System.IO.File]::ReadAllBytes($src.FullName)
    $candidateText = [System.Text.Encoding]::ASCII.GetString($raw)
    if ($candidateText -match $SecretPattern) {
        throw "Potential secret found in $relative. Review and remove before uploading."
    }
    $items.Add([pscustomobject]@{ Source=$src.FullName; Relative=$targetRelative })
}

Write-Host "Ready to import $($items.Count) sanitized files from: $Root"
Write-Host 'Protected: existing README, AGENTS, LICENSE and GitHub baseline documentation.'
if (-not $Push) {
    Write-Host 'Dry-run successful. For publishing, rerun with -Push.'
    exit 0
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git was not found. Install Git for Windows, restart PowerShell, and verify: git --version'
}

function Invoke-Git {
    param([Parameter(Mandatory=$true)][string[]]$Arguments, [Parameter(Mandatory=$true)][string]$WorkingDir)
    Push-Location -LiteralPath $WorkingDir
    try {
        & git @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Git failed (exit $LASTEXITCODE): git $($Arguments -join ' ')" }
    } finally { Pop-Location }
}

$workspace = Join-Path $env:TEMP ('bazaar-import-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $workspace -Force | Out-Null
$targetRepo = Join-Path $workspace 'shopping_agent'
Write-Host "Temporary working directory: $targetRepo"
Invoke-Git -Arguments @('clone', $Repo, $targetRepo) -WorkingDir $workspace
Invoke-Git -Arguments @('switch', '-c', $Branch) -WorkingDir $targetRepo
foreach ($file in $items) {
    $destination = Join-Path $targetRepo $file.Relative.Replace('/', [IO.Path]::DirectorySeparatorChar)
    if (Test-Path -LiteralPath $destination) {
        throw "File already exists in repository, refusing overwrite: $($file.Relative)"
    }
    $parent = Split-Path -Parent $destination
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Copy-Item -LiteralPath $file.Source -Destination $destination
}
Invoke-Git -Arguments @('-c','core.autocrlf=false','add','-A') -WorkingDir $targetRepo
Invoke-Git -Arguments @('diff','--cached','--check') -WorkingDir $targetRepo
Invoke-Git -Arguments @('diff','--cached','--stat') -WorkingDir $targetRepo
Invoke-Git -Arguments @('commit','-m','chore: import sanitized Bazaar Compass application baseline') -WorkingDir $targetRepo
Invoke-Git -Arguments @('push','-u','origin',$Branch) -WorkingDir $targetRepo
Write-Host 'SUCCESS: branch pushed. Main is untouched.' -ForegroundColor Green
Write-Host 'Open PR: https://github.com/afakhari/shopping_agent/compare/main...bootstrap/import-existing-code?expand=1'
