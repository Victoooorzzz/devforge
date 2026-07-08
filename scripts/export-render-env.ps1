param(
    [string]$ServiceName = "devforge-universal-backend",
    [switch]$TriggerDeploy
)

$ErrorActionPreference = "Stop"

$envFile = Join-Path (Get-Item -Path $PSScriptRoot).Parent.FullName ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env not found at $envFile"
    exit 1
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*([^#\s][^=]*)\s*=\s*['""]?(.*?)['""]?\s*$") {
        $key = $matches[1].Trim()
        $val = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
}

$renderApiKey = [Environment]::GetEnvironmentVariable("RENDER_API_KEY", "Process")
if (-not $renderApiKey) {
    Write-Error "RENDER_API_KEY is required in your environment or .env file."
    exit 1
}

$feedbackLensDefaults = @{
    FEEDBACKLENS_ANALYSIS_ENGINE = "local_transformers"
    FEEDBACKLENS_SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
    FEEDBACKLENS_URGENCY_MODEL   = "cross-encoder/nli-deberta-v3-xsmall"
}

foreach ($entry in $feedbackLensDefaults.GetEnumerator()) {
    if (-not [Environment]::GetEnvironmentVariable($entry.Key, "Process")) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
}

$headers = @{
    Authorization = "Bearer $renderApiKey"
    Accept        = "application/json"
}

$services = Invoke-RestMethod `
    -Method GET `
    -Uri "https://api.render.com/v1/services?limit=100" `
    -Headers $headers

$service = @($services | Where-Object { $_.service.name -eq $ServiceName } | Select-Object -First 1)
if ($service.Count -eq 0) {
    Write-Error "Render service '$ServiceName' was not found."
    exit 1
}

$serviceId = $service[0].service.id
$keys = @(
    "DATABASE_URL",
    "JWT_SECRET",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "POLAR_SERVER",
    "POLAR_API_URL",
    "POLAR_ACCESS_TOKEN",
    "POLAR_WEBHOOK_SECRET",
    "POLAR_PRODUCT_ID_FILECLEANER",
    "POLAR_PRODUCT_ID_INVOICEFOLLOW",
    "POLAR_PRODUCT_ID_PRICETRACKR",
    "POLAR_PRODUCT_ID_WEBHOOKMONITOR",
    "POLAR_PRODUCT_ID_FEEDBACKLENS",
    "POLAR_PRODUCT_ID_FILECLEANER_PRO",
    "POLAR_PRODUCT_ID_INVOICEFOLLOW_PRO",
    "POLAR_PRODUCT_ID_PRICETRACKR_PRO",
    "POLAR_PRODUCT_ID_WEBHOOKMONITOR_PRO",
    "POLAR_PRODUCT_ID_FEEDBACKLENS_PRO",
    "POLAR_PRODUCT_ID_FILECLEANER_TEAM",
    "POLAR_PRODUCT_ID_INVOICEFOLLOW_TEAM",
    "POLAR_PRODUCT_ID_PRICETRACKR_TEAM",
    "POLAR_PRODUCT_ID_WEBHOOKMONITOR_TEAM",
    "POLAR_PRODUCT_ID_FEEDBACKLENS_TEAM",
    "FRONTEND_URL",
    "ALLOWED_ORIGINS",
    "CRON_SECRET",
    "ADMIN_SECRET",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "MICROSOFT_CLIENT_ID",
    "MICROSOFT_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "MICROSOFT_REDIRECT_URI",
    "FEEDBACKLENS_ANALYSIS_ENGINE",
    "FEEDBACKLENS_SENTIMENT_MODEL",
    "FEEDBACKLENS_URGENCY_MODEL",
    "GEMINI_API_KEY",
    "S3_ENDPOINT_URL",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET_NAME"
)

foreach ($key in $keys) {
    $value = [Environment]::GetEnvironmentVariable($key, "Process")
    if (-not $value) {
        Write-Warning "Skipping missing env var: $key"
        continue
    }

    $body = @{ value = $value } | ConvertTo-Json
    Invoke-RestMethod `
        -Method PUT `
        -Uri "https://api.render.com/v1/services/$serviceId/env-vars/$key" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body | Out-Null

    Write-Host "Updated: $key"
}

if ($TriggerDeploy) {
    Invoke-RestMethod `
        -Method POST `
        -Uri "https://api.render.com/v1/services/$serviceId/deploys" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body "{}" | Out-Null

    Write-Host "Triggered Render deploy for $ServiceName"
}

Write-Host "Render env export complete."
