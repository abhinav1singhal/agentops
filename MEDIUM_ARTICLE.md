# How I Built an AI-Powered Auto-Remediation System for Cloud Run (And Cut MTTR by 90%)

## The 3 AM Wake-Up Call That Changed Everything

Picture this: It's 3 AM. Your phone buzzes. Production is down. You groggily stumble to your laptop, spend 20 minutes investigating logs and metrics, and finally execute a rollback. By the time you're back in bed, 30 minutes have passed, revenue has been lost, and you're wide awake.

Sound familiar?

This scenario plays out thousands of times daily across engineering teams. But what if we could teach an AI to handle these incidents automatically—detecting issues, analyzing root causes, and executing fixes in under 3 minutes?

That's exactly what I built with **AgentOps**, an intelligent control plane for Google Cloud Run that reduces Mean Time To Recovery (MTTR) from 15-30 minutes to under 3 minutes using Gemini AI.

## The Problem: Manual Incident Response Doesn't Scale

Traditional incident response follows this painful workflow:

1. **Detection** (5-10 min): Wait for alerts or customers to complain
2. **Analysis** (5-15 min): Manually correlate metrics, logs, and deployments
3. **Remediation** (5-10 min): Execute rollback or scaling under pressure
4. **Verification** (2-5 min): Confirm the fix worked

**Total MTTR: 15-30 minutes** of stressful, error-prone manual work.

The kicker? About 80% of production incidents follow predictable patterns:
- Error rate spikes after bad deployments
- Latency increases due to insufficient resources
- Memory exhaustion from traffic spikes

We don't need humans for these. We need **intelligent automation**.

## The Solution: AI-Powered Autonomous Remediation

AgentOps flips the script with a closed-loop system:

1. **Detect**: Cloud Scheduler triggers health scans every 2 minutes
2. **Analyze**: Gemini 1.5 Flash analyzes metrics, logs, and deployment history
3. **Act**: Fixer Agent executes rollbacks or scaling automatically
4. **Verify**: System confirms remediation worked and calculates MTTR

**Result: <3 minute MTTR** with zero manual intervention.

## Architecture: Event-Driven Microservices on Cloud Run

AgentOps leverages Google Cloud Run's serverless architecture with 5 specialized microservices:

### 1. Supervisor API (Python FastAPI)
The brain of the operation:
- Fetches metrics from Cloud Monitoring API
- Reads error logs from Cloud Logging
- Detects anomalies (error rate > 2%, latency P95 > 1000ms)
- Sends context to Gemini for analysis
- Creates incidents in Firestore
- Publishes remediation actions to Pub/Sub

```python
async def analyze_incident(self, service_health: ServiceHealth) -> IncidentAnalysis:
    """Use Gemini AI to analyze the incident"""

    # Gather context
    context = {
        "metrics": service_health.metrics,
        "error_logs": service_health.log_samples,
        "recent_deployments": await self._get_recent_revisions(service_name),
        "service_config": await self._get_service_config(service_name)
    }

    # Send to Gemini
    prompt = self._build_analysis_prompt(context)
    response = await self.gemini_client.generate_content(prompt)

    # Parse AI recommendation
    return IncidentAnalysis(
        root_cause=response.root_cause,
        recommendation=response.recommendation,
        confidence=response.confidence,
        explanation=response.explanation
    )
```

### 2. Fixer Agent (Python FastAPI)
The hands that execute:
- Consumes Pub/Sub messages via push subscription
- Executes Cloud Run API operations (rollback, scaling)
- Updates incident status in Firestore
- Verifies remediation success

```python
async def execute_rollback(self, action: RemediationAction):
    """Rollback to previous stable revision"""

    # Get current service configuration
    service = self.run_client.get_service(action.service_name)

    # Find stable revision (not the latest)
    stable_revision = self._find_stable_revision(service)

    # Update traffic split: 100% to stable, 0% to bad revision
    service.traffic = [
        {"revision": stable_revision, "percent": 100},
        {"revision": service.latest_revision, "percent": 0}
    ]

    # Execute the change
    operation = self.run_client.update_service(service)
    await operation.wait_async()

    logger.info(f"Rolled back {action.service_name} to {stable_revision}")
```

### 3. Dashboard Web (Next.js + React)
The eyes that see:
- Real-time service health visualization
- Incident timeline with AI recommendations
- Analytics dashboard with MTTR tracking
- Dark mode, responsive design, smooth animations

