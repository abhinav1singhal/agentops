# AgentOps System Architecture

## High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "External Trigger"
        CS[Cloud Scheduler<br/>Every 2 minutes]
    end

    subgraph "Monitoring & Analysis"
        SA[Supervisor API<br/>Port 8080<br/>FastAPI]
        HS[Health Scanner<br/>Module]
        GR[Gemini Reasoner<br/>AI Analysis]
        FC[Firestore Client<br/>Incident Store]
    end

    subgraph "Message Queue"
        PS[Pub/Sub Topic<br/>remediation-actions]
        SUB[Pub/Sub Subscription<br/>Push to Fixer]
    end

    subgraph "Remediation Engine"
        FA[Fixer Agent<br/>Port 8080<br/>FastAPI]
        CRM[Cloud Run Manager<br/>Rollback/Scale]
        FU[Firestore Updater<br/>Status Tracking]
    end

    subgraph "User Interface"
        DW[Dashboard Web<br/>Port 3000<br/>Next.js]
        UI[User Browser]
    end

    subgraph "Target Services"
        DA1[demo-app-a<br/>Python/FastAPI]
        DA2[demo-app-b<br/>Node.js/Express]
        SVC[Other Cloud Run<br/>Services]
    end

    subgraph "GCP Services"
        CM[Cloud Monitoring<br/>Metrics API]
        CL[Cloud Logging<br/>Logs API]
        CR[Cloud Run Admin<br/>API]
        FS[Firestore<br/>Database]
        VA[Vertex AI<br/>Gemini 1.5 Flash]
    end

    %% Monitoring Flow
    CS -->|POST /health/scan| SA
    SA --> HS
    HS -->|Fetch Metrics| CM
    HS -->|Fetch Logs| CL
    HS -->|Check Status| DA1
    HS -->|Check Status| DA2
    HS -->|Check Status| SVC

    %% Analysis Flow
    HS -->|Anomalies Detected| GR
    GR -->|AI Analysis| VA
    GR -->|Store Incident| FC
    FC -->|Write| FS

    %% Remediation Trigger
    GR -->|Publish Action| PS
    PS -->|Push Message| SUB
    SUB -->|POST /actions/execute| FA

    %% Remediation Execution
    FA --> CRM
    FA --> FU
    CRM -->|Rollback/Scale| CR
    CR -->|Update| DA1
    CR -->|Update| DA2
    CR -->|Update| SVC
    FU -->|Update Status| FS

    %% Dashboard Flow
    UI -->|HTTPS| DW
    DW -->|GET /services/status| SA
    DW -->|GET /incidents| SA
    DW -->|POST /explain/:id| SA
    SA -->|Read Incidents| FS

    %% User Testing
    UI -->|POST /inject-fault| DA1
    UI -->|POST /inject-fault| DA2

    %% Styling
    classDef monitoring fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef remediation fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef ui fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef services fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef gcp fill:#fce4ec,stroke:#880e4f,stroke-width:2px

    class SA,HS,GR,FC monitoring
    class FA,CRM,FU remediation
    class DW,UI ui
    class DA1,DA2,SVC services
    class CM,CL,CR,FS,VA,PS,SUB gcp
```

## Component Descriptions

### 1. Supervisor API (Monitoring & Analysis)
- **Technology**: Python FastAPI
- **Port**: 8080
- **Purpose**: Continuous health monitoring and AI-powered analysis
- **Key Modules**:
  - **Health Scanner**: Fetches metrics from Cloud Monitoring and logs from Cloud Logging
  - **Gemini Reasoner**: Uses Vertex AI Gemini 1.5 Flash for root cause analysis
  - **Firestore Client**: Persists incidents with full context
  - **Pub/Sub Publisher**: Triggers remediation actions

### 2. Fixer Agent (Remediation Engine)
- **Technology**: Python FastAPI
- **Port**: 8080
- **Purpose**: Executes remediation actions on Cloud Run services
- **Key Modules**:
  - **Cloud Run Manager**: Handles rollback to previous revisions and scaling adjustments
  - **Firestore Updater**: Tracks incident lifecycle (action_pending → remediating → resolved/failed)
  - **Action Executor**: Receives Pub/Sub messages and executes actions

### 3. Dashboard Web (User Interface)
- **Technology**: Next.js 14, React, Tailwind CSS
- **Port**: 3000
- **Purpose**: Real-time visualization and monitoring
- **Key Features**:
  - Service health cards with color-coded metrics
  - Incident timeline with AI recommendations
  - Analytics dashboard with charts (Recharts)
  - Dark mode support
  - Incident details modal with slide-in animation (Framer Motion)

### 4. Demo Apps (Test Services)
- **demo-app-a**: Python FastAPI with fault injection endpoints
- **demo-app-b**: Node.js Express with fault injection endpoints
- **Purpose**: Reliable testing and demonstration of auto-remediation

### 5. GCP Services Integration

| Service | Purpose | Usage |
|---------|---------|-------|
| **Cloud Run** | Hosting all services | Serverless container platform |
| **Cloud Scheduler** | Trigger scans | POST to supervisor-api every 2 minutes |
| **Cloud Monitoring** | Metrics collection | Error rates, latency, request counts |
| **Cloud Logging** | Log aggregation | Error logs, stack traces |
| **Firestore** | Data persistence | Incidents, actions, audit trail |
| **Pub/Sub** | Event messaging | Async remediation triggering |
| **Vertex AI** | AI analysis | Gemini 1.5 Flash for root cause analysis |

## Data Flow Summary

### Detection Phase
1. Cloud Scheduler triggers supervisor-api every 2 minutes
2. Health Scanner fetches metrics and logs for all services
3. Anomaly detection compares against thresholds
4. If anomaly detected → proceed to Analysis Phase

### Analysis Phase
1. Gemini Reasoner gathers context (metrics, logs, revision history)
2. Sends context to Vertex AI Gemini 1.5 Flash
3. AI returns root cause analysis and recommended action
4. Incident created in Firestore with full context
5. Pub/Sub message published with action details

### Remediation Phase
1. Pub/Sub pushes message to fixer-agent endpoint
2. Fixer Agent updates incident status to "remediating"
3. Cloud Run Manager executes action (rollback or scale)
4. Action result captured and logged
5. Incident status updated to "resolved" or "failed"
6. MTTR (Mean Time To Recovery) calculated

### Visualization Phase
1. Dashboard polls supervisor-api every 10 seconds
2. Fetches service status and recent incidents
3. Displays real-time health cards
4. Shows incident timeline with AI recommendations
5. Analytics dashboard shows MTTR and success rate

## Scalability & Reliability

- **Stateless Services**: All components are stateless, enabling horizontal scaling
- **Async Processing**: Pub/Sub decouples detection from remediation
- **Idempotent Actions**: Remediation actions can be safely retried
- **Audit Trail**: Complete incident history in Firestore
- **Safety Controls**: Min/max instance limits, dry-run mode, confidence thresholds
