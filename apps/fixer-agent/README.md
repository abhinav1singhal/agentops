# Fixer Agent

AI-powered remediation executor for Google Cloud Run services. The Fixer Agent receives action requests from the Supervisor API and executes automated remediation actions including traffic rollback, scaling adjustments, and redeployments.

> **🔧 Enhancement Plan:** This README documents the target architecture for the Fixer Agent with modular design, real Cloud Run actions, and Firestore integration. Implementation follows the proven pattern from Supervisor API.

## 🎯 Overview

The Fixer Agent is the execution engine of the AgentOps system. It:
- **Receives** action requests from Supervisor API via Pub/Sub
- **Executes** remediation actions on Cloud Run services
- **Updates** incident status in Firestore
- **Records** action results and execution details

## 🏗️ Architecture

```
Supervisor API (detects anomaly)
         ↓
   Pub/Sub Topic (agent-actions)
         ↓
   Fixer Agent (Cloud Run)
         ↓
   Cloud Run Admin API → Target Services
         ↓
   Firestore (incident updates)
```

## 📊 Current Features

### ✅ Modular Architecture
- **`cloud_run_manager`** - Cloud Run Admin API integration
- **`firestore_updater`** - Incident status updates (planned)
- **`subscribers`** - Pub/Sub message processing
- **`models`** - Pydantic data models for type safety

### ✅ Real Cloud Run Actions
- **Traffic Rollback** - Route 100% traffic to previous stable revision
- **Scale Up** - Increase min/max instances to handle load
- **Scale Down** - Decrease instance count to save costs
- **Redeploy** - Trigger new deployment (planned)

### ✅ Safety Features
- **Dry-run mode** - Test actions without making changes
- **Instance count limits** - Configurable min/max bounds
- **Revision validation** - Verify target revision exists before rollback
- **Operation timeouts** - 5-minute timeout for Cloud Run operations

### ✅ Firestore Integration (Planned)
- Update incident status (action_pending → remediating → resolved/failed)
- Record action execution details
- Calculate MTTR (Mean Time To Recovery)
- Store action audit trail

### ✅ REST API
- `/` - Service information
- `/health` - Health check endpoint
- `/actions/execute` - Pub/Sub push endpoint (receives action requests)
- `/actions/execute/manual` - Manual action execution (for testing)

## 🚀 Quick Start

### Prerequisites
- GCP Project with billing enabled
- **Required APIs enabled:**
  - Cloud Run Admin API
  - Pub/Sub API
  - Firestore API
- Service account with appropriate permissions
- Python 3.11+

### Local Development

1. **Install dependencies**
```bash
cd apps/fixer-agent

# Upgrade pip first (recommended)
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

2. **Set environment variables**
```bash
export PROJECT_ID="your-gcp-project"
export REGION="us-central1"
export DRY_RUN_MODE="false"  # Set to "true" for testing
export PUBSUB_SUBSCRIPTION="agent-actions-sub"
export INCIDENTS_COLLECTION="incidents"
export ACTIONS_COLLECTION="actions"

# Safety limits (optional)
export MIN_INSTANCES_FLOOR="0"
export MIN_INSTANCES_CEILING="5"
export MAX_INSTANCES_FLOOR="10"
export MAX_INSTANCES_CEILING="100"
```

3. **Run locally**
```bash
uvicorn main:app --host 0.0.0.0 --port 8081
```

4. **Test endpoints**
```bash
# Health check
curl http://localhost:8081/health

# Test action (dry-run mode)
curl -X POST http://localhost:8081/actions/execute/manual \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "ROLLBACK",
    "service_name": "demo-app-a",
    "region": "us-central1",
    "target_revision": "demo-app-a-00005-abc",
    "incident_id": "test_123"
  }'
```

### Deploy to Cloud Run

Using the deployment script:
```bash
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
gcloud builds submit --tag gcr.io/$PROJECT_ID/fixer-agent

# Deploy to Cloud Run
gcloud run deploy fixer-agent \
  --image gcr.io/$PROJECT_ID/fixer-agent \
  --platform managed \
  --region $REGION \
  --service-account fixer-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --min-instances 0 \
  --max-instances 5 \
  --port 8081 \
  --no-allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,\
