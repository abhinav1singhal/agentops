# Supervisor API

AI-powered health monitoring and anomaly detection service for Google Cloud Run. The Supervisor continuously monitors your Cloud Run services using real-time metrics from Cloud Monitoring and Cloud Logging, detects anomalies using Gemini AI, and triggers automated remediation actions.

> **✅ Production Ready:** Successfully deployed and running on Cloud Run with full Vertex AI Gemini integration, Firestore incident tracking, and Pub/Sub action publishing. All modules tested and operational!

## 🎯 Overview

The Supervisor API is the brain of the AgentOps system. It:
- **Monitors** Cloud Run services using real Cloud Monitoring metrics
- **Detects** anomalies based on error rates, latency, and request patterns
- **Analyzes** incidents using Gemini AI (when fully enabled)
- **Publishes** remediation actions to Pub/Sub for the Fixer Agent
- **Stores** incident data in Firestore for the Dashboard

## 🏗️ Architecture

```
Cloud Scheduler (every 2 min)
         ↓
   Supervisor API
         ↓
   [Real-time Metrics]
         ↓
   Cloud Monitoring ←→ Cloud Logging
         ↓
   Health Assessment
         ↓
   [If Anomaly Detected]
         ↓
   Gemini AI Analysis (optional)
         ↓
   Pub/Sub → Fixer Agent
         ↓
   Firestore (incident storage)
```

## 📊 Current Features

### ✅ Modular Architecture
- **`health_scanner`** - Cloud Monitoring and Logging integration
- **`gemini_reasoner`** - AI-powered analysis with Gemini 1.5 Flash
- **`pubsub_publisher`** - Action publishing to Pub/Sub
- **`firestore_client`** - Incident storage and lifecycle tracking
- **`models`** - Pydantic data models for type safety

### ✅ Real Cloud Monitoring Integration
- Fetches actual `request_count` from Cloud Run services
- Queries `5xx error rates` from response code metrics
- Retrieves `latency percentiles` (p95, p99)
- Pulls error logs from Cloud Logging
- Concurrent metric fetching for performance

### ✅ AI-Powered Decision Making
- Gemini 1.5 Flash analyzes service health metrics
- Generates intelligent remediation recommendations
- Provides confidence scores and risk assessments
- Context-aware decisions based on metrics, logs, and revision history
- Available actions: ROLLBACK, SCALE_UP, SCALE_DOWN, REDEPLOY, NONE

### ✅ Incident Management
- Creates incident records in Firestore
- Tracks incident lifecycle (detected → analyzing → action_pending → remediating → resolved/failed)
- Calculates MTTR (Mean Time To Recovery)
- Stores action results and explanations
- Full audit trail of all actions taken

### ✅ Action Publishing
- Publishes remediation actions to Pub/Sub
- Fixer agent subscribes and executes actions
- Includes incident ID, action type, confidence, and reasoning

### ✅ Health Scanning
- Configurable time windows (default: 5 minutes)
- Anomaly detection based on thresholds
- Service status: `healthy`, `degraded`, `unhealthy`
- Minimum request count validation
- Error rate and latency threshold checks

### ✅ REST API
- `/health` - Service health check with component status
- `/health/scan` - Trigger health scan with AI analysis
- `/services/status` - Get current status of all monitored services
- `/incidents` - List recent incidents from Firestore
- `/incidents/{id}` - Get specific incident details
- `/explain/{id}` - Generate human-readable incident explanation

## 🚀 Quick Start

### Prerequisites
- GCP Project with billing enabled
- **Required APIs enabled:**
  - Cloud Run API
  - Cloud Monitoring API
  - Cloud Logging API
  - **Vertex AI API** (for Gemini integration)
  - Pub/Sub API
  - Firestore API
- Service account with appropriate permissions
- Python 3.11+

### Local Development

