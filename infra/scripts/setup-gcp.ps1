# AgentOps GCP Setup Script for Windows PowerShell
# Run this script in PowerShell (Administrator not required for most operations)

# Stop on errors
$ErrorActionPreference = "Stop"

Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   AgentOps GCP Infrastructure Setup   ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Check if PROJECT_ID is set
if (-not $env:PROJECT_ID) {
    Write-Host "Error: PROJECT_ID environment variable not set" -ForegroundColor Red
    Write-Host "Usage: `$env:PROJECT_ID='your-project-id'; .\setup-gcp.ps1"
    exit 1
}

# Set default region if not provided
if (-not $env:REGION) {
    $env:REGION = "us-central1"
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Project ID: $env:PROJECT_ID"
Write-Host "  Region: $env:REGION"
Write-Host ""

# Confirm before proceeding
$confirmation = Read-Host "Proceed with setup? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "Setup cancelled."
    exit 0
}

# Set gcloud project
Write-Host "`n[1/9] Setting gcloud project..." -ForegroundColor Green
gcloud config set project $env:PROJECT_ID

# Get project number
$env:PROJECT_NUMBER = (gcloud projects describe $env:PROJECT_ID --format='value(projectNumber)')
Write-Host "  Project Number: $env:PROJECT_NUMBER"

# Enable required APIs
Write-Host "`n[2/9] Enabling required GCP APIs..." -ForegroundColor Green
Write-Host "  This may take 2-3 minutes..."
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  cloudscheduler.googleapis.com `
  pubsub.googleapis.com `
  monitoring.googleapis.com `
  logging.googleapis.com `
  firestore.googleapis.com `
  aiplatform.googleapis.com `
  secretmanager.googleapis.com `
  --project=$env:PROJECT_ID

Write-Host "✓ APIs enabled" -ForegroundColor Green

# Create Service Accounts
Write-Host "`n[3/9] Creating service accounts..." -ForegroundColor Green

# Supervisor SA
try {
    gcloud iam service-accounts describe "supervisor-sa@$env:PROJECT_ID.iam.gserviceaccount.com" --project=$env:PROJECT_ID 2>$null
    Write-Host "  supervisor-sa already exists"
} catch {
    gcloud iam service-accounts create supervisor-sa `
      --display-name="Supervisor Agent SA" `
      --project=$env:PROJECT_ID
    Write-Host "  ✓ Created supervisor-sa" -ForegroundColor Green
}

# Fixer SA
try {
    gcloud iam service-accounts describe "fixer-sa@$env:PROJECT_ID.iam.gserviceaccount.com" --project=$env:PROJECT_ID 2>$null
    Write-Host "  fixer-sa already exists"
} catch {
    gcloud iam service-accounts create fixer-sa `
      --display-name="Fixer Agent SA" `
      --project=$env:PROJECT_ID
    Write-Host "  ✓ Created fixer-sa" -ForegroundColor Green
}

# Dashboard SA
try {
    gcloud iam service-accounts describe "dashboard-sa@$env:PROJECT_ID.iam.gserviceaccount.com" --project=$env:PROJECT_ID 2>$null
    Write-Host "  dashboard-sa already exists"
} catch {
    gcloud iam service-accounts create dashboard-sa `
      --display-name="Dashboard SA" `
      --project=$env:PROJECT_ID
    Write-Host "  ✓ Created dashboard-sa" -ForegroundColor Green
}

# Grant IAM permissions - Supervisor
Write-Host "`n[4/9] Granting IAM permissions for supervisor-sa..." -ForegroundColor Green

$supervisorSA = "serviceAccount:supervisor-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$supervisorSA `
  --role="roles/monitoring.viewer" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$supervisorSA `
  --role="roles/logging.viewer" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$supervisorSA `
  --role="roles/pubsub.publisher" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$supervisorSA `
  --role="roles/aiplatform.user" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$supervisorSA `
  --role="roles/datastore.user" `
  --condition=None 2>$null

Write-Host "✓ Supervisor IAM configured" -ForegroundColor Green

# Grant IAM permissions - Fixer
Write-Host "`n[5/9] Granting IAM permissions for fixer-sa..." -ForegroundColor Green

