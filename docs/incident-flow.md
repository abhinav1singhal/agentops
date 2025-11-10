# End-to-End Incident Remediation Flow

## Complete Sequence Diagram

This diagram shows the complete lifecycle of an incident from detection through automated remediation, including all interactions between components.

```mermaid
sequenceDiagram
    autonumber
    participant CS as Cloud Scheduler
    participant SA as Supervisor API
    participant CM as Cloud Monitoring
    participant CL as Cloud Logging
    participant CR as Cloud Run API
    participant VA as Vertex AI Gemini
    participant FS as Firestore
    participant PS as Pub/Sub
    participant FA as Fixer Agent
    participant DW as Dashboard
    participant User as User Browser

    Note over CS,User: PHASE 1: SCHEDULED HEALTH SCAN
    CS->>+SA: POST /health/scan<br/>(every 2 minutes)
    SA->>SA: Health Scanner starts

    loop For each monitored service
        SA->>+CM: List time series<br/>(error_rate, latency, requests)
        CM-->>-SA: Metrics data
        SA->>+CL: Read log entries<br/>(errors, warnings)
        CL-->>-SA: Log entries
        SA->>+CR: Get service status<br/>(revisions, traffic split)
        CR-->>-SA: Service metadata
    end

    SA->>SA: Analyze metrics vs thresholds

    alt No Anomalies Detected
        SA-->>CS: 200 OK {services_scanned: 3, anomalies_detected: 0}
        Note over SA: System healthy - no action needed
    else Anomaly Detected
        Note over SA,VA: PHASE 2: AI-POWERED ANALYSIS
        SA->>SA: Anomaly found!<br/>(e.g., demo-app-a error_rate: 5.2% > 2%)

        SA->>SA: Prepare context for AI
        Note right of SA: Context includes:<br/>- Current metrics<br/>- Error logs<br/>- Recent revisions<br/>- Service config

        SA->>+VA: Generate content<br/>Prompt: Analyze incident<br/>Model: gemini-1.5-flash
        VA->>VA: AI reasoning process
        VA-->>-SA: AI Response:<br/>- Root cause: "Bad deployment in rev-003"<br/>- Recommendation: "Rollback to rev-002"<br/>- Confidence: 0.85<br/>- Explanation: "Error logs show DB timeouts..."

        SA->>SA: Create incident object
        SA->>+FS: Create document in 'incidents' collection
        Note right of FS: Incident data:<br/>- id: inc_20250110_143000<br/>- service: demo-app-a<br/>- status: action_pending<br/>- metrics: {...}<br/>- recommendation: {...}<br/>- explanation: "..."
        FS-->>-SA: Document created

        Note over SA,PS: PHASE 3: TRIGGER REMEDIATION
        SA->>SA: Prepare action message
        SA->>+PS: Publish to 'remediation-actions' topic
        Note right of PS: Message:<br/>- incident_id<br/>- service_name<br/>- action: "ROLLBACK"<br/>- target_revision: "rev-002"<br/>- reason: "High error rate"
        PS-->>-SA: Message ID: msg-12345

        SA-->>CS: 200 OK {services_scanned: 3, anomalies_detected: 1}
    end

    Note over PS,FA: PHASE 4: REMEDIATION EXECUTION
    PS->>+FA: Push subscription<br/>POST /actions/execute
    Note right of FA: Pub/Sub push delivery<br/>with action details

    FA->>FA: Validate action message
    FA->>+FS: Update incident status
    Note right of FS: status: "action_pending"<br/>→ "remediating"<br/>remediation_started_at: timestamp
    FS-->>-FA: Updated

    FA->>FA: Cloud Run Manager<br/>executes action

    alt Action: ROLLBACK
        FA->>+CR: Update traffic split<br/>service: demo-app-a<br/>revision: rev-002 (100%)<br/>revision: rev-003 (0%)
        CR->>CR: Update traffic allocation
        CR-->>-FA: Rollback successful

        FA->>FA: Verify rollback
        FA->>+CM: Check error rate<br/>(after 30 seconds)
        CM-->>-FA: error_rate: 0.4% ✓

        FA->>+FS: Update incident<br/>status: "resolved"<br/>mttr_seconds: 180
        Note right of FS: Calculate MTTR:<br/>resolved_at - detected_at<br/>= 3 minutes
        FS-->>-FA: Updated

    else Action: SCALE_UP
        FA->>+CR: Update service<br/>min_instances: 3 → 5<br/>max_instances: 10 → 15
        CR-->>-FA: Scaled successfully

        FA->>+FS: Update incident<br/>status: "resolved"
        FS-->>-FA: Updated

    else Action Fails
        FA->>+FS: Update incident<br/>status: "failed"<br/>error_message: "..."
        FS-->>-FA: Updated
    end

    FA-->>-PS: 200 OK (ack message)

    Note over DW,User: PHASE 5: REAL-TIME DASHBOARD UPDATE
    User->>+DW: Open dashboard
    DW->>DW: Auto-refresh every 10s

    DW->>+SA: GET /services/status
    SA->>+CM: Fetch latest metrics
    CM-->>-SA: Current metrics
    SA-->>-DW: Service status array

    DW->>+SA: GET /incidents?limit=10
    SA->>+FS: Query incidents collection<br/>order by detected_at desc
    FS-->>-SA: Recent incidents
    SA-->>-DW: Incidents array

    DW->>DW: Render UI with latest data
    DW-->>-User: Display:<br/>- Services: demo-app-a (Healthy ✓)<br/>- Incident resolved in 3 min<br/>- Analytics: MTTR, success rate

    opt User clicks incident
        User->>+DW: Click incident card
        DW->>+SA: GET /incidents/{incident_id}
        SA->>+FS: Get incident details
        FS-->>-SA: Full incident data
        SA-->>-DW: Complete incident with timeline
        DW-->>-User: Show modal with:<br/>- AI analysis<br/>- Timeline<br/>- Metrics<br/>- Error logs
    end

    Note over CS,User: PHASE 6: CONTINUOUS MONITORING
    Note right of CS: Next scan in 2 minutes...<br/>Cycle repeats
```

