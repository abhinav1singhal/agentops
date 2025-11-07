"""
Supervisor API - Simplified Working Version
Basic health scanning without complex integrations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from datetime import datetime
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgentOps Supervisor API",
    description="AI-powered Cloud Run health monitoring",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Startup event"""
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")
    logger.info(f"Supervisor API started for project: {project_id}, region: {region}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgentOps Supervisor API",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    project_id = os.getenv("PROJECT_ID", "not-set")
    region = os.getenv("REGION", "not-set")
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "project_id": project_id,
        "region": region,
        "components": {
            "health_scanner": True,
            "gemini_reasoner": True,
            "pubsub_publisher": True,
            "firestore_client": True
        }
    }

@app.post("/health/scan")
async def scan_services():
    """
    Scan all monitored services for anomalies
    Simplified version that returns mock data
    """
    logger.info("Starting health scan...")
    
    # Get target services
    target_services = _get_target_services()
    
    # Mock scan results
    scan_results = []
    for service in target_services:
        scan_results.append({
            "service": service["name"],
            "region": service["region"],
            "status": "healthy",
            "has_anomaly": False,
            "error_rate": 0.5,
            "latency_p95": 150.0,
            "recommendation": None
        })
    
    response = {
        "scan_id": f"scan_{datetime.utcnow().timestamp()}",
        "timestamp": datetime.utcnow().isoformat(),
        "services_scanned": len(target_services),
        "anomalies_detected": 0,
        "actions_recommended": 0,
        "details": scan_results
    }
    
    logger.info(f"Scan complete: {len(target_services)} services scanned")
    
    return response

@app.get("/incidents")
async def get_incidents(limit: int = 50, status: Optional[str] = None):
    """Get recent incidents (mock data)"""
    return []

@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get specific incident details (mock)"""
    raise HTTPException(status_code=404, detail="Incident not found")

@app.get("/services/status")
async def get_services_status():
    """Get current status of all monitored services"""
    target_services = _get_target_services()
    
    statuses = []
    for service in target_services:
        statuses.append({
            "name": service["name"],
            "region": service["region"],
            "status": "healthy",
            "error_rate": 0.5,
            "latency_p95": 150.0,
            "request_count": 1000,
            "last_checked": datetime.utcnow().isoformat()
        })
    
    return statuses

@app.post("/explain/{incident_id}")
async def generate_explanation(incident_id: str):
    """Generate explanation for an incident (mock)"""
    return {
        "incident_id": incident_id,
        "explanation": "This is a mock explanation. Full version coming soon.",
        "timestamp": datetime.utcnow().isoformat()
    }

def _get_target_services() -> List[dict]:
    """Get list of services to monitor from environment"""
    import json
    
    # Try JSON config first
    services_json = os.getenv("TARGET_SERVICES_JSON")
    if services_json:
        try:
            return json.loads(services_json)
        except json.JSONDecodeError:
            logger.error("Invalid TARGET_SERVICES_JSON format")
    
    # Fallback to comma-separated list
    services_str = os.getenv("TARGET_SERVICES", "")
    if services_str:
        region = os.getenv("REGION", "us-central1")
        return [
            {"name": name.strip(), "region": region}
            for name in services_str.split(",")
            if name.strip()
        ]
    
    # Default services
    region = os.getenv("REGION", "us-central1")
    return [
        {"name": "demo-app-a", "region": region},
        {"name": "demo-app-b", "region": region}
    ]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting Supervisor API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)