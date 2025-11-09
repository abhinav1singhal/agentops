"""
Supervisor API - Main Application
Monitors Cloud Run services and uses Gemini AI for intelligent decision-making
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from models import (
    HealthScanResponse,
    IncidentResponse,
    ActionRequest,
    ServiceStatus
)
from health_scanner import HealthScanner
from gemini_reasoner import GeminiReasoner
from pubsub_publisher import PubSubPublisher
from firestore_client import FirestoreClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
health_scanner: Optional[HealthScanner] = None
gemini_reasoner: Optional[GeminiReasoner] = None
pubsub_publisher: Optional[PubSubPublisher] = None
firestore_client: Optional[FirestoreClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    global health_scanner, gemini_reasoner, pubsub_publisher, firestore_client

    logger.info("Starting Supervisor API...")

    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")

    if not project_id:
        raise ValueError("PROJECT_ID environment variable is required")

    # Initialize components
    health_scanner = HealthScanner(project_id, region)
    gemini_reasoner = GeminiReasoner(project_id, region)
    pubsub_publisher = PubSubPublisher(project_id)
    firestore_client = FirestoreClient(project_id)

    logger.info(f"Supervisor API started for project: {project_id}, region: {region}")

    yield

    # Shutdown
    logger.info("Shutting down Supervisor API...")


# Initialize FastAPI app
app = FastAPI(
    title="AgentOps Supervisor API",
    description="AI-powered Cloud Run health monitoring and auto-remediation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "health_scanner": health_scanner is not None,
            "gemini_reasoner": gemini_reasoner is not None,
            "pubsub_publisher": pubsub_publisher is not None,
            "firestore_client": firestore_client is not None
        }
    }


@app.post("/health/scan", response_model=HealthScanResponse)
async def scan_services():
    """
    Scan all monitored services for anomalies
    This is the main endpoint triggered by Cloud Scheduler
    """
    logger.info("Starting health scan...")

    try:
        # Get list of services to monitor
        target_services = _get_target_services()

        if not target_services:
            logger.warning("No target services configured")
            return HealthScanResponse(
                scan_id=f"scan_{datetime.utcnow().timestamp()}",
                timestamp=datetime.utcnow(),
                services_scanned=0,
                anomalies_detected=0,
                actions_recommended=0,
                details=[]
            )

        # Scan each service
        scan_results = []
        anomalies_count = 0
        actions_count = 0

        for service_config in target_services:
            service_name = service_config["name"]
            service_region = service_config.get("region", os.getenv("REGION", "us-central1"))

            logger.info(f"Scanning service: {service_name} in {service_region}")

            # Get health metrics
            health_status = await health_scanner.scan_service(service_name, service_region)

            # Check if anomaly detected
            if health_status.has_anomaly:
                anomalies_count += 1
                logger.warning(f"Anomaly detected in {service_name}: {health_status.anomaly_summary}")

                # Get AI recommendation
                recommendation = await gemini_reasoner.analyze_and_recommend(health_status)

                if recommendation.action != "NONE":
                    actions_count += 1

                    # Create incident record
                    incident = await firestore_client.create_incident(
                        service_name=service_name,
                        health_status=health_status,
                        recommendation=recommendation
                    )

                    # Publish action to Pub/Sub for fixer agent
                    action_request = ActionRequest(
                        incident_id=incident.id,
                        service_name=service_name,
                        region=service_region,
                        action_type=recommendation.action,
                        target_revision=recommendation.target_revision,
                        reason=recommendation.reasoning,
                        confidence=recommendation.confidence
                    )

                    await pubsub_publisher.publish_action(action_request)

                    logger.info(f"Action published for {service_name}: {recommendation.action}")

            scan_results.append({
                "service": service_name,
                "region": service_region,
                "status": health_status.status,
                "has_anomaly": health_status.has_anomaly,
                "error_rate": health_status.error_rate,
                "latency_p95": health_status.latency_p95,
                "recommendation": recommendation.action if health_status.has_anomaly else None
            })

        response = HealthScanResponse(
            scan_id=f"scan_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            services_scanned=len(target_services),
            anomalies_detected=anomalies_count,
            actions_recommended=actions_count,
            details=scan_results
        )

        logger.info(f"Scan complete: {anomalies_count} anomalies, {actions_count} actions")

        return response

    except Exception as e:
        logger.error(f"Error during health scan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health scan failed: {str(e)}")


@app.get("/incidents", response_model=List[IncidentResponse])
async def get_incidents(limit: int = 50, status: Optional[str] = None):
    """Get recent incidents"""
    try:
        incidents = await firestore_client.get_incidents(limit=limit, status=status)
        return incidents
    except Exception as e:
        logger.error(f"Error fetching incidents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str):
    """Get specific incident details"""
    try:
        incident = await firestore_client.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        return incident
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching incident: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/status", response_model=List[ServiceStatus])
async def get_services_status():
    """Get current status of all monitored services"""
    try:
        target_services = _get_target_services()
        statuses = []

        for service_config in target_services:
            service_name = service_config["name"]
            service_region = service_config.get("region", os.getenv("REGION", "us-central1"))

            health_status = await health_scanner.scan_service(service_name, service_region)

            statuses.append(ServiceStatus(
                name=service_name,
                region=service_region,
                status=health_status.status,
                error_rate=health_status.error_rate,
                latency_p95=health_status.latency_p95,
                request_count=health_status.request_count,
                last_checked=datetime.utcnow()
            ))

        return statuses

    except Exception as e:
        logger.error(f"Error fetching service status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain/{incident_id}")
async def generate_explanation(incident_id: str):
    """Generate human-readable explanation for an incident"""
    try:
        incident = await firestore_client.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        explanation = await gemini_reasoner.generate_explanation(incident)

        # Update incident with explanation
        await firestore_client.update_incident(
            incident_id=incident_id,
            updates={"explanation": explanation}
        )

        return {
            "incident_id": incident_id,
            "explanation": explanation,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating explanation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_target_services() -> List[Dict]:
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

    return []


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
