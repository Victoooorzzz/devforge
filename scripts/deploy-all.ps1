# deploy-all.ps1 — Orchestrate Vercel Deployment for Monorepo
# Manually injects .vercel/project.json to allow root deployment of multiple apps.

param(
    [string]$AppName = ""
)

$ErrorActionPreference = "Stop"

# Load .env if it exists
$envFile = Join-Path (Get-Item -Path $PSScriptRoot).Parent.FullName ".env"
if (Test-Path $envFile) {
    Write-Host "Cargando variables desde .env..."
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#\s][^=]*)\s*=\s*['""]?(.*?)['""]?\s*$") {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

if (-not $env:VERCEL_TOKEN) {
    Write-Error "La variable de entorno VERCEL_TOKEN no esta configurada. Agregala a tu archivo .env como VERCEL_TOKEN=tu_token"
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

$monorepoRoot = (Get-Item -Path $PSScriptRoot).Parent.FullName

Write-Host "`n=== DevForge Vercel Deployment Orchestrator ==="
Write-Host "Root detectado: $monorepoRoot"

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
        nodeVersion     = "20.x"
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
    # MOVEMOS ESTO ANTES de inyectar variables para que el CLI sepa a que proyecto referirse
    Write-Host "  [1.5/3] Inyectando .vercel/project.json..."
    $vercelDir = Join-Path $monorepoRoot ".vercel"
    if (-not (Test-Path $vercelDir)) { New-Item -ItemType Directory -Path $vercelDir | Out-Null }
    
    $projectJson = @{
        orgId     = $orgId
        projectId = $project.id
    } | ConvertTo-Json
    
    Set-Content -Path (Join-Path $vercelDir "project.json") -Value $projectJson -Force

    # Paso 1.8 - Inyectar variables de entorno criticas via CLI
    Write-Host "  [1.8/3] Inyectando variables de entorno..."
    $variantKey = "NEXT_PUBLIC_LS_VARIANT_ID_$($app.Name.ToUpper())"
    $variantValue = Get-ChildItem Env: | Where-Object { $_.Name -eq $variantKey } | Select-Object -ExpandProperty Value
    
    # Temporarily allow errors (Vercel CLI writes progress to stderr)
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    if ($env:NEXT_PUBLIC_API_URL) {
        Write-Host "    - Sincronizando NEXT_PUBLIC_API_URL..."
        & vercel env rm NEXT_PUBLIC_API_URL production --token $env:VERCEL_TOKEN --yes --cwd $monorepoRoot 2>$null | Out-Null
        & vercel env add NEXT_PUBLIC_API_URL production "$($env:NEXT_PUBLIC_API_URL)" --token $env:VERCEL_TOKEN --cwd $monorepoRoot 2>$null | Out-Null
    }

    if ($variantValue) {
        Write-Host "    - Sincronizando LS Variant ID ($variantKey)..."
        & vercel env rm NEXT_PUBLIC_LS_VARIANT_ID production --token $env:VERCEL_TOKEN --yes --cwd $monorepoRoot 2>$null | Out-Null
        & vercel env add NEXT_PUBLIC_LS_VARIANT_ID production "$variantValue" --token $env:VERCEL_TOKEN --cwd $monorepoRoot 2>$null | Out-Null
        
        & vercel env rm $variantKey production --token $env:VERCEL_TOKEN --yes --cwd $monorepoRoot 2>$null | Out-Null
        & vercel env add $variantKey production "$variantValue" --token $env:VERCEL_TOKEN --cwd $monorepoRoot 2>$null | Out-Null
    }

    $ErrorActionPreference = $oldEAP

    # Paso 3 - Deploy desde el root
    Write-Host "  [3/3] Desplegando desde monorepo root..."
    & vercel deploy --prod --yes --token $env:VERCEL_TOKEN --cwd $monorepoRoot

    Write-Host "  OK: $($app.Name) desplegado con exito."
}

Write-Host "`n=== Orquestacion Finalizada ==="