## Timeline Breakdown

### Detection to Resolution Timeline

| Time | Event | Component | Duration |
|------|-------|-----------|----------|
| T+0s | Cloud Scheduler triggers scan | Cloud Scheduler | - |
| T+5s | Health Scanner detects anomaly | Supervisor API | 5s |
| T+10s | Gemini AI analysis complete | Vertex AI | 5s |
| T+12s | Incident created in Firestore | Firestore | 2s |
| T+15s | Action published to Pub/Sub | Pub/Sub | 3s |
| T+16s | Fixer Agent receives message | Fixer Agent | 1s |
| T+18s | Incident status → remediating | Firestore | 2s |
| T+20s | Rollback executed on Cloud Run | Cloud Run API | 2s |
| T+50s | Verification scan (metrics check) | Cloud Monitoring | 30s |
| T+52s | Incident status → resolved | Firestore | 2s |
| T+60s | Dashboard shows updated status | Dashboard | - |

**Total MTTR (Mean Time To Recovery): ~52 seconds** (automated)

Compare to manual process: 15-30 minutes average

## State Transitions

### Incident Status Lifecycle

```mermaid
stateDiagram-v2
    [*] --> action_pending: Anomaly Detected<br/>Incident Created

    action_pending --> remediating: Fixer Agent<br/>Receives Action

    remediating --> resolved: Action Successful<br/>Metrics Normal
    remediating --> failed: Action Failed<br/>or Metrics Still Bad

    resolved --> [*]: Incident Closed<br/>MTTR Calculated
    failed --> [*]: Incident Closed<br/>Manual Review Needed

    note right of action_pending
        AI analysis complete
        Recommendation ready
        Waiting for execution
    end note

    note right of remediating
        Rollback/Scale in progress
        Status tracked in real-time
        Verification pending
    end note

    note right of resolved
        Service healthy
        MTTR recorded
        Shown in dashboard
    end note

    note right of failed
        Manual intervention needed
        Logs captured for review
        Alert sent
    end note
```