$fixerSA = "serviceAccount:fixer-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$fixerSA `
  --role="roles/run.admin" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$fixerSA `
  --role="roles/cloudbuild.builds.editor" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$fixerSA `
  --role="roles/pubsub.subscriber" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$fixerSA `
  --role="roles/iam.serviceAccountUser" `
  --condition=None 2>$null

Write-Host "✓ Fixer IAM configured" -ForegroundColor Green

# Grant IAM permissions - Dashboard
Write-Host "`n[6/9] Granting IAM permissions for dashboard-sa..." -ForegroundColor Green

$dashboardSA = "serviceAccount:dashboard-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$dashboardSA `
  --role="roles/datastore.viewer" `
  --condition=None 2>$null

gcloud projects add-iam-policy-binding $env:PROJECT_ID `
  --member=$dashboardSA `
  --role="roles/run.viewer" `
  --condition=None 2>$null

Write-Host "✓ Dashboard IAM configured" -ForegroundColor Green

# Create Pub/Sub topic and subscription
Write-Host "`n[7/9] Setting up Pub/Sub..." -ForegroundColor Green

try {
    gcloud pubsub topics describe agent-actions --project=$env:PROJECT_ID 2>$null
    Write-Host "  agent-actions topic already exists"
} catch {
    gcloud pubsub topics create agent-actions --project=$env:PROJECT_ID
    Write-Host "  ✓ Created agent-actions topic" -ForegroundColor Green
}

try {
    gcloud pubsub subscriptions describe agent-actions-sub --project=$env:PROJECT_ID 2>$null
    Write-Host "  agent-actions-sub subscription already exists"
} catch {
    gcloud pubsub subscriptions create agent-actions-sub `
      --topic=agent-actions `
      --ack-deadline=60 `
      --project=$env:PROJECT_ID
    Write-Host "  ✓ Created agent-actions-sub subscription" -ForegroundColor Green
}

# Initialize Firestore
Write-Host "`n[8/9] Initializing Firestore..." -ForegroundColor Green

try {
    gcloud firestore databases describe --project=$env:PROJECT_ID 2>$null
    Write-Host "  Firestore database already exists"
} catch {
    gcloud firestore databases create `
      --location=$env:REGION `
      --type=firestore-native `
      --project=$env:PROJECT_ID
    Write-Host "  ✓ Created Firestore database" -ForegroundColor Green
}

# Create Cloud Scheduler job placeholder
Write-Host "`n[9/9] Setting up Cloud Scheduler..." -ForegroundColor Green
Write-Host "  Note: Cloud Scheduler job will be created after supervisor-api deployment"

# Summary
Write-Host "`n╔═══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        Setup Complete! ✓              ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Resources Created:" -ForegroundColor Yellow
Write-Host "  ✓ Service Accounts: supervisor-sa, fixer-sa, dashboard-sa"
Write-Host "  ✓ IAM Permissions: Configured"
Write-Host "  ✓ Pub/Sub: agent-actions topic + subscription"
Write-Host "  ✓ Firestore: Initialized"
Write-Host "  ✓ APIs: All enabled"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Deploy services: .\infra\scripts\deploy-all.ps1"
Write-Host "  2. Verify deployment: gcloud run services list --project=$env:PROJECT_ID"
Write-Host "  3. Access dashboard: (URL will be shown after deployment)"
Write-Host ""
Write-Host "Happy Hacking! 🚀" -ForegroundColor Green

# Save environment variables for future use
$envContent = @"
# AgentOps Environment Variables
# Source this file: . .\env.ps1

`$env:PROJECT_ID="$env:PROJECT_ID"
`$env:REGION="$env:REGION"
`$env:PROJECT_NUMBER="$env:PROJECT_NUMBER"
"@

$envContent | Out-File -FilePath "..\..\env.ps1" -Encoding UTF8
Write-Host "`nEnvironment variables saved to env.ps1" -ForegroundColor Cyan
Write-Host "To use in a new session, run: . .\env.ps1" -ForegroundColor Cyan