1. **Install dependencies**
```bash
cd apps/supervisor-api

# Upgrade pip first (recommended to avoid build issues)
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

> **Important:** The application requires `google-cloud-aiplatform>=1.60.0` for Vertex AI Gemini integration. Earlier versions (e.g., 1.38.1) use a preview API with different import paths and will cause `ImportError` at runtime.

2. **Set environment variables**
```bash
export PROJECT_ID="your-gcp-project"
export REGION="us-central1"
export TARGET_SERVICES="demo-app-a,demo-app-b"
export ERROR_THRESHOLD="5.0"
export LATENCY_P95_THRESHOLD_MS="600"
export SCAN_WINDOW_MINUTES="5"
export MIN_REQUEST_COUNT="100"
```

3. **Run locally**
```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

4. **Test endpoints**
```bash
# Health check
curl http://localhost:8080/health

# Trigger scan
curl -X POST http://localhost:8080/health/scan

# Get service status
curl http://localhost:8080/services/status
```

### Deploy to Cloud Run

Using the deployment script:
```powershell
# Windows
cd infra/scripts
.\deploy-all.ps1
```

```bash
# Linux/Mac
cd infra/scripts
./deploy-all.sh
```

Or manually:
```bash
# Set variables
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/supervisor-api

# Deploy to Cloud Run with all environment variables
gcloud run deploy supervisor-api \
  --image gcr.io/$PROJECT_ID/supervisor-api \
  --platform managed \
  --region $REGION \
  --service-account supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --min-instances 1 \
  --max-instances 5 \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,\
REGION=$REGION,\
TARGET_SERVICES=demo-app-a,demo-app-b,\
ERROR_THRESHOLD=5.0,\
LATENCY_P95_THRESHOLD_MS=600,\
SCAN_WINDOW_MINUTES=5,\
MIN_REQUEST_COUNT=100,\
PUBSUB_TOPIC=agent-actions,\
GEMINI_MODEL=gemini-1.5-flash,\
INCIDENTS_COLLECTION=incidents,\
ACTIONS_COLLECTION=actions"
```

> **Note:** Ensure the Vertex AI API is enabled in your GCP project before deploying, otherwise Gemini integration will fail.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PROJECT_ID` | GCP Project ID | - | ✅ Yes |
| `REGION` | GCP Region | `us-central1` | ✅ Yes |
| `TARGET_SERVICES` | Comma-separated service names | - | ✅ Yes |
| `TARGET_SERVICES_JSON` | JSON array of services (alternative) | - | No |
| `ERROR_THRESHOLD` | Error rate threshold (%) | `5.0` | No |
| `LATENCY_P95_THRESHOLD_MS` | P95 latency threshold (ms) | `600` | No |
| `LATENCY_P99_THRESHOLD_MS` | P99 latency threshold (ms) | `1000` | No |
| `MIN_REQUEST_COUNT` | Minimum requests for analysis | `100` | No |
| `SCAN_WINDOW_MINUTES` | Metrics time window | `5` | No |
| `PUBSUB_TOPIC` | Pub/Sub topic for actions | `agent-actions` | No |
| `GEMINI_MODEL` | Gemini model name | `gemini-1.5-flash` | No |
| `INCIDENTS_COLLECTION` | Firestore collection for incidents | `incidents` | No |
| `ACTIONS_COLLECTION` | Firestore collection for actions | `actions` | No |

### Target Services Configuration

**Option 1: Comma-separated list**
```bash
TARGET_SERVICES="demo-app-a,demo-app-b,production-api"
```

**Option 2: JSON array** (for multi-region)
```bash
TARGET_SERVICES_JSON='[
  {"name":"demo-app-a","region":"us-central1"},
  {"name":"demo-app-b","region":"us-central1"},
  {"name":"production-api","region":"us-east1"}
]'
```

### Health Check Thresholds

Customize anomaly detection:
```bash
ERROR_THRESHOLD="5.0"              # Trigger at 5% error rate
LATENCY_P95_THRESHOLD_MS="600"     # Trigger at 600ms p95 latency
LATENCY_P99_THRESHOLD_MS="1000"    # Trigger at 1000ms p99 latency
MIN_REQUEST_COUNT="100"            # Need 100+ requests for analysis
```

## 📡 API Reference

### GET /health
Health check endpoint for Cloud Run.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "project_id": "my-project",
  "region": "us-central1",
  "components": {
    "health_scanner": true,
    "gemini_reasoner": true,
    "pubsub_publisher": true,
    "firestore_client": true
  }
}
```

### POST /health/scan
Trigger a manual health scan of all monitored services.