## Key Decision Points

### 1. Threshold Detection
```
IF error_rate > 2.0%:
    → Anomaly detected
ELSE IF latency_p95 > 1000ms:
    → Anomaly detected
ELSE:
    → System healthy
```

### 2. AI Confidence Scoring
```
IF confidence >= 0.8:
    → Publish remediation action
ELSE IF confidence >= 0.6:
    → Flag for review (future feature)
ELSE:
    → Log incident, no auto-action
```

### 3. Action Selection
```
IF error_rate_spike AND recent_deployment:
    → Recommend ROLLBACK
ELSE IF latency_high AND low_instances:
    → Recommend SCALE_UP
ELSE IF memory_usage_high:
    → Recommend SCALE_UP
ELSE:
    → No clear action, investigate
```

### 4. Verification Logic
```
AFTER action execution:
    WAIT 30 seconds
    CHECK metrics again
    IF metrics_normal:
        → Mark resolved
    ELSE:
        → Mark failed, needs review
```

## Error Handling & Resilience

### Retry Logic
- **Cloud Monitoring API**: 3 retries with exponential backoff
- **Gemini API**: 2 retries (with rate limit handling)
- **Firestore writes**: Best effort, logs errors but doesn't fail
- **Cloud Run updates**: Single attempt (idempotent operation)

### Failure Scenarios

#### Scenario 1: Gemini API Unavailable
```
Detection → Health Scanner ✓
Analysis → Gemini API ✗ (503 error)
Fallback → Use rule-based recommendation
Result → Action still executed (reduced confidence)
```

#### Scenario 2: Fixer Agent Unreachable
```
Detection → Supervisor API ✓
Pub/Sub → Message published ✓
Delivery → Fixer Agent ✗ (endpoint down)
Retry → Pub/Sub retries up to 7 days
Result → Eventually consistent (or DLQ after max retries)
```

#### Scenario 3: Rollback Fails
```
Execution → Cloud Run API ✗ (permission denied)
Status → Incident marked "failed"
Notification → Dashboard shows failed incident
Action → Manual intervention required
Audit → Full error logged in Firestore
```

## Performance Characteristics

### Throughput
- **Services monitored**: Up to 100 services
- **Scan frequency**: Every 2 minutes (720 scans/day)
- **Concurrent incidents**: Up to 10 simultaneous remediations
- **Dashboard refresh**: 10-second polling interval

### Latency
- **Detection latency**: 2-3 minutes (scan interval)
- **Analysis latency**: 2-5 seconds (Gemini API)
- **Execution latency**: 2-5 seconds (Cloud Run API)
- **Verification latency**: 30 seconds (metrics stabilization)
- **End-to-end MTTR**: 1-3 minutes (automated)

### Resource Usage
- **Supervisor API**: ~256 MB memory, 0.5 vCPU (idle)
- **Fixer Agent**: ~128 MB memory, 0.2 vCPU (idle)
- **Dashboard**: ~512 MB memory, 1 vCPU (build), ~128 MB (runtime)
- **Firestore**: ~1 KB per incident document
- **Pub/Sub**: Standard messaging costs

## Best Practices Demonstrated

1. **Separation of Concerns**: Detection, analysis, remediation are independent
2. **Event-Driven Architecture**: Pub/Sub decouples components
3. **Observability**: Full audit trail in Firestore
4. **Idempotency**: Actions can be safely retried
5. **Graceful Degradation**: System continues with rule-based fallbacks
6. **Security**: Service accounts with least privilege IAM
7. **Scalability**: Stateless services enable horizontal scaling
8. **Cost Optimization**: Min instances = 0 for non-critical services