REGION=$REGION,\
DRY_RUN_MODE=false,\
PUBSUB_SUBSCRIPTION=agent-actions-sub,\
INCIDENTS_COLLECTION=incidents,\
ACTIONS_COLLECTION=actions,\
MIN_INSTANCES_FLOOR=0,\
MIN_INSTANCES_CEILING=5,\
MAX_INSTANCES_FLOOR=10,\
MAX_INSTANCES_CEILING=100"
```

> **Note:** The Fixer Agent should **not** be publicly accessible (`--no-allow-unauthenticated`). Only Pub/Sub push subscription should trigger it.

### Setup Pub/Sub Push Subscription

After deploying the Fixer Agent, create a Pub/Sub push subscription:

```bash
# Get fixer agent URL
export FIXER_URL=$(gcloud run services describe fixer-agent --region=$REGION --format='value(status.url)')

# Create push subscription pointing to fixer agent
gcloud pubsub subscriptions create agent-actions-sub \
  --topic=agent-actions \
  --push-endpoint="$FIXER_URL/actions/execute" \
  --push-auth-service-account=fixer-sa@$PROJECT_ID.iam.gserviceaccount.com
```

This allows Pub/Sub to automatically push messages to the Fixer Agent when the Supervisor publishes action requests.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PROJECT_ID` | GCP Project ID | - | ✅ Yes |
| `REGION` | GCP Region | `us-central1` | ✅ Yes |
| `DRY_RUN_MODE` | Test mode (no actual changes) | `false` | No |
| `MIN_INSTANCES_FLOOR` | Minimum allowed min_instances | `0` | No |
| `MIN_INSTANCES_CEILING` | Maximum allowed min_instances | `5` | No |
| `MAX_INSTANCES_FLOOR` | Minimum allowed max_instances | `10` | No |
| `MAX_INSTANCES_CEILING` | Maximum allowed max_instances | `100` | No |
| `PUBSUB_SUBSCRIPTION` | Pub/Sub subscription name | `agent-actions-sub` | No |
| `INCIDENTS_COLLECTION` | Firestore incidents collection | `incidents` | No |
| `ACTIONS_COLLECTION` | Firestore actions collection | `actions` | No |

### Safety Limits

The Fixer Agent enforces safety limits to prevent misconfiguration:

**Instance Count Bounds:**
- Requested min_instances is clamped to [MIN_INSTANCES_FLOOR, MIN_INSTANCES_CEILING]
- Requested max_instances is clamped to [MAX_INSTANCES_FLOOR, MAX_INSTANCES_CEILING]
- Ensures min_instances <= max_instances

**Example:**
```bash
# Request: min_instances=100 (too high)
# Enforced: min_instances=5 (MIN_INSTANCES_CEILING)

# Request: max_instances=5 (too low)
# Enforced: max_instances=10 (MAX_INSTANCES_FLOOR)
```

## 📡 API Reference

### GET /
Service information endpoint.

**Response:**
```json
{
  "service": "AgentOps Fixer Agent",
  "status": "healthy",
  "version": "1.1.0 Enhanced",
  "features": {
    "cloud_run_actions": true,
    "dry_run_mode": false
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /health
Health check endpoint for Cloud Run.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "cloud_run_client": true
}
```

### POST /actions/execute
Receives action requests from Pub/Sub (push subscription).

**Pub/Sub Message Format:**
```json
{
  "message": {
    "data": "base64-encoded-json",
    "messageId": "12345",
    "publishTime": "2024-01-15T10:30:00Z"
  }
}
```

**Decoded message data:**
```json
{
  "incident_id": "inc_demo-app-a_1705318200",
  "service_name": "demo-app-a",
  "region": "us-central1",
  "action_type": "ROLLBACK",
  "target_revision": "demo-app-a-00005-abc",
  "reason": "High error rate detected after deployment",
  "confidence": 0.85
}
```

**Response:**
```json
{
  "status": "processed",
  "action_type": "ROLLBACK",
  "service_name": "demo-app-a",
  "incident_id": "inc_demo-app-a_1705318200",
  "result": {
    "success": true,
    "service": "demo-app-a",
    "target_revision": "demo-app-a-00005-abc",
    "old_traffic": {"demo-app-a-00006-xyz": 100},
    "new_traffic": {"demo-app-a-00005-abc": 100},
    "operation_id": "operations/cp.1234567890"
  },
  "timestamp": "2024-01-15T10:31:00Z"
}
```

