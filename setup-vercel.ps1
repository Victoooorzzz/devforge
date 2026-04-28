$ErrorActionPreference = "Stop"

if (-not $env:VERCEL_TOKEN) {
    Write-Error "La variable de entorno VERCEL_TOKEN no esta configurada."
    Write-Host "Por favor configurala ejecutando:"
    Write-Host "$env:VERCEL_TOKEN = \"tu-token-aqui\""
    exit 1
}

$root = $PSScriptRoot

Write-Host "=== Setup Vercel Monorepo via API ==="

$apps = @(
    @{ Name = "devforge-site";  Root = "apps/devforge-site/frontend"  },
    @{ Name = "filecleaner";    Root = "apps/filecleaner/frontend"    },
    @{ Name = "invoicefollow";  Root = "apps/invoicefollow/frontend"  },
    @{ Name = "pricetrackr";    Root = "apps/pricetrackr/frontend"    },
    @{ Name = "webhookmonitor"; Root = "apps/webhookmonitor/frontend" },
    @{ Name = "feedbacklens";   Root = "apps/feedbacklens/frontend"   }
)

foreach ($app in $apps) {
    Write-Host "================================================="
    Write-Host "Procesando $($app.Name)..."

    # 1. Crear el proyecto en Vercel
    Write-Host "  -- Creando proyecto en Vercel..."
    & vercel project add $app.Name --token $env:VERCEL_TOKEN | Out-Null

    # 2. Configurar Build settings via API de Vercel
    Write-Host "  -- Configurando settings via Vercel API..."
    $apiUrl = "https://api.vercel.com/v9/projects/$($app.Name)"
    
    $headers = @{
        "Authorization" = "Bearer $($env:VERCEL_TOKEN)"
        "Content-Type"  = "application/json"
    }

    $body = @{
        installCommand = "pnpm install"
        buildCommand   = "cd ../../../ && pnpm turbo build --filter=$($app.Name)"
        rootDirectory  = $app.Root
        framework      = "nextjs"
    } | ConvertTo-Json -Depth 5

    try {
        Invoke-RestMethod -Uri $apiUrl -Method Patch -Headers $headers -Body $body | Out-Null
        Write-Host "  OK: Proyecto configurado correctamente."
    } catch {
        Write-Warning "  FAIL: Fallo al configurar el proyecto por API."
    }

    # 3. Desplegar
    Write-Host "  -- Desplegando a produccion (desde root)..."
    
    # Vinculamos localmente para que vercel sepa de que proyecto hablamos, pero sin duplicar paths
    & vercel link --project $app.Name --yes --token $env:VERCEL_TOKEN --cwd $root | Out-Null
    
    # Desplegamos usando el contexto del root
    & vercel deploy --prod --yes --token $env:VERCEL_TOKEN --cwd $root -e NEXT_PUBLIC_API_URL="" --build-env TURBO_TOKEN="" --build-env VERCEL_TOKEN=$env:VERCEL_TOKEN

    Write-Host "  -- Despliegue completado."
}

Write-Host "=== Setup Finalizado ==="