**Response:**
```json
{
  "scan_id": "scan_1705318200",
  "timestamp": "2024-01-15T10:30:00Z",
  "services_scanned": 2,
  "anomalies_detected": 1,
  "actions_recommended": 1,
  "details": [
    {
      "service": "demo-app-a",
      "region": "us-central1",
      "status": "unhealthy",
      "has_anomaly": true,
      "error_rate": 15.5,
      "latency_p95": 450.2,
      "request_count": 1250,
      "error_count": 194,
      "success_count": 1056,
      "anomaly_summary": "High error rate: 15.50% (threshold: 5.0%)",
      "error_logs": [
        {
          "timestamp": "2024-01-15T10:29:45Z",
          "severity": "ERROR",
          "message": "Connection timeout to database"
        }
      ],
      "recommendation": "ROLLBACK"
    }
  ]
}
```

### GET /services/status
Get current health status of all monitored services.

**Response:**
```json
[
  {
    "name": "demo-app-a",
    "region": "us-central1",
    "status": "healthy",
    "error_rate": 0.5,
    "latency_p95": 150.0,
    "request_count": 1000,
    "last_checked": "2024-01-15T10:30:00Z",
    "real_data": true
  }
]
```

### GET /incidents
List recent incidents from Firestore.

**Query Parameters:**
- `limit` (int): Maximum number of incidents (default: 50)
- `status` (string): Filter by status (detected, analyzing, action_pending, remediating, resolved, failed)

**Response:**
```json
[
  {
    "id": "inc_demo-app-a_1705318200",
    "service_name": "demo-app-a",
    "region": "us-central1",
    "status": "resolved",
    "detected_at": "2024-01-15T10:30:00Z",
    "resolved_at": "2024-01-15T10:35:00Z",
    "mttr_seconds": 300,
    "error_rate": 15.5,
    "latency_p95": 450.2,
    "recommended_action": "ROLLBACK",
    "action_taken": "ROLLBACK",
    "confidence": 0.85
  }
]
```

### GET /incidents/{incident_id}
Get specific incident details.

**Response:**
```json
{
  "id": "inc_demo-app-a_1705318200",
  "service_name": "demo-app-a",
  "region": "us-central1",
  "status": "resolved",
  "detected_at": "2024-01-15T10:30:00Z",
  "resolved_at": "2024-01-15T10:35:00Z",
  "health_snapshot": {
    "error_rate": 15.5,
    "latency_p95": 450.2,
    "request_count": 1250
  },
  "recommendation": {
    "action": "ROLLBACK",
    "confidence": 0.85,
    "reasoning": "High error rate detected after recent deployment...",
    "target_revision": "demo-app-a-00005-abc"
  },
  "action_result": {
    "success": true,
    "message": "Successfully rolled back to revision demo-app-a-00005-abc"
  }
}
```

### POST /explain/{incident_id}
Generate human-readable explanation for an incident using Gemini AI.

**Response:**
```json
{
  "incident_id": "inc_demo-app-a_1705318200",
  "explanation": "At 10:30 AM, the demo-app-a service experienced a critical incident...",
  "timestamp": "2024-01-15T10:40:00Z"
}
```

## 🏛️ Modular Architecture

The Supervisor API is built with a clean, modular architecture for maximum maintainability and testability:

### Core Modules

#### 1. **models.py** - Data Models
Pydantic models for type safety and validation:
- `ServiceHealth` - Complete health assessment
- `HealthMetrics` - Error rate, latency, request counts
- `AIRecommendation` - Gemini's suggested action with confidence
- `ActionRequest` - Message sent to Pub/Sub for Fixer agent
- `Incident` - Full incident record with lifecycle tracking
- `ActionResult` - Result of remediation action execution

#### 2. **health_scanner.py** - Metrics & Logs
Cloud Monitoring and Logging integration:
- Queries Cloud Run metrics (request_count, latencies, errors)
- Fetches error logs with severity filtering
- Calculates error rates and percentiles
- Assesses health status based on thresholds
- Concurrent metric/log fetching for performance

