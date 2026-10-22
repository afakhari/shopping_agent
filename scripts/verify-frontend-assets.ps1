param(
  [string]$BaseUrl = 'http://localhost:8080'
)

$ErrorActionPreference = 'Stop'
$BaseUrl = $BaseUrl.TrimEnd('/')

Write-Host "Checking frontend HTML at $BaseUrl ..." -ForegroundColor Cyan
$response = Invoke-WebRequest "$BaseUrl/" -UseBasicParsing
$html = [string]$response.Content
$cssMatch = [regex]::Match($html, 'href="([^"]+\.css)"')
if (-not $cssMatch.Success) {
  throw 'No CSS bundle link was found in the served HTML. The frontend container may be serving a stale or incomplete build.'
}

$cssPath = $cssMatch.Groups[1].Value
if ($cssPath.StartsWith('/')) {
  $cssUrl = "$BaseUrl$cssPath"
} else {
  $cssUrl = "$BaseUrl/$cssPath"
}

Write-Host "CSS asset: $cssPath"
$cssResponse = Invoke-WebRequest $cssUrl -UseBasicParsing
$contentType = [string]$cssResponse.Headers['Content-Type']
$css = [string]$cssResponse.Content
if ($contentType -notmatch 'text/css') {
  throw "The CSS asset returned Content-Type '$contentType' instead of text/css."
}
if (-not $css.Contains('--bc-chat-canvas')) {
  throw 'The loaded CSS does not contain the chat-shell design marker. Rebuild and recreate the frontend container.'
}

Write-Host 'PASS: HTML points to a CSS asset, the asset responds as text/css, and the new chat shell is present.' -ForegroundColor Green
Write-Host 'If the page still looks unchanged, use Ctrl+F5 and check the browser Network panel for the CSS request.'
