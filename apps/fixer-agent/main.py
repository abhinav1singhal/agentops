"""
Fixer Agent - Main Application
Executes automated remediation actions on Cloud Run services
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any

from cloud_run_manager import CloudRunManager
from firestore_updater import FirestoreUpdater
from models import ActionType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
cloud_run_manager: Optional[CloudRunManager] = None
firestore_updater: Optional[FirestoreUpdater] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    global cloud_run_manager, firestore_updater

    logger.info("Starting Fixer Agent...")

    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")

    if not project_id:
        raise ValueError("PROJECT_ID environment variable is required")

    # Initialize components
    cloud_run_manager = CloudRunManager(project_id, region)
    firestore_updater = FirestoreUpdater(project_id)

    logger.info(f"Fixer Agent started for project: {project_id}, region: {region}")

    yield

    # Shutdown
    logger.info("Shutting down Fixer Agent...")


# Initialize FastAPI app
app = FastAPI(
    title="AgentOps Fixer Agent",
    description="AI-powered remediation executor for Cloud Run services",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgentOps Fixer Agent",
        "status": "healthy",
        "version": "2.0.0 Modular",
        "features": {
            "cloud_run_manager": cloud_run_manager is not None,
            "firestore_updater": firestore_updater is not None,
            "dry_run_mode": cloud_run_manager.dry_run if cloud_run_manager else False
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "cloud_run_manager": cloud_run_manager is not None,
            "firestore_updater": firestore_updater is not None
        }
    }


@app.post("/actions/execute")
async def execute_action(request: Request):
    """
    Execute action from Pub/Sub push subscription

    This endpoint receives action requests from the Supervisor API via Pub/Sub
    and executes the appropriate remediation action.
    """
    try:
        envelope = await request.json()

        if "message" not in envelope:
            logger.warning("Received request without 'message' field")
            return JSONResponse({"status": "ignored"}, status_code=200)

        message = envelope["message"]
        message_id = message.get("messageId", "unknown")

        logger.info(f"📨 Received Pub/Sub message: {message_id}")

        # Decode and parse action request
        message_data = base64.b64decode(message["data"]).decode("utf-8")
        action_data = json.loads(message_data)

        # Extract action details
        action_type = action_data.get("action_type", "UNKNOWN")
        service_name = action_data.get("service_name", "unknown")
        region = action_data.get("region", os.getenv("REGION", "us-central1"))
        incident_id = action_data.get("incident_id", "unknown")

        logger.info(f"📋 Action: {action_type} for {service_name} in {region}")

        # Update incident status: action_pending → remediating
        await firestore_updater.update_incident_status(
            incident_id=incident_id,
            status="remediating"
        )

        # Execute action using CloudRunManager
        result = await execute_cloud_run_action(
            action_type=action_type,
            service_name=service_name,
            region=region,
            action_data=action_data
        )

        # Check if action succeeded
        if result.get("success", False):
            # Update incident: remediating → resolved
            await firestore_updater.update_incident_status(
                incident_id=incident_id,
                status="resolved",
                action_result=result
            )

            # Record action result for audit trail
            await firestore_updater.record_action_result(
                incident_id=incident_id,
                action_type=action_type,
                result=result
            )

            logger.info(f"✅ Action {action_type} completed successfully")
        else:
            # Action failed
            error_msg = result.get("message", "Unknown error")
            await firestore_updater.update_incident_status(
                incident_id=incident_id,
                status="failed",
                error_message=error_msg
            )

            logger.error(f"❌ Action {action_type} failed: {error_msg}")

        return JSONResponse({
            "status": "processed",
            "action_type": action_type,
            "service_name": service_name,
            "incident_id": incident_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=200)

    except Exception as e:
        logger.error(f"❌ Error processing action: {str(e)}", exc_info=True)

        # Try to update incident as failed
        if 'incident_id' in locals():
            try:
                await firestore_updater.update_incident_status(
                    incident_id=incident_id,
                    status="failed",
                    error_message=str(e)
                )
            except:
                pass  # Best effort

        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=200)  # Return 200 to acknowledge Pub/Sub message


@app.post("/actions/execute/manual")
async def execute_action_manual(action_request: dict):
    """
    Manually execute an action (for testing)

    Example request:
    {
        "action_type": "ROLLBACK",
        "service_name": "demo-app-a",
        "region": "us-central1",
        "target_revision": "demo-app-a-00005-abc",
        "incident_id": "test_123"
    }
    """
    try:
        action_type = action_request.get("action_type", "UNKNOWN")
        service_name = action_request.get("service_name")
        region = action_request.get("region", os.getenv("REGION", "us-central1"))
        incident_id = action_request.get("incident_id", f"manual_{int(datetime.utcnow().timestamp())}")

        if not service_name:
            raise HTTPException(status_code=400, detail="service_name is required")

        logger.info(f"🔧 Manual action: {action_type} for {service_name}")

        # Update incident if provided
        if incident_id:
            await firestore_updater.update_incident_status(
                incident_id=incident_id,
                status="remediating"
            )

        # Execute action
        result = await execute_cloud_run_action(
            action_type=action_type,
            service_name=service_name,
            region=region,
            action_data=action_request
        )

        # Update incident status
        if incident_id and result.get("success", False):
            await firestore_updater.update_incident_status(
                incident_id=incident_id,
                status="resolved",
                action_result=result
            )
            await firestore_updater.record_action_result(
                incident_id=incident_id,
                action_type=action_type,
                result=result
            )
        elif incident_id:
            await firestore_updater.update_incident_status(
                incident_id=incident_id,
                status="failed",
                error_message=result.get("message", "Action failed")
            )

        return {
            "status": "success" if result.get("success") else "failed",
            "action_type": action_type,
            "service_name": service_name,
            "incident_id": incident_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual execution: {str(e)}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def execute_cloud_run_action(
    action_type: str,
    service_name: str,
    region: str,
    action_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute Cloud Run action using CloudRunManager

    Args:
        action_type: Type of action (ROLLBACK, SCALE_UP, SCALE_DOWN, etc.)
        service_name: Target Cloud Run service
        region: GCP region
        action_data: Additional action parameters

    Returns:
        Result dictionary with success status and details
    """

    if not cloud_run_manager:
        return {
            "success": False,
            "message": "Cloud Run manager not initialized"
        }

    try:
        if action_type == "ROLLBACK":
            # Execute traffic rollback
            target_revision = action_data.get("target_revision")

            if not target_revision:
                return {
                    "success": False,
                    "message": "target_revision is required for ROLLBACK"
                }

            result = await cloud_run_manager.rollback_traffic(
                service_name=service_name,
                region=region,
                target_revision=target_revision,
                percentage=100
            )

            return result

        elif action_type == "SCALE_UP":
            # Execute scale up
            scale_params = action_data.get("scale_params", {})
            min_instances = scale_params.get("min_instances")
            max_instances = scale_params.get("max_instances")

            result = await cloud_run_manager.update_scaling(
                service_name=service_name,
                region=region,
                min_instances=min_instances,
                max_instances=max_instances
            )

            return result

        elif action_type == "SCALE_DOWN":
            # Execute scale down
            scale_params = action_data.get("scale_params", {})
            min_instances = scale_params.get("min_instances")
            max_instances = scale_params.get("max_instances")

            result = await cloud_run_manager.update_scaling(
                service_name=service_name,
                region=region,
                min_instances=min_instances,
                max_instances=max_instances
            )

            return result

        elif action_type == "NONE":
            logger.info("Action type is NONE - no action taken")
            return {
                "success": True,
                "message": "No action required"
            }

        else:
            return {
                "success": False,
                "message": f"Unknown action type: {action_type}"
            }

    except Exception as e:
        logger.error(f"Action execution failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8081))
    logger.info(f"Starting Fixer Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
