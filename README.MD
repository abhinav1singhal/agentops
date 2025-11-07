# AgentOps - AI-Powered Cloud Run Auto-Remediation

AgentOps is an intelligent control plane that uses Gemini AI to monitor Google Cloud Run services, detect anomalies, and automatically execute remediation actions.

## 🎯 Features

- **Real-time Monitoring**: Tracks Cloud Run service health using Cloud Monitoring
- **AI-Powered Analysis**: Gemini 1.5 Flash analyzes anomalies and recommends actions
- **Automated Remediation**: Executes rollbacks, scaling, and rebuilds automatically
- **Live Dashboard**: Real-time visualization of service health and incidents
- **Fault Injection**: Built-in fault injection for testing and demos

## 🏗️ Architecture

\\\
Cloud Scheduler → Supervisor API (Gemini) → Pub/Sub → Fixer Agent → Cloud Run Services
                         ↓
                   Dashboard (Next.js)
\\\

## 🚀 Quick Start

### Prerequisites

- Google Cloud Project with billing enabled
- gcloud CLI installed
- PowerShell (Windows) or Bash (Linux/Mac)
- Node.js 18+
- Python 3.11+

### 1. Clone Repository

\\\powershell
git clone https://github.com/YOUR_USERNAME/agentops.git
cd agentops
\\\

### 2. Setup GCP Infrastructure

\\\powershell
# Set your project
$env:PROJECT_ID = "your-gcp-project-id"
$env:REGION = "us-central1"

# Run setup
cd infra\scripts
.\setup-gcp.ps1
\\\

### 3. Deploy Services

\\\powershell
.\deploy-all.ps1
\\\

### 4. Open Dashboard

\\\powershell
# Get dashboard URL
$DASHBOARD_URL = (gcloud run services describe dashboard-web --region=$env:REGION --format='value(status.url)')
Start-Process $DASHBOARD_URL
\\\

## 📊 Services

| Service | Description | Port |
|---------|-------------|------|
| **supervisor-api** | Monitors services, calls Gemini AI | 8080 |
| **fixer-agent** | Executes remediation actions | 8081 |
| **demo-app-a** | Python test service with fault injection | 8080 |
| **demo-app-b** | Node.js test service with fault injection | 8080 |
| **dashboard-web** | Next.js monitoring dashboard | 3000 |

## 🎬 Demo

1. Inject fault: \Invoke-RestMethod -Method Post -Uri "DEMO_URL/fault/enable?type=5xx&error_rate=15&duration=300"\
2. Wait 2-3 minutes for detection
3. Watch automatic remediation!

## 🛠️ Configuration

Edit \.env\ file:

\\\ash
PROJECT_ID=your-project-id
REGION=us-central1
ERROR_THRESHOLD=5.0
LATENCY_P95_THRESHOLD_MS=600
TARGET_SERVICES=demo-app-a,demo-app-b
\\\

## 📝 Environment Variables

See \.env.template\ for all available configuration options.

## 🧪 Testing

\\\powershell
# Test supervisor health
Invoke-RestMethod -Uri "SUPERVISOR_URL/health"

# Trigger manual scan
Invoke-RestMethod -Method Post -Uri "SUPERVISOR_URL/health/scan"

# Inject fault
Invoke-RestMethod -Method Post -Uri "DEMO_URL/fault/enable?type=5xx&error_rate=15&duration=300"
\\\

## 💰 Cost Estimate

~\-20/month for demo usage (with generous GCP free tiers)

## 🧹 Cleanup

\\\powershell
cd infra\scripts
.\teardown.ps1

# Or delete entire project
gcloud projects delete $PROJECT_ID
\\\

## 📚 Documentation

- [Architecture](docs/architecture.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Windows Quick Start](WINDOWS_QUICKSTART.md)

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📄 License

MIT License - See LICENSE file

## 🏆 Built With

- Google Cloud Run
- Gemini 1.5 Flash
- FastAPI
- Next.js
- Pub/Sub
- Firestore

---

**Created for Google Cloud AI Hackathon 2024**