### 4 & 5. Demo Apps (Python FastAPI + Node.js Express)
The guinea pigs:
- Built-in fault injection endpoints
- Configurable error rates and latency
- Perfect for testing and demonstrations

## The Magic: How Gemini AI Analyzes Incidents

This is where things get interesting. Instead of rigid rule-based thresholds, I use Gemini 1.5 Flash to perform **contextual analysis**.

Here's what I send to the AI:

```
You are an expert SRE analyzing a Cloud Run incident.

SERVICE: demo-app-a
CURRENT METRICS:
- Error rate: 5.2% (threshold: 2.0%)
- Latency P95: 245ms
- Request count: 1,247 requests/min

RECENT ERROR LOGS:
[2025-01-10 14:32:15] 500 Internal Server Error - Database timeout
[2025-01-10 14:32:18] 500 Internal Server Error - Connection refused
[2025-01-10 14:32:22] 503 Service Unavailable - Upstream timeout

RECENT DEPLOYMENTS:
- rev-003: Deployed 5 minutes ago (current, receiving 100% traffic)
- rev-002: Deployed 2 days ago (stable, 0.3% error rate)
- rev-001: Deployed 1 week ago (stable, 0.2% error rate)

SERVICE CONFIGURATION:
- Min instances: 0
- Max instances: 10
- Current instances: 3
- Memory: 512Mi
- CPU: 1

Analyze this incident and provide:
1. Root cause (2-3 sentences)
2. Recommended action (ROLLBACK, SCALE_UP, or INVESTIGATE)
3. Confidence score (0.0-1.0)
4. Human-readable explanation for the team
```

Gemini responds with structured analysis:

```json
{
  "root_cause": "Error rate spike correlates precisely with rev-003 deployment 5 minutes ago. Error logs show database timeouts and connection issues not present in previous revisions.",

  "recommendation": "ROLLBACK",

  "target_revision": "rev-002",

  "confidence": 0.87,

  "explanation": "The timing and error patterns strongly suggest rev-003 introduced a regression. Database timeout errors were absent in rev-002 logs. Recommend immediate rollback to restore service health, then investigate rev-003 in staging environment."
}
```

## The Results: 90% MTTR Reduction

Let's compare manual vs. automated response for a real incident:

### Before AgentOps (Manual)
```
03:00 AM - Error rate spikes to 5.2%
03:00 AM - PagerDuty alert wakes engineer
03:03 AM - Engineer logs in, opens dashboard
03:08 AM - Identifies bad deployment in rev-003
03:15 AM - Manually rolls back to rev-002
03:20 AM - Confirms error rate back to normal
03:25 AM - Documents incident, goes back to bed

Total MTTR: 25 minutes
```

### After AgentOps (Automated)
```
03:00 AM - Error rate spikes to 5.2%
03:02 AM - Cloud Scheduler triggers health scan
03:02 AM - Supervisor detects anomaly, queries Gemini
03:02 AM - Gemini recommends rollback (87% confidence)
03:02 AM - Incident created, action published to Pub/Sub
03:02 AM - Fixer Agent receives message
03:02 AM - Rollback to rev-002 executed
03:03 AM - Verification: error rate 0.3% ✓
03:03 AM - Incident marked resolved, MTTR: 2m 47s

Total MTTR: 2 minutes 47 seconds
Engineer: Still sleeping peacefully
```

**Impact: 90% reduction in MTTR** (25 min → 2.8 min)

## Building Blocks: Key Technologies

### Google Cloud Run
The foundation. Cloud Run's **revision-aware architecture** is perfect for rollbacks:
- Each deployment creates a new immutable revision
- Traffic splitting enables instant rollback
- Serverless scaling handles variable load
- Min instances = 0 keeps costs low

### Vertex AI Gemini 1.5 Flash
The intelligence. Why Gemini?
- **Fast**: 2-5 second response time
- **Cheap**: $0.0002 per prompt (100 incidents = $0.02)
- **Contextual**: Analyzes full context, not just thresholds
- **Explainable**: Provides human-readable reasoning

### Cloud Scheduler
The heartbeat. Triggers health scans every 2 minutes:
- Reliable cron-like execution
- OIDC authentication to Cloud Run
- Configurable retry policies
- Sub-$1/month cost

### Pub/Sub
The nervous system. Decouples detection from remediation:
- Async, event-driven processing
- Automatic retry with exponential backoff
- Dead letter queue for failed actions
- Scales to millions of messages