#### 3. **gemini_reasoner.py** - AI Analysis
Gemini 1.5 Flash integration:
- Analyzes service health metrics and logs
- Queries Cloud Run revision information
- Generates remediation recommendations
- Calculates confidence scores
- Provides risk assessments and explanations

#### 4. **pubsub_publisher.py** - Action Publishing
Pub/Sub integration:
- Publishes `ActionRequest` messages to Pub/Sub topic
- Includes metadata (incident_id, service_name, action_type)
- Async publishing with error handling
- Configurable topic name

#### 5. **firestore_client.py** - Incident Storage
Firestore integration:
- Creates incident records with full context
- Updates incidents as they progress through lifecycle
- Queries incidents with filtering and pagination
- Records action execution results
- Calculates MTTR automatically

### Lifecycle Manager

The app uses FastAPI's `lifespan` context manager for clean startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Initialize all components
    health_scanner = HealthScanner(project_id, region)
    gemini_reasoner = GeminiReasoner(project_id, region)
    pubsub_publisher = PubSubPublisher(project_id)
    firestore_client = FirestoreClient(project_id)

    yield

    # Shutdown - Clean up resources
```

### Benefits

- **Separation of Concerns**: Each module handles one responsibility
- **Testability**: Modules can be tested independently
- **Maintainability**: Changes to monitoring logic don't affect AI logic
- **Type Safety**: Pydantic models validate data structures
- **Async Architecture**: Efficient concurrent operations

## ✅ Deployment Verification

After deploying, verify the service is working correctly:

**1. Check deployment status:**
```bash
gcloud run services describe supervisor-api --region=$REGION
```

**2. Test health endpoint:**
```bash
# Get the service URL
export SUPERVISOR_URL=$(gcloud run services describe supervisor-api --region=$REGION --format='value(status.url)')

# Check health
curl $SUPERVISOR_URL/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "health_scanner": true,
    "gemini_reasoner": true,
    "pubsub_publisher": true,
    "firestore_client": true
  }
}
```

**3. Test health scan:**
```bash
curl -X POST $SUPERVISOR_URL/health/scan
```

**4. Check logs for errors:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=supervisor-api AND severity>=WARNING" --limit=20
```

**5. Verify all components initialized:**
```bash
# Look for startup messages in logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=supervisor-api AND textPayload:\"Supervisor API started\"" --limit=5
```

## 🔍 How It Works

### 1. Scheduled Scanning
Cloud Scheduler triggers `/health/scan` every 2 minutes:
```bash
gcloud scheduler jobs create http health-scan-job \
  --location=$REGION \
  --schedule="*/2 * * * *" \
  --uri="$SUPERVISOR_URL/health/scan" \
  --http-method=POST
```

### 2. Metric Collection
For each service, the Supervisor fetches:

**Request Count:**
```python
metric_type = "run.googleapis.com/request_count"
aligner = "ALIGN_SUM"
# Total requests in last 5 minutes
```

**Error Count:**
```python
metric_type = "run.googleapis.com/request_count"
filter = 'metric.label.response_code_class="5xx"'
# 5xx errors in last 5 minutes
```

**Latency (P95):**
```python
metric_type = "run.googleapis.com/request_latencies"
aligner = "ALIGN_DELTA"
reducer = "REDUCE_PERCENTILE_95"
# 95th percentile latency
```

**Error Logs:**
```python
filter = 'severity>=ERROR AND timestamp>=(now-5m)'
# Recent error log entries
```

### 3. Health Assessment
```python
# Calculate error rate
error_rate = (error_count / request_count) * 100

# Check thresholds
if request_count >= MIN_REQUEST_COUNT:
    if error_rate > ERROR_THRESHOLD:
        status = "unhealthy"
        has_anomaly = True
    elif latency_p95 > LATENCY_P95_THRESHOLD:
        status = "degraded"
        has_anomaly = True
    else:
        status = "healthy"
```

### 4. AI-Powered Analysis
When anomaly detected, Gemini AI analyzes the situation:
```python
# Get AI recommendation
recommendation = await gemini_reasoner.analyze_and_recommend(health_status)

# Recommendation includes:
# - action: ROLLBACK, SCALE_UP, SCALE_DOWN, REDEPLOY, or NONE
# - confidence: 0.0 to 1.0
# - reasoning: Detailed explanation
# - target_revision: For rollback actions
# - risk_assessment: Potential impact
```