### POST /actions/execute/manual
Manually execute an action (for testing).

**Request:**
```json
{
  "action_type": "ROLLBACK",
  "service_name": "demo-app-a",
  "region": "us-central1",
  "target_revision": "demo-app-a-00005-abc",
  "incident_id": "test_incident_123"
}
```

**Response:**
```json
{
  "status": "success",
  "action_type": "ROLLBACK",
  "service_name": "demo-app-a",
  "result": {
    "success": true,
    "old_traffic": {"demo-app-a-00006-xyz": 100},
    "new_traffic": {"demo-app-a-00005-abc": 100}
  },
  "timestamp": "2024-01-15T10:31:00Z"
}
```

## 🏛️ Modular Architecture

The Fixer Agent is built with a clean, modular architecture for maximum maintainability and testability:

### Core Modules

#### 1. **cloud_run_manager.py** - Cloud Run Operations
Manages all Cloud Run Admin API interactions:

**Key Functions:**
- `rollback_traffic()` - Route traffic to specific revision
  - Validates target revision exists
  - Records old traffic split
  - Updates service with new traffic configuration
  - Waits for operation completion (5-minute timeout)
  - Returns detailed rollback result

- `update_scaling()` - Adjust instance counts
  - Gets current scaling settings
  - Applies safety limits
  - Validates min <= max
  - Updates service scaling configuration
  - Returns scaling update details

- `get_service_info()` - Inspect service state
  - Current revision
  - Traffic split
  - Scaling configuration
  - Available revisions

- `list_revisions()` - Query available revisions
  - Lists up to N recent revisions
  - Returns revision names for rollback targets

**Safety Features:**
- Dry-run mode (test without making changes)
- Instance count safety bounds
- Revision existence validation
- Operation timeout handling

#### 2. **firestore_updater.py** - Incident Updates (Planned)
Firestore integration for incident tracking:

**Planned Functions:**
- `update_incident_status()` - Update incident lifecycle
  - action_pending → remediating
  - remediating → resolved (on success)
  - remediating → failed (on error)

- `record_action_result()` - Store action details
  - Action type executed
  - Execution timestamp
  - Result details (traffic changes, scaling, etc.)
  - Operation IDs

- `calculate_mttr()` - Compute Mean Time To Recovery
  - Time from detection to resolution
  - Historical MTTR tracking

#### 3. **subscribers.py** - Pub/Sub Processing (Optional)
Alternative Pub/Sub pull subscription (if not using push):

**Features:**
- Pull messages from subscription
- Batch processing
- Retry logic for failed actions
- Manual acknowledgment

#### 4. **models.py** - Data Models
Pydantic models for type safety and validation:

**Enums:**
- `ActionType` - ROLLBACK, SCALE_UP, SCALE_DOWN, REDEPLOY, NONE
- `ActionStatus` - PENDING, IN_PROGRESS, SUCCESS, FAILED, PARTIAL

**Models:**
- `ActionRequest` - Incoming action from Supervisor
- `ActionResult` - Execution result details
- `TrafficTarget` - Revision and traffic percentage
- `ServiceInfo` - Complete service state

### Lifecycle Manager (Planned Enhancement)

Target architecture using FastAPI's `lifespan` context manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global cloud_run_manager, firestore_updater

    # Startup - Initialize all components
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")

    cloud_run_manager = CloudRunManager(project_id, region)
    firestore_updater = FirestoreUpdater(project_id)

    logger.info("Fixer Agent started")

    yield

    # Shutdown - Clean up resources
    logger.info("Shutting down Fixer Agent")

app = FastAPI(
    title="AgentOps Fixer Agent",
    version="1.1.0",
    lifespan=lifespan
)
```

### Benefits

- **Separation of Concerns**: Each module handles one responsibility
- **Testability**: Modules can be tested independently
- **Maintainability**: Cloud Run logic separate from API layer
- **Type Safety**: Pydantic models validate data structures
- **Async Architecture**: Efficient concurrent operations

## 🔍 How It Works

### 1. Action Request Flow

```
Supervisor API detects anomaly (error rate spike)
    ↓