### Firestore
The memory. Stores incident history:
- NoSQL flexibility for varying incident types
- Real-time updates to dashboard
- Complete audit trail for compliance
- Automatic MTTR calculation

## Lessons Learned: What Worked (And What Didn't)

### ✅ What Worked

**1. AI Over Rules**
Initial version used rigid thresholds: "error rate > 5% = rollback". Problem? Too many false positives. Gemini's contextual analysis dramatically improved accuracy.

**2. Event-Driven Architecture**
Pub/Sub decoupling was brilliant. Supervisor and Fixer Agent can scale independently. If Fixer is down, messages queue until it recovers.

**3. Cloud Run Revisions**
Using Cloud Run's native revision system (vs. custom version tracking) simplified rollback logic and made it instant.

**4. Built-In Testing**
Fault injection endpoints made demo prep painless. No need to actually break production to test the system.

### ❌ What Didn't Work

**1. Cloud Monitoring Metrics Delay**
Cloud Run metrics can take 15-30 minutes to propagate to the Monitoring API on first deployment.

**Workaround**: Let Cloud Scheduler run overnight. By morning, metrics flow normally. For demos, show logs as backup.

**2. Next.js Environment Variables**
Spent 2 hours debugging why dashboard couldn't connect to supervisor-api. Turns out `NEXT_PUBLIC_*` vars must be set at **build time**, not runtime.

**Solution**: Use Docker build args in `cloudbuild.yaml`:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'NEXT_PUBLIC_SUPERVISOR_API_URL=https://supervisor-api-xxx.run.app'
```

**3. Too Aggressive Rollback Initially**
Early version rolled back on any error rate increase. Learned to add:
- Minimum request threshold (100 requests)
- Confidence scoring (>0.8 for auto-action)
- Time-based grace period (5 minutes after deployment)

## Cost Analysis: $10/Month for Peace of Mind

Monthly cost breakdown for monitoring 5 services:

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run (5 services) | 720 requests/day each | $5 |
| Cloud Scheduler | 1 job, 720 runs/day | $0.10 |
| Cloud Monitoring | Metrics API calls | $2 |
| Cloud Logging | Log ingestion | $1 |
| Vertex AI (Gemini) | ~100 incidents/month | $0.02 |
| Pub/Sub | ~100 messages/month | $0.10 |
| Firestore | ~100 documents | $1 |
| **Total** | | **$9.22/month** |

**ROI Calculation**:
- Manual response: 20 min × 4 incidents/month × $100/hr = **$133/month**
- AgentOps cost: **$10/month**
- Engineer time saved: **$123/month**

Plus intangibles:
- Eliminated 3 AM pages
- Faster recovery = less downtime
- Complete audit trail for compliance
- Improved team morale

## Getting Started: Deploy in 10 Minutes

Want to try it yourself? The entire system is open source:

```bash
# Clone repository
git clone https://github.com/abhinav1singhal/agentops.git
cd agentops

# Set GCP project
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Setup infrastructure (APIs, IAM, Pub/Sub, Firestore)
cd infra/scripts
./setup-gcp.sh

# Deploy all 5 services
./deploy-all.sh

# Open dashboard
DASHBOARD_URL=$(gcloud run services describe dashboard-web \
  --region=$REGION --format='value(status.url)')
open $DASHBOARD_URL
```

## Testing: Inject Fault, Watch Magic Happen

Built-in fault injection makes testing easy:

```bash
# Inject 20% error rate for 15 minutes
curl -X POST "https://demo-app-a-xxx.run.app/fault/enable?type=5xx&error_rate=20&duration=900"

# Wait 2-3 minutes for detection
sleep 180