### 5. Incident Recording
Create incident record in Firestore:
```python
incident = await firestore_client.create_incident(
    service_name=service_name,
    health_status=health_status,
    recommendation=recommendation
)
```

Incident lifecycle states:
- **detected** - Anomaly identified
- **analyzing** - Gemini is analyzing
- **action_pending** - Recommendation made
- **remediating** - Fixer agent executing
- **resolved** - Issue fixed
- **failed** - Action failed

### 6. Action Publishing
Publish to Pub/Sub for Fixer Agent:
```python
action_request = ActionRequest(
    incident_id=incident.id,
    service_name=service_name,
    action_type=recommendation.action,
    target_revision=recommendation.target_revision,
    reason=recommendation.reasoning,
    confidence=recommendation.confidence
)

await pubsub_publisher.publish_action(action_request)
```

## 🧪 Testing

### Manual Testing

1. **Check service health**
```bash
curl https://supervisor-api-xxx.run.app/health
```

2. **Trigger a scan**
```bash
curl -X POST https://supervisor-api-xxx.run.app/health/scan
```

3. **Inject a fault in demo app**
```bash
# Inject 15% error rate for 5 minutes
curl -X POST https://demo-app-a-xxx.run.app/fault/enable?type=5xx&error_rate=15&duration=300
```

4. **Wait 2-3 minutes for next scheduled scan**

5. **Check results**
```bash
curl https://supervisor-api-xxx.run.app/services/status
```

### Expected Behavior

**Healthy Service:**
```json
{
  "name": "demo-app-a",
  "status": "healthy",
  "error_rate": 0.5,
  "latency_p95": 150.0,
  "request_count": 1000
}
```

**Unhealthy Service (after fault injection):**
```json
{
  "name": "demo-app-a",
  "status": "unhealthy",
  "error_rate": 15.5,
  "latency_p95": 450.0,
  "request_count": 1250,
  "has_anomaly": true,
  "anomaly_summary": "High error rate: 15.50% (threshold: 5.0%)"
}
```

## 🔐 IAM Permissions

The `supervisor-sa` service account needs:

```bash
# Read metrics and logs
roles/monitoring.viewer
roles/logging.viewer

# Publish to Pub/Sub
roles/pubsub.publisher

# Use Gemini AI
roles/aiplatform.user

# Store incidents in Firestore
roles/datastore.user

# View Cloud Run services
roles/run.viewer
```

Grant permissions:
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"
```

## 📊 Metrics and Monitoring

The Supervisor itself can be monitored:

**Key Metrics:**
- Scan duration
- Services scanned per run
- Anomalies detected
- API response times
- Error rates in metric fetching

**Logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=supervisor-api" --limit 50
```

**Health Status:**
```bash
# Check if supervisor is healthy
curl https://supervisor-api-xxx.run.app/health
```

## 🐛 Troubleshooting

### Issue: ImportError - cannot import GenerativeModel from vertexai.generative_models
**Cause:** Incompatible `google-cloud-aiplatform` version. Versions below 1.60.0 use a preview API with different import paths.

**Error Message:**
```
ImportError: cannot import name 'GenerativeModel' from 'vertexai.generative_models' (unknown location)
```

**Fix:**
```bash
# Update requirements.txt to use version >= 1.60.0
google-cloud-aiplatform>=1.60.0

# Rebuild and redeploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/supervisor-api
gcloud run deploy supervisor-api --image gcr.io/$PROJECT_ID/supervisor-api --region=$REGION
```

**Why this happens:**
- `google-cloud-aiplatform<1.60.0` uses `vertexai.preview.generative_models` (preview API)
- `google-cloud-aiplatform>=1.60.0` uses `vertexai.generative_models` (stable API)
- The `gemini_reasoner.py` module uses the stable API imports

### Issue: "Monitoring client not initialized"
**Cause:** PROJECT_ID environment variable not set or invalid credentials

**Fix:**
```bash
# Check environment
gcloud run services describe supervisor-api --region=$REGION --format='value(spec.template.spec.containers[0].env)'

# Update if needed
gcloud run services update supervisor-api \
  --region=$REGION \
  --set-env-vars="PROJECT_ID=$PROJECT_ID"
```

