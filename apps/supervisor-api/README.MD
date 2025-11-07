# Supervisor API

AI-powered health monitoring and anomaly detection service for Google Cloud Run. The Supervisor continuously monitors your Cloud Run services using real-time metrics from Cloud Monitoring and Cloud Logging, detects anomalies, and can trigger automated remediation actions.

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

### ✅ Real Cloud Monitoring Integration
- Fetches actual `request_count` from Cloud Run services
- Queries `5xx error rates` from response code metrics
- Retrieves `latency percentiles` (p95, p99)
- Pulls error logs from Cloud Logging
- Concurrent metric fetching for performance

### ✅ Health Scanning
- Configurable time windows (default: 5 minutes)
- Anomaly detection based on thresholds
- Service status: `healthy`, `degraded`, `unhealthy`
- Minimum request count validation
- Error rate and latency threshold checks

### ✅ REST API
- `/health` - Service health check
- `/health/scan` - Trigger manual health scan
- `/services/status` - Get current status of all monitored services
- `/incidents` - List recent incidents (ready for Firestore)
- `/incidents/{id}` - Get specific incident details

### 🔄 In Progress / Optional
- Gemini AI analysis and recommendations
- Firestore incident storage
- Pub/Sub action publishing
- Auto-remediation suggestions

## 🚀 Quick Start

### Prerequisites
- GCP Project with billing enabled
- Cloud Run, Monitoring, and Logging APIs enabled
- Service account with appropriate permissions
- Python 3.11+

### Local Development

1. **Install dependencies**
```bash
cd apps/supervisor-api
pip install -r requirements.txt
```

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
# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/supervisor-api

# Deploy to Cloud Run
gcloud run deploy supervisor-api \
  --image gcr.io/$PROJECT_ID/supervisor-api \
  --platform managed \
  --region $REGION \
  --service-account supervisor-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --min-instances 1 \
  --max-instances 5 \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,TARGET_SERVICES=demo-app-a,demo-app-b"
```

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
    "logging_client": true,
    "gemini_reasoner": false,
    "pubsub_publisher": true,
    "firestore_client": false
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
      "recommendation": null
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
List recent incidents.

**Query Parameters:**
- `limit` (int): Maximum number of incidents (default: 50)
- `status` (string): Filter by status

**Response:**
```json
[]
```
*Note: Full implementation requires Firestore integration*

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

### 4. Anomaly Response
When anomaly detected:
1. Log anomaly details
2. (Optional) Call Gemini AI for analysis
3. (Optional) Publish action to Pub/Sub
4. (Optional) Store incident in Firestore

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

## 🔄 Roadmap

### Phase 1: Real Monitoring ✅ (Current)
- [x] Cloud Monitoring integration
- [x] Cloud Logging integration
- [x] Real-time metrics fetching
- [x] Anomaly detection
- [x] Health status assessment

### Phase 2: AI Analysis (In Progress)
- [ ] Gemini AI integration
- [ ] Root cause analysis
- [ ] Action recommendations
- [ ] Confidence scoring

### Phase 3: Incident Management
- [ ] Firestore incident storage
- [ ] Incident lifecycle tracking
- [ ] MTTR calculation
- [ ] Historical analysis

### Phase 4: Auto-Remediation
- [ ] Pub/Sub action publishing
- [ ] Integration with Fixer Agent
- [ ] Rollback recommendations
- [ ] Scaling suggestions

### Phase 5: Advanced Features
- [ ] Multi-region support
- [ ] Custom metric queries
- [ ] Alert channels (email, Slack)
- [ ] Canary deployment analysis
- [ ] Cost impact analysis

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