Creates incident in Firestore (status: "action_pending")
    ↓
Gemini AI analyzes and recommends ROLLBACK
    ↓
Publishes ActionRequest to Pub/Sub topic "agent-actions"
    ↓
Pub/Sub pushes message to Fixer Agent endpoint
    ↓
Fixer Agent receives POST /actions/execute
    ↓
Updates incident (status: "remediating")
    ↓
Executes Cloud Run rollback via cloud_run_manager
    ↓
Updates incident (status: "resolved" or "failed")
    ↓
Records action result in Firestore "actions" collection
```

### 2. Traffic Rollback Example

**Scenario:** demo-app-a deployed bad revision (demo-app-a-00006-xyz) causing 15% errors

**Action Request:**
```json
{
  "incident_id": "inc_demo-app-a_1705318200",
  "service_name": "demo-app-a",
  "region": "us-central1",
  "action_type": "ROLLBACK",
  "target_revision": "demo-app-a-00005-abc",
  "reason": "High error rate: 15.50% (threshold: 5.0%)",
  "confidence": 0.85
}
```

**Execution Steps:**
1. Get current service state:
   ```python
   service = cloud_run_client.get_service(
       name="projects/my-project/locations/us-central1/services/demo-app-a"
   )
   ```

2. Verify target revision exists:
   ```python
   available_revisions = await list_revisions("demo-app-a", "us-central1")
   # ["demo-app-a-00006-xyz", "demo-app-a-00005-abc", "demo-app-a-00004-def"]

   if "demo-app-a-00005-abc" not in available_revisions:
       raise ValueError("Target revision not found")
   ```

3. Record old traffic:
   ```python
   old_traffic = {"demo-app-a-00006-xyz": 100}
   ```

4. Update traffic to target revision:
   ```python
   new_traffic = [
       TrafficTarget(
           type=TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION,
           revision="demo-app-a-00005-abc",
           percent=100
       )
   ]

   service.traffic = new_traffic
   operation = cloud_run_client.update_service(service)
   updated_service = operation.result(timeout=300)
   ```

5. Verify new traffic:
   ```python
   new_traffic = {"demo-app-a-00005-abc": 100}
   ```

**Result:**
```json
{
  "success": true,
  "service": "demo-app-a",
  "target_revision": "demo-app-a-00005-abc",
  "old_traffic": {"demo-app-a-00006-xyz": 100},
  "new_traffic": {"demo-app-a-00005-abc": 100},
  "operation_id": "operations/cp.1234567890"
}
```

### 3. Scale Up Example

**Scenario:** demo-app-b experiencing high latency due to insufficient capacity

**Action Request:**
```json
{
  "action_type": "SCALE_UP",
  "service_name": "demo-app-b",
  "region": "us-central1",
  "scale_params": {
    "min_instances": 3,
    "max_instances": 20
  }
}
```

**Execution:**
```python
result = await cloud_run_manager.update_scaling(
    service_name="demo-app-b",
    region="us-central1",
    min_instances=3,
    max_instances=20
)
```

**Result:**
```json
{
  "success": true,
  "service": "demo-app-b",
  "old_min": 0,
  "old_max": 10,
  "new_min": 3,
  "new_max": 20,
  "operation_id": "operations/cp.9876543210"
}
```

### 4. Safety Features in Action

**Dry-Run Mode:**
```bash
export DRY_RUN_MODE="true"
```

When enabled:
- Logs all actions without executing
- Returns what *would* happen
- Perfect for testing and validation

**Instance Count Limits:**
```bash
export MIN_INSTANCES_CEILING="5"
export MAX_INSTANCES_CEILING="100"
```

If request exceeds limits:
```python
# Request: min_instances=10 (exceeds ceiling of 5)
# Enforced: min_instances=5
logger.warning("Clamping min_instances from 10 to 5 (ceiling)")
```

**Revision Validation:**
```python
# Request: rollback to "demo-app-a-00099-xyz" (doesn't exist)
available = ["demo-app-a-00006-xyz", "demo-app-a-00005-abc"]
raise ValueError(
    f"Target revision demo-app-a-00099-xyz not found. "
    f"Available: {available}"
)
```

## 🧪 Testing

### Manual Testing

1. **Test dry-run mode**
```bash
# Enable dry-run
export DRY_RUN_MODE="true"

