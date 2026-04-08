Param(
  [string]$OpenWebuiDir = ".\\open-webui",
  [string]$VendorDir = ".\\vendor",
  [string]$TorchIndexUrlCpu = "https://download.pytorch.org/whl/cpu",
  [string]$NodeImage = "node:22-alpine3.20",
  [string]$PythonImage = "python:3.11.14-slim-bookworm"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir($p) {
  if (!(Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

if (!(Test-Path $OpenWebuiDir)) {
  throw "open-webui dir not found: $OpenWebuiDir (clone upstream first)"
}

Ensure-Dir $VendorDir
Ensure-Dir (Join-Path $VendorDir "npm-cache")
Ensure-Dir (Join-Path $VendorDir "pip-wheels")
Ensure-Dir (Join-Path $VendorDir "apt-debs")
Ensure-Dir (Join-Path $VendorDir "images")

Write-Host "Pulling base images (for offline availability)..."
docker pull $NodeImage | Out-Null
docker pull $PythonImage | Out-Null
docker save -o (Join-Path $VendorDir "images\\node.tar") $NodeImage
docker save -o (Join-Path $VendorDir "images\\python.tar") $PythonImage

Write-Host "Populating npm cache (contains package tarballs)..."
docker run --rm `
  -v "${PWD}\\${OpenWebuiDir}:/work:ro" `
  -v "${PWD}\\${VendorDir}\\npm-cache:/npm-cache" `
  $NodeImage sh -lc "set -e; cp -a /work /tmp/work; cd /tmp/work; npm ci --force --cache /npm-cache"

Write-Host "Downloading Python wheels (including torch + uv) ..."
docker run --rm `
  -v "${PWD}\\${OpenWebuiDir}:/work:ro" `
  -v "${PWD}\\${VendorDir}\\pip-wheels:/wheels" `
  $PythonImage bash -lc "python -m pip install --upgrade pip && pip download -r /work/backend/requirements.txt -d /wheels && pip download -d /wheels uv && pip download -d /wheels --index-url '$TorchIndexUrlCpu' 'torch<=2.9.1' torchvision torchaudio"

Write-Host "Downloading apt .deb archives (system build deps)..."
$AptPkgs = @(
  "git",
  "build-essential",
  "pandoc",
  "gcc",
  "netcat-openbsd",
  "curl",
  "jq",
  "libmariadb-dev",
  "python3-dev",
  "ffmpeg",
  "libsm6",
  "libxext6",
  "zstd"
) -join " "

docker run --rm `
  -v "${PWD}\\${VendorDir}\\apt-debs:/debs" `
  $PythonImage bash -lc "set -eux; apt-get update; apt-get install -y --no-install-recommends apt-utils ca-certificates; apt-get -y --download-only -o Dir::Cache::archives=/debs install $AptPkgs; ls -la /debs"

Write-Host ""
Write-Host "Vendor ready in: $VendorDir"
Write-Host "On the offline machine:"
Write-Host "  docker load -i .\\vendor\\images\\node.tar"
Write-Host "  docker load -i .\\vendor\\images\\python.tar"
Write-Host "  docker build --pull=false -f Dockerfile.offline -t open-webui:branded-offline ."