# Check incidents
curl "https://supervisor-api-xxx.run.app/incidents?limit=5"
```

Expected output:
```json
{
  "incidents": [
    {
      "id": "inc_20250110_143200",
      "service": "demo-app-a",
      "status": "resolved",
      "detected_at": "2025-01-10T14:32:00Z",
      "resolved_at": "2025-01-10T14:34:47Z",
      "mttr_seconds": 167,
      "error_rate": 5.2,
      "recommendation": {
        "action": "ROLLBACK",
        "confidence": 0.87,
        "explanation": "Error rate spike correlates with rev-003..."
      }
    }
  ]
}
```

## Real-World Applications Beyond Demo Apps

While this project uses demo apps, the architecture scales to real production scenarios:

### E-Commerce Platform
**Scenario**: Payment service error rate spikes
**Detection**: 3.2% error rate (threshold: 2%)
**Analysis**: Gemini identifies database connection pool exhaustion
**Action**: Scale min_instances from 2 to 5
**Result**: Error rate drops to 0.4%, no customer impact

### Microservices API Gateway
**Scenario**: API gateway latency increases
**Detection**: P95 latency 1,800ms (threshold: 1,000ms)
**Analysis**: Upstream service slow, not gateway issue
**Action**: Increase request timeout, scale upstream
**Result**: Latency back to 400ms in 2 minutes

### SaaS Background Jobs
**Scenario**: Job processor memory exhaustion
**Detection**: Container restart loop
**Analysis**: Memory leak in recent deployment
**Action**: Rollback to previous stable version
**Result**: Jobs processing normally, investigate memory leak in staging

## Future Enhancements: What's Next

**1. Multi-Cloud Support**
Extend to AWS ECS, Azure Container Apps using provider abstractions.

**2. Predictive Anomaly Detection**
Use ML to predict incidents before they happen based on metric trends.

**3. Custom Remediation Actions**
Beyond rollback/scale: restart containers, clear caches, circuit breakers.

**4. Team Integrations**
Slack notifications, PagerDuty integration, Jira ticket creation.

**5. Cost Optimization**
Analyze historical data to recommend optimal min/max instance settings.

## Why This Matters: The Future of Operations

We're at an inflection point in software operations. Traditional monitoring tells us **what** happened. AI-powered systems tell us **why** it happened and **what to do** about it.

AgentOps demonstrates three key principles for the future:

**1. Autonomous Systems**
The best incident response is one that doesn't need human intervention for common issues.

**2. AI as Reasoning Engine**
LLMs excel at contextual analysis—exactly what incident response requires.

**3. Event-Driven Architecture**
Decoupled, async systems are more reliable and scalable than monolithic ones.

## Conclusion: From Reactive to Proactive

Building AgentOps taught me that **most production incidents don't need humans**—they need intelligent automation that can:
- Detect issues faster than humans (2 min vs. 5-10 min)
- Analyze context better than humans (considers all data)
- Execute fixes more reliably than humans (no mistakes under pressure)
- Never get tired, never need vacation, never wake up groggy at 3 AM

The result? Teams spend less time firefighting and more time building. Engineers sleep through the night. Customers experience less downtime.

**90% MTTR reduction isn't magic—it's intelligent automation.**

## Resources

- **Live Demo**: [dashboard-web-668107958735.us-central1.run.app](https://dashboard-web-668107958735.us-central1.run.app)
- **GitHub Repository**: [github.com/abhinav1singhal/agentops](https://github.com/abhinav1singhal/agentops)
- **Architecture Docs**: [Complete system design with Mermaid diagrams](https://github.com/abhinav1singhal/agentops/blob/main/docs/architecture-overview.md)
- **Testing Guide**: [Step-by-step demo instructions](https://github.com/abhinav1singhal/agentops/blob/main/DEMO_TEST_GUIDE.md)

## Tech Stack Summary

- **Cloud Platform**: Google Cloud Run, Vertex AI, Pub/Sub, Firestore
- **Backend**: Python 3.11, FastAPI, Cloud Run Admin API
- **Frontend**: Next.js 14, React, Tailwind CSS, Recharts
- **AI**: Gemini 1.5 Flash via Vertex AI
- **Infrastructure**: Cloud Scheduler, Cloud Monitoring, Cloud Logging
- **Lines of Code**: 11,000+ across 5 microservices
- **Documentation**: 3,000+ lines with architecture diagrams

---

**Built for Google Cloud Run Hackathon 2025**

*If you found this useful, give the [GitHub repo](https://github.com/abhinav1singhal/agentops) a star ⭐ and follow me for more content on AI, Cloud, and DevOps automation.*

---

## About the Author

I'm a software engineer passionate about using AI to solve real-world operational problems. When I'm not building autonomous systems, I'm usually exploring new cloud technologies or writing about developer tools.

**Connect with me:**
- GitHub: [@abhinav1singhal](https://github.com/abhinav1singhal)
- Medium: [Your Medium Profile]
- LinkedIn: [Your LinkedIn]
- Twitter/X: [Your Handle]

---

*Have questions or want to contribute? Drop a comment below or open an issue on GitHub!*