# Test rollback (no actual changes)
curl -X POST http://localhost:8081/actions/execute/manual \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "ROLLBACK",
    "service_name": "demo-app-a",
    "region": "us-central1",
    "target_revision": "demo-app-a-00005-abc"
  }'
```

Expected output:
```json
{
  "status": "success",
  "result": {
    "dry_run": true,
    "service": "demo-app-a",
    "target_revision": "demo-app-a-00005-abc",
    "old_traffic": {"demo-app-a-00006-xyz": 100},
    "new_traffic": {"demo-app-a-00005-abc": 100}
  }
}
```

2. **Test real rollback**
```bash
# Disable dry-run
export DRY_RUN_MODE="false"

# List available revisions first
gcloud run revisions list --service=demo-app-a --region=us-central1

# Execute rollback to previous revision
curl -X POST http://localhost:8081/actions/execute/manual \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "ROLLBACK",
    "service_name": "demo-app-a",
    "region": "us-central1",
    "target_revision": "demo-app-a-00005-abc",
    "incident_id": "manual_test_123"
  }'
```

3. **Verify traffic shift**
```bash
# Check current traffic distribution
gcloud run services describe demo-app-a --region=us-central1 --format='value(status.traffic)'
```

### End-to-End Testing

1. **Inject fault in demo app**
```bash
curl -X POST https://demo-app-a-xxx.run.app/fault/enable?type=5xx&error_rate=15&duration=300
```

2. **Wait for Supervisor to detect** (2-3 minutes)
```bash
# Monitor supervisor logs
gcloud logging read "resource.labels.service_name=supervisor-api AND textPayload:Anomaly" --limit=5
```

3. **Verify Fixer receives action**
```bash
# Monitor fixer logs
gcloud logging read "resource.labels.service_name=fixer-agent AND textPayload:Received" --limit=5
```

4. **Check action execution**
```bash
# Look for rollback completion
gcloud logging read "resource.labels.service_name=fixer-agent AND textPayload:Rollback" --limit=5
```

5. **Verify service recovered**
```bash
# Check service status
curl https://supervisor-api-xxx.run.app/services/status
```

### Expected Behavior

**Healthy Service (before fault):**
```json
{
  "name": "demo-app-a",
  "status": "healthy",
  "error_rate": 0.5,
  "latency_p95": 150.0
}
```

**After fault injection:**
```json
{
  "name": "demo-app-a",
  "status": "unhealthy",
  "error_rate": 15.5,
  "has_anomaly": true
}
```

**After automatic rollback:**
```json
{
  "name": "demo-app-a",
  "status": "healthy",
  "error_rate": 0.4,
  "latency_p95": 140.0
}
```

## 🔐 IAM Permissions

The `fixer-sa` service account needs:

```bash
# Execute Cloud Run actions
roles/run.admin

# Subscribe to Pub/Sub
roles/pubsub.subscriber

# Update Firestore
roles/datastore.user

# Write logs
roles/logging.logWriter
```

Grant permissions:
```bash
# Cloud Run admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Pub/Sub subscriber
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

# Firestore user
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

## 📊 Metrics and Monitoring

The Fixer Agent itself can be monitored:

**Key Metrics:**
- Actions executed per hour
- Action success/failure rate
- Action execution duration
- Pub/Sub message processing latency

**Logs:**
```bash
# View fixer agent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=fixer-agent" --limit=50

# Filter for errors
gcloud logging read "resource.labels.service_name=fixer-agent AND severity>=ERROR" --limit=20

# Filter for specific action type
gcloud logging read "resource.labels.service_name=fixer-agent AND textPayload:ROLLBACK" --limit=10
```

**Health Status:**
```bash
# Check if fixer is healthy
curl https://fixer-agent-xxx.run.app/health
```

## 🐛 Troubleshooting

### Issue: "Service account does not have permission"
**Cause:** fixer-sa lacks Cloud Run Admin API permissions

**Error Message:**
```
Permission 'run.services.update' denied on resource 'projects/.../services/demo-app-a'
```

**Fix:**
```bash
# Grant run.admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:fixer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

### Issue: "Target revision not found"
**Cause:** Trying to rollback to non-existent or deleted revision

**Error Message:**
```
Target revision demo-app-a-00099-xyz not found. Available: [...]
```

**Fix:**
```bash
# List available revisions
gcloud run revisions list --service=demo-app-a --region=$REGION

