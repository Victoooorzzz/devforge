# deploy-all.ps1 — Deploy all DevForge frontend apps from monorepo root
# Usage: .\scripts\deploy-all.ps1 [app-name]
# If no app-name is given, deploys all apps.

param(
    [string]$AppName = ""
)

$ErrorActionPreference = "Stop"

# Map: package-name -> vercel-project-name -> output-dir
$apps = @(
    @{ Package = "devforge-site";  VercelProject = "devforge-empire";  OutputDir = "apps/devforge-site/frontend/out" },
    @{ Package = "filecleaner";    VercelProject = "file-cleaner";     OutputDir = "apps/filecleaner/frontend/out" },
    @{ Package = "invoicefollow";  VercelProject = "invoice-follow";   OutputDir = "apps/invoicefollow/frontend/out" },
    @{ Package = "pricetrackr";    VercelProject = "price-trackr";     OutputDir = "apps/pricetrackr/frontend/out" },
    @{ Package = "webhookmonitor"; VercelProject = "webhook-monitor";  OutputDir = "apps/webhookmonitor/frontend/out" },
    @{ Package = "feedbacklens";   VercelProject = "feedback-lens";    OutputDir = "apps/feedbacklens/frontend/out" }
)

# Filter if a specific app was requested
if ($AppName -ne "") {
    $apps = $apps | Where-Object { $_.Package -eq $AppName -or $_.VercelProject -eq $AppName }
    if ($apps.Count -eq 0) {
        Write-Error "App '$AppName' not found. Available: devforge-site, filecleaner, invoicefollow, pricetrackr, webhookmonitor, feedbacklens"
        exit 1
    }
}

$root = Split-Path -Parent $PSScriptRoot

Write-Host "`n=== DevForge Monorepo Deploy ===" -ForegroundColor Cyan
Write-Host "Root: $root"
Write-Host "Apps to deploy: $($apps.Count)`n"

# Step 1: Build all requested apps using turbo from monorepo root
Write-Host "[1/2] Building with Turbo..." -ForegroundColor Yellow
$filterArgs = ($apps | ForEach-Object { "--filter=$($_.Package)" }) -join " "
$buildCmd = "pnpm build $filterArgs"
Write-Host "  > $buildCmd"
Push-Location $root
Invoke-Expression $buildCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    Pop-Location
    exit 1
}
Pop-Location

# Step 2: Deploy each app's output directory to its Vercel project
Write-Host "`n[2/2] Deploying to Vercel..." -ForegroundColor Yellow
foreach ($app in $apps) {
    $outPath = Join-Path $root $app.OutputDir
    if (-not (Test-Path $outPath)) {
        Write-Warning "Output dir not found for $($app.Package): $outPath — skipping"
        continue
    }

    Write-Host "`n  Deploying $($app.Package) -> $($app.VercelProject)..." -ForegroundColor Green

    # Deploy the static output directory directly
    Push-Location $outPath
    vercel link --project $app.VercelProject --yes 2>&1 | Out-Null
    vercel deploy --prod --yes 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Deploy failed for $($app.Package)"
    } else {
        Write-Host "  ✓ $($app.Package) deployed!" -ForegroundColor Green
    }
    Pop-Location
}

Write-Host "`n=== Deploy Complete ===" -ForegroundColor Cyan
