"""
Fixer Agent - Simplified Version
Receives action requests and logs them (can be enhanced later)
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import os
import json
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgentOps Fixer Agent",
    description="Executes automated remediation actions",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgentOps Fixer Agent",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/actions/execute")
async def execute_action(request: Request):
    """
    Execute action from Pub/Sub push subscription
    Simplified version that logs actions
    """
    try:
        # Parse Pub/Sub message
        envelope = await request.json()
        
        if "message" not in envelope:
            logger.warning("Received request without 'message' field")
            return JSONResponse({"status": "ignored"}, status_code=200)
        
        message = envelope["message"]
        message_id = message.get("messageId", "unknown")
        
        logger.info(f"Received Pub/Sub message: {message_id}")
        
        # Decode message data
        message_data = base64.b64decode(message["data"]).decode("utf-8")
        action_data = json.loads(message_data)
        
        logger.info(f"Action received: {json.dumps(action_data, indent=2)}")
        
        # Extract action details
        action_type = action_data.get("action_type", "UNKNOWN")
        service_name = action_data.get("service_name", "unknown")
        incident_id = action_data.get("incident_id", "unknown")
        
        logger.info(
            f"📋 Action: {action_type} for {service_name} (incident: {incident_id})"
        )
        
        # Simulate action execution
        logger.info(f"✅ Action {action_type} would be executed here")
        logger.info("   (Simplified version - manual execution required)")
        
        # Return success
        return JSONResponse({
            "status": "processed",
            "action_type": action_type,
            "service_name": service_name,
            "incident_id": incident_id,
            "message": "Action logged (manual execution required)",
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=200)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {str(e)}")
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)
    
    except Exception as e:
        logger.error(f"Error processing action: {str(e)}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=200)

@app.post("/actions/execute/manual")
async def execute_action_manual(action_request: dict):
    """
    Manually execute an action (for testing)
    """
    try:
        logger.info(f"Manual action requested: {json.dumps(action_request, indent=2)}")
        
        action_type = action_request.get("action_type", "UNKNOWN")
        service_name = action_request.get("service_name", "unknown")
        
        logger.info(f"📋 Manual action: {action_type} for {service_name}")
        
        return {
            "status": "success",
            "message": f"Action {action_type} logged for {service_name}",
            "note": "Simplified version - manual execution required",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in manual execution: {str(e)}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/actions/history")
async def get_action_history(limit: int = 50):
    """Get recent action execution history (mock)"""
    return {
        "actions": [],
        "total": 0,
        "limit": limit,
        "message": "Action history not yet implemented"
    }

@app.post("/services/{service_name}/rollback")
async def manual_rollback(service_name: str, target_revision: str = None):
    """
    Manually trigger a rollback for a service
    """
    logger.info(f"Manual rollback requested for {service_name}")
    logger.info(f"Target revision: {target_revision or 'auto'}")
    
    return {
        "service": service_name,
        "action": "rollback",
        "target_revision": target_revision,
        "status": "logged",
        "message": "Manual rollback via Cloud Console required",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8081))
    logger.info(f"Starting Fixer Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)