### Issue: No metrics returned (all zeros)
**Cause:** Service name or region mismatch, or insufficient data

**Fix:**
1. Verify service names match exactly:
```bash
gcloud run services list --region=$REGION
```

2. Check if services have traffic:
```bash
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --project=$PROJECT_ID
```

3. Generate some traffic:
```bash
# Send requests to demo app
for i in {1..100}; do curl https://demo-app-a-xxx.run.app/; done
```

### Issue: "Insufficient data" in scan results
**Cause:** Not enough requests in the time window

**Fix:**
```bash
# Lower the minimum request count threshold
gcloud run services update supervisor-api \
  --region=$REGION \
  --set-env-vars="MIN_REQUEST_COUNT=10"

# Or increase scan window
gcloud run services update supervisor-api \
  --region=$REGION \
  --set-env-vars="SCAN_WINDOW_MINUTES=10"
```

### Issue: Scan takes too long
**Cause:** Multiple services being scanned sequentially

**Fix:**
The current implementation uses concurrent fetching (`asyncio.gather`), but you can optimize:
```bash
# Reduce scan window
SCAN_WINDOW_MINUTES=3

# Reduce number of monitored services
TARGET_SERVICES="demo-app-a"
```

### Issue: Container fails to start - "The user-provided container failed to start and listen on the port"
**Cause:** Application crash during startup, often due to missing dependencies or import errors

**Fix:**
1. Check container logs for the actual error:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=supervisor-api" --limit=50 --format=json
```

2. Common issues:
   - **Import errors**: Check all module imports are correct
   - **Missing environment variables**: Ensure PROJECT_ID and REGION are set
   - **Dependency conflicts**: Verify requirements.txt versions are compatible

3. Test locally first:
```bash
# Build and run container locally
docker build -t supervisor-api .
docker run -p 8080:8080 \
  -e PROJECT_ID=your-project \
  -e REGION=us-central1 \
  -e TARGET_SERVICES=demo-app-a \
  supervisor-api
```

## 🔄 Roadmap

### Phase 1: Real Monitoring ✅ (Complete)
- [x] Cloud Monitoring integration
- [x] Cloud Logging integration
- [x] Real-time metrics fetching
- [x] Anomaly detection
- [x] Health status assessment
- [x] Modular architecture with separate components

### Phase 2: AI Analysis ✅ (Complete)
- [x] Gemini AI integration
- [x] Root cause analysis
- [x] Action recommendations (ROLLBACK, SCALE_UP, SCALE_DOWN, REDEPLOY)
- [x] Confidence scoring
- [x] Human-readable incident explanations

### Phase 3: Incident Management ✅ (Complete)
- [x] Firestore incident storage
- [x] Incident lifecycle tracking
- [x] MTTR calculation
- [x] Historical analysis
- [x] Action audit trail

### Phase 4: Auto-Remediation ✅ (Complete)
- [x] Pub/Sub action publishing
- [x] Integration with Fixer Agent
- [x] Rollback recommendations
- [x] Scaling suggestions

### Phase 5: Advanced Features (Planned)
- [ ] Multi-region support
- [ ] Custom metric queries
- [ ] Alert channels (email, Slack)
- [ ] Canary deployment analysis
- [ ] Cost impact analysis
- [ ] ML-based anomaly detection
- [ ] Predictive scaling
- [ ] Custom remediation workflows

## 📚 Related Documentation

- [AgentOps Main README](../../README.md)
- [Fixer Agent README](../fixer-agent/README.md)
- [Dashboard README](../dashboard-web/README.md)
- [Deployment Guide](../../DEPLOYMENT_GUIDE.md)

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional metric types
- Custom aggregation methods
- Better error handling
- Performance optimizations
- Test coverage

## 📄 License

MIT License - See [LICENSE](../../LICENSE)

## 🆘 Support

- **Issues**: Open an issue on GitHub
- **Questions**: Check existing issues or create new one
- **Documentation**: See main README and deployment guide

---

**Built with ❤️ for Google Cloud AI Hackathon 2024**

*Part of the AgentOps AI-powered Cloud Run auto-remediation system*