# deploy-all.ps1 — Orchestrate Vercel Deployment for Monorepo
# Manually injects .vercel/project.json to allow root deployment of multiple apps.

param(
    [string]$AppName = ""
)

$ErrorActionPreference = "Stop"

if (-not $env:VERCEL_TOKEN) {
    Write-Error "La variable de entorno VERCEL_TOKEN no esta configurada."
    exit 1
}

$apps = @(
    @{ Name = "devforge-site";  Root = "apps/devforge-site/frontend"  },
    @{ Name = "filecleaner";    Root = "apps/filecleaner/frontend"    },
    @{ Name = "invoicefollow";  Root = "apps/invoicefollow/frontend"  },
    @{ Name = "pricetrackr";    Root = "apps/pricetrackr/frontend"    },
    @{ Name = "webhookmonitor"; Root = "apps/webhookmonitor/frontend" },
    @{ Name = "feedbacklens";   Root = "apps/feedbacklens/frontend"   }
)

if ($AppName -ne "") {
    $apps = $apps | Where-Object { $_.Name -eq $AppName }
    if ($apps.Count -eq 0) {
        Write-Error "App '$AppName' no encontrada."
        exit 1
    }
}

$monorepoRoot = Get-Location

Write-Host "`n=== DevForge Vercel Deployment Orchestrator ==="

# Pre-requisito: Obtener el orgId (ID del usuario) una sola vez
Write-Host "Obteniendo informacion de la cuenta..."
$me = Invoke-RestMethod -Uri "https://api.vercel.com/v2/user" -Headers @{ Authorization = "Bearer $env:VERCEL_TOKEN" }
$orgId = $me.user.id

foreach ($app in $apps) {
    Write-Host "-------------------------------------------------"
    Write-Host "Procesando: $($app.Name)"

    # Paso 1 - Configurar / Obtener info del proyecto via Vercel API
    Write-Host "  [1/3] Configurando API y obteniendo IDs..."
    $headers = @{ Authorization = "Bearer $env:VERCEL_TOKEN" }
    
    # FIX 1: Intentar crear el proyecto si no existe
    try {
        Invoke-RestMethod `
            -Uri "https://api.vercel.com/v9/projects" `
            -Method POST `
            -Headers $headers `
            -ContentType "application/json" `
            -Body (@{ name = $app.Name; framework = "nextjs" } | ConvertTo-Json) | Out-Null
        Write-Host "  OK: Proyecto creado en Vercel."
    } catch {
        # Proyecto ya existe, ignorar error
    }

    # FIX 2: Configurar settings optimizados
    $apiUrl = "https://api.vercel.com/v9/projects/$($app.Name)"
    $config = @{
        rootDirectory   = $app.Root
        installCommand  = "pnpm install --frozen-lockfile"
        buildCommand    = "pnpm turbo build --filter=$($app.Name)..."
        outputDirectory = ".next"
        framework       = "nextjs"
    } | ConvertTo-Json

    $project = $null
    try {
        $project = Invoke-RestMethod -Uri $apiUrl -Method PATCH -Headers $headers -ContentType "application/json" -Body $config
        Write-Host "  OK: Configuracion API actualizada."
    } catch {
        # Si falla el PATCH, intentamos obtenerlo para tener el ID
        try {
            $project = Invoke-RestMethod -Uri $apiUrl -Method GET -Headers $headers
        } catch {
            Write-Warning "  FAIL: No se pudo obtener el proyecto '$($app.Name)' de Vercel."
            continue
        }
    }

    # Paso 2 - Crear .vercel/project.json manualmente para "engañar" al CLI
    Write-Host "  [2/3] Inyectando .vercel/project.json..."
    $vercelDir = Join-Path $monorepoRoot ".vercel"
    if (-not (Test-Path $vercelDir)) { New-Item -ItemType Directory -Path $vercelDir | Out-Null }
    
    $projectJson = @{
        orgId     = $orgId
        projectId = $project.id
    } | ConvertTo-Json
    
    Set-Content -Path (Join-Path $vercelDir "project.json") -Value $projectJson -Force

    # Paso 3 - Deploy desde el root
    Write-Host "  [3/3] Desplegando desde monorepo root..."
    & vercel deploy --prod --yes --token $env:VERCEL_TOKEN --cwd $monorepoRoot

    Write-Host "  OK: $($app.Name) desplegado con exito."
}

Write-Host "`n=== Orquestacion Finalizada ==="
