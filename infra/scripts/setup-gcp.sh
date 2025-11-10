#!/bin/bash

# AgentOps GCP Setup Script
# This script provisions all required GCP resources for AgentOps

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   AgentOps GCP Infrastructure Setup   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: PROJECT_ID environment variable not set${NC}"
    echo "Usage: export PROJECT_ID=your-project-id && ./setup-gcp.sh"
    exit 1
fi

# Set default region if not provided
REGION=${REGION:-us-central1}

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo ""

# Confirm before proceeding
read -p "Proceed with setup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Set gcloud project
echo -e "\n${GREEN}[1/9] Setting gcloud project...${NC}"
gcloud config set project $PROJECT_ID

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
echo "  Project Number: $PROJECT_NUMBER"

# Enable required APIs
echo -e "\n${GREEN}[2/9] Enabling required GCP APIs...${NC}"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  pubsub.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

echo -e "${GREEN}✓ APIs enabled${NC}"

# Create Service Accounts
echo -e "\n${GREEN}[3/9] Creating service accounts...${NC}"

# Supervisor SA
if gcloud iam service-accounts describe supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID &>/dev/null; then
    echo "  supervisor-sa already exists"
else
    gcloud iam service-accounts create supervisor-sa \
      --display-name="Supervisor Agent SA" \
      --project=$PROJECT_ID
    echo "  ✓ Created supervisor-sa"
fi

# Fixer SA
if gcloud iam service-accounts describe fixer-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID &>/dev/null; then
    echo "  fixer-sa already exists"
else
    gcloud iam service-accounts create fixer-sa \
      --display-name="Fixer Agent SA" \
      --project=$PROJECT_ID
    echo "  ✓ Created fixer-sa"
fi

# Dashboard SA
if gcloud iam service-accounts describe dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID &>/dev/null; then
    echo "  dashboard-sa already exists"
else
    gcloud iam service-accounts create dashboard-sa \
      --display-name="Dashboard SA" \
      --project=$PROJECT_ID
    echo "  ✓ Created dashboard-sa"
fi

# Grant IAM permissions - Supervisor
echo -e "\n${GREEN}[4/9] Granting IAM permissions for supervisor-sa...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.viewer" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

echo -e "${GREEN}✓ Supervisor IAM configured${NC}"

# Grant IAM permissions - Fixer
echo -e "\n${GREEN}[5/9] Granting IAM permissions for fixer-sa...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

echo -e "${GREEN}✓ Fixer IAM configured${NC}"

# Grant IAM permissions - Dashboard
echo -e "\n${GREEN}[6/9] Granting IAM permissions for dashboard-sa...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.viewer" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.viewer" \
  --condition=None 2>/dev/null || echo "  (role already granted)"

echo -e "${GREEN}✓ Dashboard IAM configured${NC}"

# Create Pub/Sub topic and subscription
echo -e "\n${GREEN}[7/9] Setting up Pub/Sub...${NC}"
if gcloud pubsub topics describe agent-actions --project=$PROJECT_ID &>/dev/null; then
    echo "  agent-actions topic already exists"
else
    gcloud pubsub topics create agent-actions --project=$PROJECT_ID
    echo "  ✓ Created agent-actions topic"
fi

if gcloud pubsub subscriptions describe agent-actions-sub --project=$PROJECT_ID &>/dev/null; then
    echo "  agent-actions-sub subscription already exists"
else
    gcloud pubsub subscriptions create agent-actions-sub \
      --topic=agent-actions \
      --ack-deadline=60 \
      --project=$PROJECT_ID
    echo "  ✓ Created agent-actions-sub subscription"
fi

# Initialize Firestore
echo -e "\n${GREEN}[8/9] Initializing Firestore...${NC}"
if gcloud firestore databases describe --project=$PROJECT_ID &>/dev/null; then
    echo "  Firestore database already exists"
else
    gcloud firestore databases create \
      --location=$REGION \
      --type=firestore-native \
      --project=$PROJECT_ID
    echo "  ✓ Created Firestore database"
fi

# Create Cloud Scheduler job (placeholder - will be updated after supervisor deployment)
echo -e "\n${GREEN}[9/9] Setting up Cloud Scheduler...${NC}"
if gcloud scheduler jobs describe health-scan-job --location=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "  health-scan-job already exists"
else
    echo "  Note: Cloud Scheduler job will be created after supervisor-api deployment"
fi

# Summary
echo -e "\n${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Setup Complete! ✓              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Resources Created:${NC}"
echo "  ✓ Service Accounts: supervisor-sa, fixer-sa, dashboard-sa"
echo "  ✓ IAM Permissions: Configured"
echo "  ✓ Pub/Sub: agent-actions topic + subscription"
echo "  ✓ Firestore: Initialized"
echo "  ✓ APIs: All enabled"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Deploy services: cd ../../ && ./infra/scripts/deploy-all.sh"
echo "  2. Verify deployment: gcloud run services list --project=$PROJECT_ID"
echo "  3. Access dashboard: (URL will be shown after deployment)"
echo ""
echo -e "${GREEN}Happy Hacking! 🚀${NC}"