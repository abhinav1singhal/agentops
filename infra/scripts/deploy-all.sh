#!/bin/bash

# AgentOps Complete Deployment Script
# Deploys all services in the correct order with dependencies

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AgentOps Complete Deployment       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# Load environment variables
if [ -f "../../.env" ]; then
    export $(cat ../../.env | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Loaded .env file${NC}"
else
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.template to .env and configure it"
    exit 1
fi

# Validate required variables
REQUIRED_VARS=("PROJECT_ID" "REGION")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: $var is not set${NC}"
        exit 1
    fi
done

echo -e "${YELLOW}Deployment Configuration:${NC}"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Services: demo-app-a, demo-app-b, supervisor-api, fixer-agent, dashboard-web"
echo ""

# Confirm deployment
read -p "Deploy all services? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Function to deploy a Cloud Run service
deploy_service() {
    local SERVICE_NAME=$1
    local SERVICE_DIR=$2
    local SERVICE_ACCOUNT=$3
    local MIN_INSTANCES=${4:-0}
    local MAX_INSTANCES=${5:-10}
    local PORT=${6:-8080}
    
    echo -e "\n${GREEN}[Deploying $SERVICE_NAME]${NC}"
    
    cd "../../apps/$SERVICE_DIR"
    
    # Build and submit to Cloud Build
    echo "  Building container..."
    gcloud builds submit \
      --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
      --project=$PROJECT_ID \
      --quiet
    
    # Deploy to Cloud Run
    echo "  Deploying to Cloud Run..."
    gcloud run deploy $SERVICE_NAME \
      --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
      --platform managed \
      --region $REGION \
      --service-account $SERVICE_ACCOUNT \
      --min-instances $MIN_INSTANCES \
      --max-instances $MAX_INSTANCES \
      --port $PORT \
      --allow-unauthenticated \
      --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION" \
      --project=$PROJECT_ID \
      --quiet
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
      --platform managed \
      --region $REGION \
      --format 'value(status.url)' \
      --project=$PROJECT_ID)
    
    echo -e "${GREEN}  ✓ $SERVICE_NAME deployed${NC}"
    echo -e "${BLUE}  URL: $SERVICE_URL${NC}"
    
    cd - > /dev/null
    
    # Return the URL
    echo "$SERVICE_URL"
}

# Deploy Demo Apps First
echo -e "\n${YELLOW}═══ Phase 1: Demo Applications ═══${NC}"

DEMO_APP_A_URL=$(deploy_service "demo-app-a" "demo-app-a" "dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com" 0 5 8080)
DEMO_APP_B_URL=$(deploy_service "demo-app-b" "demo-app-b" "dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com" 0 5 8080)

# Deploy Fixer Agent
echo -e "\n${YELLOW}═══ Phase 2: Fixer Agent ═══${NC}"

FIXER_URL=$(deploy_service "fixer-agent" "fixer-agent" "fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" 1 3 8081)

# Configure Pub/Sub to push to Fixer
echo "  Configuring Pub/Sub push subscription..."
gcloud pubsub subscriptions delete agent-actions-sub \
  --project=$PROJECT_ID \
  --quiet || true

gcloud pubsub subscriptions create agent-actions-sub \
  --topic=agent-actions \
  --push-endpoint="${FIXER_URL}/actions/execute" \
  --ack-deadline=60 \
  --project=$PROJECT_ID

echo -e "${GREEN}  ✓ Pub/Sub configured to push to Fixer${NC}"

# Deploy Supervisor API
echo -e "\n${YELLOW}═══ Phase 3: Supervisor API ═══${NC}"

cd ../../apps/supervisor-api

# Add target services to env vars
TARGET_SERVICES_JSON="[{\"name\":\"demo-app-a\",\"region\":\"$REGION\"},{\"name\":\"demo-app-b\",\"region\":\"$REGION\"}]"

echo "  Building container..."
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/supervisor-api \
  --project=$PROJECT_ID \
  --quiet

echo "  Deploying to Cloud Run..."
gcloud run deploy supervisor-api \
  --image gcr.io/$PROJECT_ID/supervisor-api \
  --platform managed \
  --region $REGION \
  --service-account supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --min-instances 1 \
  --max-instances 5 \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,TARGET_SERVICES_JSON=$TARGET_SERVICES_JSON,PUBSUB_TOPIC=agent-actions,ERROR_THRESHOLD=$ERROR_THRESHOLD_PCT,LATENCY_P95_THRESHOLD_MS=$LATENCY_P95_THRESHOLD_MS" \
  --project=$PROJECT_ID \
  --quiet

