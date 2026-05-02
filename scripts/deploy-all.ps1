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
    Write-Error "La variable de entorno VERCEL_TOKEN no esta configurada."
    exit 1
}

# ─── Helper: upsert env var via API REST (evita el bug del pipe con CLI) ───
function Set-VercelEnvVar {
    param(
        [string]$ProjectId,
        [string]$Key,
        [string]$Value,
        [string]$Target = "production"
    )

    $headers = @{ Authorization = "Bearer $env:VERCEL_TOKEN" }

    # Listar variables existentes del proyecto
    $existing = Invoke-RestMethod `
        -Uri "https://api.vercel.com/v9/projects/$ProjectId/env" `
        -Headers $headers

    $existingVar = $existing.envs | Where-Object { $_.key -eq $Key -and $_.target -contains $Target }

    if ($existingVar) {
        # Actualizar la existente
        $body = @{ value = $Value } | ConvertTo-Json
        Invoke-RestMethod `
            -Uri "https://api.vercel.com/v9/projects/$ProjectId/env/$($existingVar.id)" `
            -Method PATCH `
            -Headers $headers `
            -ContentType "application/json" `
            -Body $body | Out-Null
        Write-Host "    - Actualizada: $Key"
    }
    else {
        # Crear nueva
        $body = @{
            key    = $Key
            value  = $Value
            type   = "plain"
            target = @($Target)
        } | ConvertTo-Json
        Invoke-RestMethod `
            -Uri "https://api.vercel.com/v9/projects/$ProjectId/env" `
            -Method POST `
            -Headers $headers `
            -ContentType "application/json" `
            -Body $body | Out-Null
        Write-Host "    - Creada: $Key"
    }
}
# ────────────────────────────────────────────────────────────────────────────

$apps = @(
    @{ Name = "devforge-site"; Root = "apps/devforge-site/frontend" },
    @{ Name = "filecleaner"; Root = "apps/filecleaner/frontend" },
    @{ Name = "invoicefollow"; Root = "apps/invoicefollow/frontend" },
    @{ Name = "pricetrackr"; Root = "apps/pricetrackr/frontend" },
    @{ Name = "webhookmonitor"; Root = "apps/webhookmonitor/frontend" },
    @{ Name = "feedbacklens"; Root = "apps/feedbacklens/frontend" }
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

# Obtener orgId una sola vez
Write-Host "Obteniendo informacion de la cuenta..."
$me = Invoke-RestMethod -Uri "https://api.vercel.com/v2/user" -Headers @{ Authorization = "Bearer $env:VERCEL_TOKEN" }
$orgId = $me.user.id

foreach ($app in $apps) {
    Write-Host "-------------------------------------------------"
    Write-Host "Procesando: $($app.Name)"

    $headers = @{ Authorization = "Bearer $env:VERCEL_TOKEN" }

    # Paso 1 - Crear proyecto si no existe
    Write-Host "  [1/3] Configurando proyecto en Vercel..."
    try {
        Invoke-RestMethod `
            -Uri "https://api.vercel.com/v9/projects" `
            -Method POST `
            -Headers $headers `
            -ContentType "application/json" `
            -Body (@{ name = $app.Name; framework = "nextjs" } | ConvertTo-Json) | Out-Null
        Write-Host "  OK: Proyecto creado."
    }
    catch {
        # Ya existe, continuar
    }

    # Actualizar configuracion
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
        $project = Invoke-RestMethod `
            -Uri "https://api.vercel.com/v9/projects/$($app.Name)" `
            -Method PATCH `
            -Headers $headers `
            -ContentType "application/json" `
            -Body $config
        Write-Host "  OK: Configuracion actualizada."
    }
    catch {
        try {
            $project = Invoke-RestMethod `
                -Uri "https://api.vercel.com/v9/projects/$($app.Name)" `
                -Method GET `
                -Headers $headers
        }
        catch {
            Write-Warning "  FAIL: No se pudo obtener el proyecto '$($app.Name)'."
            continue
        }
    }

    # Paso 1.5 - Inyectar env vars via API REST (sin pipe, sin CLI)
    Write-Host "  [1.5/3] Inyectando variables de entorno..."

    if ($env:NEXT_PUBLIC_API_URL) {
        Set-VercelEnvVar -ProjectId $project.id -Key "NEXT_PUBLIC_API_URL" -Value $env:NEXT_PUBLIC_API_URL
    }

    $variantKey = "NEXT_PUBLIC_LS_VARIANT_ID_$($app.Name.ToUpper())"
    $variantValue = [Environment]::GetEnvironmentVariable($variantKey, "Process")

    if ($variantValue) {
        # Variable generica que usa el frontend
        Set-VercelEnvVar -ProjectId $project.id -Key "NEXT_PUBLIC_LS_VARIANT_ID" -Value $variantValue
        # Variable especifica por si acaso
        Set-VercelEnvVar -ProjectId $project.id -Key $variantKey -Value $variantValue
    }

    # Paso 2 - Inyectar .vercel/project.json
    Write-Host "  [2/3] Inyectando .vercel/project.json..."
    $vercelDir = Join-Path $monorepoRoot ".vercel"
    if (-not (Test-Path $vercelDir)) { New-Item -ItemType Directory -Path $vercelDir | Out-Null }

    $projectJson = @{
        orgId     = $orgId
        projectId = $project.id
    } | ConvertTo-Json

    Set-Content -Path (Join-Path $vercelDir "project.json") -Value $projectJson -Force

    # Paso 3 - Deploy
    Write-Host "  [3/3] Desplegando..."
    & vercel deploy --prod --yes --token $env:VERCEL_TOKEN --cwd $monorepoRoot

    Write-Host "  OK: $($app.Name) desplegado."
}

Write-Host "`n=== Orquestacion Finalizada ==="