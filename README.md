#Pitch: An AI-powered control plane that automatically detects and fixes Cloud Run service failures using Gemini for intelligent decision-making, with a live dashboard explaining every action taken.
#Core Value: Reduces Mean Time To Recovery (MTTR) from minutes/hours to under 60 seconds by automating incident detection, decision-making, and remediation.



┌─────────────────┐
│  Cloud Scheduler│ ──► Triggers health scans every 1-2 min
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│          SUPERVISOR-API (FastAPI)                    │
│  • Monitors Cloud Run services via APIs              │
│  • Analyzes metrics/logs with Gemini 1.5 Flash      │
│  • Publishes decisions to Pub/Sub                   │
│  • Generates human-readable explanations            │
└─────────────────────────────────────────────────────┘
         │
         │ (Pub/Sub: agent-actions topic)
         ▼
┌─────────────────────────────────────────────────────┐
│          FIXER-AGENT (Cloud Run Job)                 │
│  • Subscribes to action commands                     │
│  • Executes: Traffic rollback, scaling, rebuilds    │
│  • Reports results back                              │
└─────────────────────────────────────────────────────┘
         │
         │ (Actions affect)
         ▼
┌──────────────────┐      ┌──────────────────┐
│  DEMO-APP-A      │      │  DEMO-APP-B      │
│  (with fault     │      │  (with fault     │
│   injection)     │      │   injection)     │
└──────────────────┘      └──────────────────┘
         │                         │
         └─────────┬───────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  DASHBOARD-WEB  │
         │  (Next.js)      │
         │  • Live status  │
         │  • AI decisions │
         │  • Fault inject │
         └─────────────────┘
```

---

## 🔧 Google Cloud Stack

### **Core Services**
1. **Cloud Run** - Host all services & jobs
2. **Pub/Sub** - Agent-to-agent messaging bus
3. **Cloud Monitoring API** - Fetch metrics (latency p95, error rates)
4. **Cloud Logging API** - Query error logs
5. **Cloud Run Admin API** - Traffic splitting, scaling, revision management
6. **Cloud Build** - Automated rebuilds/redeploys
7. **Vertex AI (Gemini 1.5 Flash)** - AI reasoning engine
8. **Cloud Scheduler** - Periodic health scans
9. **Firestore** - Persist incidents & actions
10. **Secret Manager** - API keys & credentials
11. **IAM** - Least-privilege service accounts

---

## 📊 Data Flow (Incident Lifecycle)
```
1. DETECT
   Cloud Scheduler → /health/scan
   ↓
   Supervisor queries last 5-15 min:
   • Cloud Monitoring: latency_p95, error_ratio
   • Cloud Logging: ERROR+ severity logs
   
2. ANALYZE
   Supervisor → Gemini prompt:
   "Service X shows 12% errors (threshold 5%), p95=850ms (threshold 600ms).
    Recent logs: [sample]. Recommend action."
   ↓
   Gemini response:
   "ROLLBACK to revision Y (confidence: 0.86). Current revision likely has bug."

3. DECIDE
   Supervisor validates:
   • 2 consecutive windows exceeded threshold? ✓
   • Latest revision has >80% traffic? ✓
   • Previous revision available? ✓
   ↓
   Publish to Pub/Sub: {action: ROLLBACK, target: demo-app-a, revision: Y, reason: "..."}

4. EXECUTE
   Fixer-Agent receives message
   ↓
   Cloud Run Admin API:
   • Update traffic split: revision-Y=100%, revision-latest=0%
   ↓
   Reports: {status: SUCCESS, executed_at: timestamp}

5. EXPLAIN
   Supervisor generates post-incident note
   ↓
   Dashboard shows: "Incident resolved in 45s. Rolled back to stable revision."
```

---

## 🛠️ APIs & Key Methods

### **1. Cloud Monitoring API**
```
projects.timeSeries.list(
  filter: metric.type="run.googleapis.com/request_latencies"
          resource.service_name="demo-app-a"
  interval: [now-5m, now]
  aggregation: ALIGN_DELTA, REDUCE_MEAN
)
→ Get p95 latency, error ratios
```

### **2. Cloud Logging API**
```
entries.list(
  filter: resource.type="cloud_run_revision"
          resource.labels.service_name="demo-app-a"
          severity>=ERROR
  orderBy: timestamp desc
  pageSize: 50
)
→ Sample recent error logs for context
```

### **3. Cloud Run Admin API**
```
# Get current service state
services.get(name: "projects/.../services/demo-app-a")

# List revisions
revisions.list(parent: "projects/.../services/demo-app-a")

# Traffic split (rollback)
services.patch(
  name: "...",
  updateMask: "traffic",
  body: {
    traffic: [
      {revisionName: "demo-app-a-00003-xyz", percent: 100},
      {revisionName: "demo-app-a-00004-abc", percent: 0}
    ]
  }
)

# Scale adjustment
services.patch(
  updateMask: "template.scaling",
  body: {
    template: {
      scaling: {minInstanceCount: 2, maxInstanceCount: 10}
    }
  }
)
```

### **4. Cloud Build API**
```
projects.triggers.run(
  projectId: "...",
  triggerId: "...",
  source: {substitutions: {_SERVICE: "demo-app-a"}}
)