SUPERVISOR_URL=$(gcloud run services describe supervisor-api \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)' \
  --project=$PROJECT_ID)

echo -e "${GREEN}  ✓ Supervisor API deployed${NC}"
echo -e "${BLUE}  URL: $SUPERVISOR_URL${NC}"

cd - > /dev/null

# Create Cloud Scheduler job
echo -e "\n${GREEN}[Configuring Cloud Scheduler]${NC}"

# Delete if exists
gcloud scheduler jobs delete health-scan-job \
  --location=$REGION \
  --project=$PROJECT_ID \
  --quiet || true

# Create new job
gcloud scheduler jobs create http health-scan-job \
  --location=$REGION \
  --schedule="*/2 * * * *" \
  --uri="${SUPERVISOR_URL}/health/scan" \
  --http-method=POST \
  --oidc-service-account-email=supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --project=$PROJECT_ID

echo -e "${GREEN}  ✓ Cloud Scheduler configured (runs every 2 minutes)${NC}"

# Deploy Dashboard
echo -e "\n${YELLOW}═══ Phase 4: Dashboard ═══${NC}"

cd ../../apps/dashboard-web

# Create .env.local for build
cat > .env.local << EOF
NEXT_PUBLIC_SUPERVISOR_API_URL=$SUPERVISOR_URL
NEXT_PUBLIC_PROJECT_ID=$PROJECT_ID
NEXT_PUBLIC_REGION=$REGION
EOF

echo "  Building container..."
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/dashboard-web \
  --project=$PROJECT_ID \
  --quiet

echo "  Deploying to Cloud Run..."
gcloud run deploy dashboard-web \
  --image gcr.io/$PROJECT_ID/dashboard-web \
  --platform managed \
  --region $REGION \
  --service-account dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --min-instances 1 \
  --max-instances 3 \
  --port 3000 \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_SUPERVISOR_API_URL=$SUPERVISOR_URL,NEXT_PUBLIC_PROJECT_ID=$PROJECT_ID,NEXT_PUBLIC_REGION=$REGION" \
  --project=$PROJECT_ID \
  --quiet

DASHBOARD_URL=$(gcloud run services describe dashboard-web \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)' \
  --project=$PROJECT_ID)

echo -e "${GREEN}  ✓ Dashboard deployed${NC}"
echo -e "${BLUE}  URL: $DASHBOARD_URL${NC}"

cd - > /dev/null

# Save URLs to file
cat > ../../deployment-urls.txt << EOF
AgentOps Deployment URLs
========================

Dashboard: $DASHBOARD_URL
Supervisor API: $SUPERVISOR_URL
Fixer Agent: $FIXER_URL
Demo App A: $DEMO_APP_A_URL
Demo App B: $DEMO_APP_B_URL

Quick Test Commands:
====================

# Check supervisor health
curl $SUPERVISOR_URL/health

# Trigger manual scan
curl -X POST $SUPERVISOR_URL/health/scan

# View dashboard
open $DASHBOARD_URL

# Inject fault in Demo App A
curl -X POST $DEMO_APP_A_URL/fault/enable?type=5xx&duration=300

EOF

# Final summary
echo -e "\n${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Deployment Complete! ✓            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}All services deployed successfully!${NC}"
echo ""
echo -e "${YELLOW}Service URLs:${NC}"
echo -e "  Dashboard:      ${BLUE}$DASHBOARD_URL${NC}"
echo -e "  Supervisor API: ${BLUE}$SUPERVISOR_URL${NC}"
echo -e "  Fixer Agent:    ${BLUE}$FIXER_URL${NC}"
echo -e "  Demo App A:     ${BLUE}$DEMO_APP_A_URL${NC}"
echo -e "  Demo App B:     ${BLUE}$DEMO_APP_B_URL${NC}"
echo ""
echo -e "${YELLOW}URLs saved to: deployment-urls.txt${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open dashboard: ${BLUE}$DASHBOARD_URL${NC}"
echo "  2. Wait 2-3 minutes for first health scan"
echo "  3. Click 'Inject Fault' to test auto-remediation"
echo ""
echo -e "${GREEN}Happy Hacking! 🚀${NC}"