# Use an existing revision
```

### Issue: "Pub/Sub messages not received"
**Cause:** Push subscription not configured correctly

**Fix:**
1. Verify subscription exists:
```bash
gcloud pubsub subscriptions describe agent-actions-sub
```

2. Check push endpoint:
```bash
# Should point to fixer agent /actions/execute
gcloud pubsub subscriptions describe agent-actions-sub --format='value(pushConfig.pushEndpoint)'
```

3. Ensure service account has permissions:
```bash
# Fixer service should NOT allow unauthenticated access
gcloud run services describe fixer-agent --region=$REGION --format='value(spec.template.spec.containers[0].env)'
```

4. Test manually:
```bash
# Publish test message
gcloud pubsub topics publish agent-actions \
  --message='{"action_type":"NONE","service_name":"test","region":"us-central1","incident_id":"test_123"}'

# Check fixer logs
gcloud logging read "resource.labels.service_name=fixer-agent AND textPayload:Received" --limit=1
```

### Issue: "Operation timeout"
**Cause:** Cloud Run operation took longer than 5 minutes

**Fix:**
```bash
# Check Cloud Run service status
gcloud run services describe demo-app-a --region=$REGION

# Look for stuck operations
gcloud run operations list --region=$REGION --filter="metadata.target:demo-app-a"
```

### Issue: "Scaling limits rejected"
**Cause:** Requested values outside safety bounds

**Error Message:**
```
min_instances (10) cannot be greater than max_instances (5)
```

**Fix:**
```bash
# Adjust safety limits
export MIN_INSTANCES_CEILING="10"
export MAX_INSTANCES_CEILING="50"

# Or request valid values
# min=3, max=20 (both within bounds)
```

## ✅ Deployment Verification

After deploying, verify the service is working correctly:

**1. Check deployment status:**
```bash
gcloud run services describe fixer-agent --region=$REGION
```

**2. Test health endpoint:**
```bash
# Get the service URL
export FIXER_URL=$(gcloud run services describe fixer-agent --region=$REGION --format='value(status.url)')

# Check health (requires auth token since not public)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" $FIXER_URL/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "cloud_run_client": true
}
```

**3. Test manual action (dry-run):**
```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -X POST $FIXER_URL/actions/execute/manual \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "NONE",
    "service_name": "test",
    "region": "us-central1"
  }'
```

**4. Verify Pub/Sub subscription:**
```bash
# Check subscription exists and points to fixer
gcloud pubsub subscriptions describe agent-actions-sub
```

**5. Check logs for startup:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=fixer-agent AND textPayload:\"Cloud Run client initialized\"" --limit=5
```

## 🔄 Roadmap

### Phase 1: Core Actions ✅ (Complete)
- [x] Cloud Run Admin API integration
- [x] Traffic rollback with revision validation
- [x] Scaling actions with safety limits
- [x] Dry-run mode for testing
- [x] Modular architecture (cloud_run_manager, models)

### Phase 2: Incident Integration 🚧 (Planned)
- [ ] Firestore incident status updates
- [ ] Action result recording
- [ ] MTTR calculation
- [ ] Refactor main.py to use modules (lifespan manager)

### Phase 3: Advanced Features (Future)
- [ ] Canary rollback (gradual traffic shift)
- [ ] Rollback validation (health check after rollback)
- [ ] Automatic rollback revert (if health doesn't improve)
- [ ] Multi-region action coordination
- [ ] Custom action workflows
- [ ] Action approval workflow (manual confirmation)

### Phase 4: Observability (Future)
- [ ] Action history UI in dashboard
- [ ] Success/failure rate metrics
- [ ] Execution duration tracking
- [ ] Cost impact analysis (scaling changes)

## 📚 Related Documentation

- [AgentOps Main README](../../README.md)
- [Supervisor API README](../supervisor-api/README.MD)
- [Dashboard README](../dashboard-web/README.md)
- [Deployment Guide](../../DEPLOYMENT_GUIDE.md)

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional action types (custom actions)
- Rollback validation logic
- Multi-region coordination
- Enhanced safety checks
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
