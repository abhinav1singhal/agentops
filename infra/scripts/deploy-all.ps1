# AgentOps Complete Deployment Script for Windows PowerShell
# Deploys all services in the correct order with dependencies

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Blue
Write-Host "    AgentOps Complete Deployment" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Load environment variables
if (Test-Path "..\..\..\env.ps1") {
    . "..\..\..\env.ps1"
    Write-Host "[OK] Loaded env.ps1 file" -ForegroundColor Green
}
elseif (Test-Path "..\..\.env") {
    # Try to read .env file and convert to PowerShell format
    Get-Content "..\..\.env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    Write-Host "[OK] Loaded .env file" -ForegroundColor Green
}
else {
    Write-Host "[ERROR] No env.ps1 or .env file found" -ForegroundColor Red
    Write-Host "Please run setup-gcp.ps1 first or create .env file" -ForegroundColor Red
    exit 1
}

# Validate required variables
$requiredVars = @("PROJECT_ID", "REGION")
foreach ($var in $requiredVars) {
    if (-not (Test-Path "env:$var")) {
        Write-Host "[ERROR] $var is not set" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Project: $env:PROJECT_ID"
Write-Host "  Region: $env:REGION"
Write-Host "  Services: demo-app-a, demo-app-b, supervisor-api, fixer-agent, dashboard-web"
Write-Host ""

# Confirm deployment
$confirmation = Read-Host "Deploy all services? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Function to deploy a Cloud Run service
function Deploy-Service {
    param(
        [string]$ServiceName,
        [string]$ServiceDir,
        [string]$ServiceAccount,
        [int]$MinInstances = 0,
        [int]$MaxInstances = 10,
        [int]$Port = 8080,
        [hashtable]$EnvVars = @{}
    )
    
    Write-Host ""
    Write-Host "[Deploying $ServiceName]" -ForegroundColor Green
    
    $originalLocation = Get-Location
    Set-Location "..\..\apps\$ServiceDir"
    
    try {
        # Build and submit to Cloud Build
        Write-Host "  Building container..." -ForegroundColor Cyan
        gcloud builds submit --tag "gcr.io/$env:PROJECT_ID/$ServiceName" --project=$env:PROJECT_ID --quiet
        
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed for $ServiceName"
        }
        
        # Prepare env vars string
        $envVarString = "PROJECT_ID=$env:PROJECT_ID,REGION=$env:REGION"
        foreach ($key in $EnvVars.Keys) {
            $value = $EnvVars[$key]
            $envVarString += ",$key=$value"
        }
        
        # Deploy to Cloud Run
        Write-Host "  Deploying to Cloud Run..." -ForegroundColor Cyan
        gcloud run deploy $ServiceName --image "gcr.io/$env:PROJECT_ID/$ServiceName" --platform managed --region $env:REGION --service-account $ServiceAccount --min-instances $MinInstances --max-instances $MaxInstances --port $Port --allow-unauthenticated --set-env-vars $envVarString --project=$env:PROJECT_ID --quiet
        
        if ($LASTEXITCODE -ne 0) {
            throw "Deployment failed for $ServiceName"
        }
        
        # Get service URL
        $serviceUrl = (gcloud run services describe $ServiceName --platform managed --region $env:REGION --format 'value(status.url)' --project=$env:PROJECT_ID)
        
        Write-Host "  [OK] $ServiceName deployed" -ForegroundColor Green
        Write-Host "  URL: $serviceUrl" -ForegroundColor Blue
        
        return $serviceUrl
    }
    catch {
        Write-Host "  [ERROR] Failed to deploy $ServiceName" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
    finally {
        Set-Location $originalLocation
    }
}

# Deploy Demo Apps First
Write-Host ""
Write-Host "=== Phase 1: Demo Applications ===" -ForegroundColor Yellow

$demoAppASA = "dashboard-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

try {
    $demoAppA_URL = Deploy-Service -ServiceName "demo-app-a" -ServiceDir "demo-app-a" -ServiceAccount $demoAppASA -MinInstances 0 -MaxInstances 5 -Port 8080
}
catch {
    Write-Host "[WARNING] Failed to deploy demo-app-a. Continuing..." -ForegroundColor Yellow
    $demoAppA_URL = "https://demo-app-a-failed.run.app"
}

try {
    $demoAppB_URL = Deploy-Service -ServiceName "demo-app-b" -ServiceDir "demo-app-b" -ServiceAccount $demoAppASA -MinInstances 0 -MaxInstances 5 -Port 8080
}
catch {
    Write-Host "[WARNING] Failed to deploy demo-app-b. Continuing..." -ForegroundColor Yellow
    $demoAppB_URL = "https://demo-app-b-failed.run.app"
}

# Deploy Fixer Agent
Write-Host ""
Write-Host "=== Phase 2: Fixer Agent ===" -ForegroundColor Yellow

$fixerSA = "fixer-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

try {
    $fixer_URL = Deploy-Service -ServiceName "fixer-agent" -ServiceDir "fixer-agent" -ServiceAccount $fixerSA -MinInstances 1 -MaxInstances 3 -Port 8081
    
    # Configure Pub/Sub to push to Fixer
    Write-Host "  Configuring Pub/Sub push subscription..." -ForegroundColor Cyan
    
    try {
        gcloud pubsub subscriptions delete agent-actions-sub --project=$env:PROJECT_ID --quiet 2>$null
    }
    catch {
        # Subscription might not exist
    }
    
    gcloud pubsub subscriptions create agent-actions-sub --topic=agent-actions --push-endpoint="$fixer_URL/actions/execute" --ack-deadline=60 --project=$env:PROJECT_ID
    
    Write-Host "  [OK] Pub/Sub configured" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to deploy fixer-agent!" -ForegroundColor Red
    $fixer_URL = "https://fixer-agent-failed.run.app"
}

# Deploy Supervisor API
Write-Host ""
Write-Host "=== Phase 3: Supervisor API ===" -ForegroundColor Yellow

# Prepare target services JSON (escape quotes properly)
$targetServicesJSON = '[{\"name\":\"demo-app-a\",\"region\":\"' + $env:REGION + '\"},{\"name\":\"demo-app-b\",\"region\":\"' + $env:REGION + '\"}]'

# Set default thresholds if not set
if (-not $env:ERROR_THRESHOLD) {
    $env:ERROR_THRESHOLD = "5.0"
}
if (-not $env:LATENCY_P95_THRESHOLD_MS) {
    $env:LATENCY_P95_THRESHOLD_MS = "600"
}

$supervisorEnvVars = @{
    "TARGET_SERVICES_JSON" = $targetServicesJSON
    "PUBSUB_TOPIC" = "agent-actions"
    "ERROR_THRESHOLD" = $env:ERROR_THRESHOLD
    "LATENCY_P95_THRESHOLD_MS" = $env:LATENCY_P95_THRESHOLD_MS
    "GEMINI_MODEL" = "gemini-1.5-flash"
}

$supervisorSA = "supervisor-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

try {
    $supervisor_URL = Deploy-Service -ServiceName "supervisor-api" -ServiceDir "supervisor-api" -ServiceAccount $supervisorSA -MinInstances 1 -MaxInstances 5 -Port 8080 -EnvVars $supervisorEnvVars
    
    # Create Cloud Scheduler job
    Write-Host ""
    Write-Host "[Configuring Cloud Scheduler]" -ForegroundColor Green
    
    try {
        gcloud scheduler jobs delete health-scan-job --location=$env:REGION --project=$env:PROJECT_ID --quiet 2>$null
    }
    catch {
        # Job might not exist
    }
    
    gcloud scheduler jobs create http health-scan-job --location=$env:REGION --schedule="*/2 * * * *" --uri="$supervisor_URL/health/scan" --http-method=POST --oidc-service-account-email=$supervisorSA --project=$env:PROJECT_ID
    
    Write-Host "  [OK] Cloud Scheduler configured (runs every 2 minutes)" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to deploy supervisor-api!" -ForegroundColor Red
    $supervisor_URL = "https://supervisor-api-failed.run.app"
}

# Deploy Dashboard
Write-Host ""
Write-Host "=== Phase 4: Dashboard ===" -ForegroundColor Yellow

Set-Location "..\..\apps\dashboard-web"

try {
    # Create .env.local for build
    $envLocalContent = @"
NEXT_PUBLIC_SUPERVISOR_API_URL=$supervisor_URL
NEXT_PUBLIC_PROJECT_ID=$env:PROJECT_ID
NEXT_PUBLIC_REGION=$env:REGION
"@
    $envLocalContent | Out-File -FilePath ".env.local" -Encoding UTF8
    
    Write-Host "  Building container..." -ForegroundColor Cyan
    gcloud builds submit --tag "gcr.io/$env:PROJECT_ID/dashboard-web" --project=$env:PROJECT_ID --quiet
    
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed for dashboard-web"
    }
    
    Write-Host "  Deploying to Cloud Run..." -ForegroundColor Cyan
    $dashboardSA = "dashboard-sa@$env:PROJECT_ID.iam.gserviceaccount.com"
    gcloud run deploy dashboard-web --image "gcr.io/$env:PROJECT_ID/dashboard-web" --platform managed --region $env:REGION --service-account $dashboardSA --min-instances 1 --max-instances 3 --port 3000 --allow-unauthenticated --set-env-vars "NEXT_PUBLIC_SUPERVISOR_API_URL=$supervisor_URL,NEXT_PUBLIC_PROJECT_ID=$env:PROJECT_ID,NEXT_PUBLIC_REGION=$env:REGION" --project=$env:PROJECT_ID --quiet
    
    $dashboard_URL = (gcloud run services describe dashboard-web --platform managed --region $env:REGION --format 'value(status.url)' --project=$env:PROJECT_ID)
    
    Write-Host "  [OK] Dashboard deployed" -ForegroundColor Green
    Write-Host "  URL: $dashboard_URL" -ForegroundColor Blue
}
catch {
    Write-Host "[WARNING] Failed to deploy dashboard" -ForegroundColor Yellow
    $dashboard_URL = "https://dashboard-web-failed.run.app"
}

Set-Location ..\..\infra\scripts

# Save URLs to file
$urlsContent = @"
AgentOps Deployment URLs
========================

Dashboard: $dashboard_URL
Supervisor API: $supervisor_URL
Fixer Agent: $fixer_URL
Demo App A: $demoAppA_URL
Demo App B: $demoAppB_URL

Quick Test Commands (PowerShell):
==================================

# Check supervisor health
Invoke-RestMethod -Uri "$supervisor_URL/health"

# Trigger manual scan
Invoke-RestMethod -Method Post -Uri "$supervisor_URL/health/scan"

# View dashboard
Start-Process "$dashboard_URL"

# Inject fault in Demo App A
Invoke-RestMethod -Method Post -Uri "$demoAppA_URL/fault/enable?type=5xx&error_rate=15&duration=300"

# Check fault status
Invoke-RestMethod -Uri "$demoAppA_URL/fault/status"

# View service status
Invoke-RestMethod -Uri "$supervisor_URL/services/status"

# List incidents
Invoke-RestMethod -Uri "$supervisor_URL/incidents"

"@

$urlsPath = Join-Path -Path $PSScriptRoot -ChildPath "..\..\deployment-urls.txt"
$urlsContent | Out-File -FilePath $urlsPath -Encoding UTF8

# Final summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Blue
Write-Host "     Deployment Complete!" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "All services deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Yellow
Write-Host "  Dashboard:      $dashboard_URL" -ForegroundColor Blue
Write-Host "  Supervisor API: $supervisor_URL" -ForegroundColor Blue
Write-Host "  Fixer Agent:    $fixer_URL" -ForegroundColor Blue
Write-Host "  Demo App A:     $demoAppA_URL" -ForegroundColor Blue
Write-Host "  Demo App B:     $demoAppB_URL" -ForegroundColor Blue
Write-Host ""
Write-Host "URLs saved to: deployment-urls.txt" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open dashboard: Start-Process `"$dashboard_URL`"" -ForegroundColor Cyan
Write-Host "  2. Wait 2-3 minutes for first health scan" -ForegroundColor Cyan
Write-Host "  3. Test fault injection with commands in deployment-urls.txt" -ForegroundColor Cyan
Write-Host ""
Write-Host "Happy Hacking!" -ForegroundColor Green