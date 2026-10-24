# Download DocILE dataset chunks. Pass token as first arg or $env:DOCILE_TOKEN.
# Never commit the token. Example: .\scripts\download_docile.ps1 YOUR_TOKEN annotated-trainval
param(
  [string]$Token = $env:DOCILE_TOKEN,
  [string]$Dataset = "annotated-trainval",
  [string]$OutDir = ""
)

if (-not $Token) {
  Write-Error "Set DOCILE_TOKEN or pass token as first argument (from https://docile.rossum.ai/)"
  exit 1
}

$root = if ($OutDir) { $OutDir } else { Join-Path $PSScriptRoot "..\data\train_data\docile" }
New-Item -ItemType Directory -Force -Path $root | Out-Null
$zip = Join-Path $root "$Dataset.zip"
$url = "https://docile.rossum.ai/download?token=$Token&dataset=$Dataset"

Write-Host "Downloading $Dataset -> $zip"
curl.exe -L -C - -o $zip $url
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$dest = Join-Path $root $Dataset
Write-Host "Unzipping to $dest (may take a while)..."
Expand-Archive -Path $zip -DestinationPath $dest -Force
Write-Host "Done. Annotations: $(Join-Path $dest 'annotations')"
