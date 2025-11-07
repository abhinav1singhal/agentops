"""
Demo App A - FastAPI Test Service with Fault Injection
Used to demonstrate AgentOps auto-remediation capabilities
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fault injection state
class FaultType(str, Enum):
    NONE = "none"
    ERROR_5XX = "5xx"
    LATENCY = "latency"
    TIMEOUT = "timeout"

class FaultConfig:
    def __init__(self):
        self.enabled = False
        self.fault_type = FaultType.NONE
        self.error_rate = 0.0  # 0-100 percentage
        self.latency_ms = 0  # milliseconds
        self.expires_at: Optional[datetime] = None
    
    def is_active(self) -> bool:
        """Check if fault injection is currently active"""
        if not self.enabled:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            # Fault expired, disable it
            self.enabled = False
            self.fault_type = FaultType.NONE
            logger.info("Fault injection expired and disabled")
            return False
        
        return True
    
    def should_inject(self) -> bool:
        """Determine if this request should have fault injected"""
        if not self.is_active():
            return False
        
        # Random chance based on error_rate
        return random.random() * 100 < self.error_rate

# Global fault configuration
fault_config = FaultConfig()

# Initialize FastAPI app
app = FastAPI(
    title="Demo App A",
    description="Test service with fault injection for AgentOps demo",
    version="1.0.0"
)

# Request counter for metrics
request_count = 0
error_count = 0


@app.middleware("http")
async def fault_injection_middleware(request: Request, call_next):
    """Middleware to inject faults into requests"""
    global request_count, error_count
    
    # Skip fault injection for health and fault management endpoints
    if request.url.path in ["/health", "/fault/status", "/fault/enable", "/fault/disable"]:
        return await call_next(request)
    
    request_count += 1
    
    # Check if we should inject a fault
    if fault_config.should_inject():
        
        if fault_config.fault_type == FaultType.ERROR_5XX:
            error_count += 1
            error_code = random.choice([500, 502, 503])
            logger.warning(f"💥 Injecting {error_code} error (fault injection active)")
            return JSONResponse(
                status_code=error_code,
                content={
                    "error": "Simulated error",
                    "message": f"This is a simulated {error_code} error for testing",
                    "fault_injection": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        elif fault_config.fault_type == FaultType.LATENCY:
            # Add artificial latency
            latency_ms = fault_config.latency_ms
            logger.warning(f"⏱️  Injecting {latency_ms}ms latency")
            time.sleep(latency_ms / 1000.0)
        
        elif fault_config.fault_type == FaultType.TIMEOUT:
            # Simulate timeout by sleeping longer than typical timeout
            logger.warning("⏱️  Injecting timeout (30s delay)")
            time.sleep(30)
    
    # Normal request processing
    response = await call_next(request)
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Demo App A",
        "version": "1.0.0",
        "status": "healthy" if not fault_config.is_active() else "fault_injection_active",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Hello from Demo App A! Use /fault endpoints to inject failures."
    }


@app.get("/health")
async def health_check():
    """Health check endpoint (never has faults injected)"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "running",
        "fault_injection": fault_config.is_active()
    }


@app.get("/api/data")
async def get_data():
    """Sample API endpoint that returns data"""
    return {
        "data": [
            {"id": 1, "name": "Item 1", "value": random.randint(1, 100)},
            {"id": 2, "name": "Item 2", "value": random.randint(1, 100)},
            {"id": 3, "name": "Item 3", "value": random.randint(1, 100)}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/random")
async def get_random():
    """Random number generator endpoint"""
    return {
        "random": random.random(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/process")
async def process_data(data: dict):
    """Process some data (simulates work)"""
    time.sleep(random.uniform(0.01, 0.05))  # Simulate processing
    return {
        "processed": True,
        "input": data,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def get_metrics():
    """Simple metrics endpoint"""
    success_count = request_count - error_count
    error_rate = (error_count / request_count * 100) if request_count > 0 else 0.0
    
    return {
        "total_requests": request_count,
        "success_count": success_count,
        "error_count": error_count,
        "error_rate_pct": round(error_rate, 2),
        "fault_injection_active": fault_config.is_active(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/fault/status")
async def fault_status():
    """Get current fault injection status"""
    return {
        "enabled": fault_config.enabled,
        "active": fault_config.is_active(),
        "fault_type": fault_config.fault_type,
        "error_rate": fault_config.error_rate,
        "latency_ms": fault_config.latency_ms,
        "expires_at": fault_config.expires_at.isoformat() if fault_config.expires_at else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/fault/enable")
async def enable_fault(
    type: FaultType = FaultType.ERROR_5XX,
    error_rate: float = 15.0,
    latency_ms: int = 1000,
    duration: int = 300  # seconds
):
    """
    Enable fault injection
    
    Args:
        type: Type of fault (5xx, latency, timeout)
        error_rate: Percentage of requests to affect (0-100)
        latency_ms: Latency to add in milliseconds
        duration: How long to keep fault active (seconds)
    """
    # Validate inputs
    if error_rate < 0 or error_rate > 100:
        raise HTTPException(status_code=400, detail="error_rate must be between 0 and 100")
    
    if latency_ms < 0:
        raise HTTPException(status_code=400, detail="latency_ms must be positive")
    
    if duration < 0:
        raise HTTPException(status_code=400, detail="duration must be positive")
    
    # Enable fault injection
    fault_config.enabled = True
    fault_config.fault_type = type
    fault_config.error_rate = error_rate
    fault_config.latency_ms = latency_ms
    fault_config.expires_at = datetime.utcnow() + timedelta(seconds=duration)
    
    logger.warning(
        f"🔴 FAULT INJECTION ENABLED: type={type}, error_rate={error_rate}%, "
        f"latency={latency_ms}ms, duration={duration}s"
    )
    
    return {
        "message": "Fault injection enabled",
        "config": {
            "type": type,
            "error_rate": error_rate,
            "latency_ms": latency_ms,
            "duration": duration,
            "expires_at": fault_config.expires_at.isoformat()
        },
        "warning": "This service will now start failing. AgentOps should detect and remediate.",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/fault/disable")
async def disable_fault():
    """Disable fault injection"""
    fault_config.enabled = False
    fault_config.fault_type = FaultType.NONE
    fault_config.error_rate = 0.0
    fault_config.expires_at = None
    
    logger.info("✅ FAULT INJECTION DISABLED")
    
    return {
        "message": "Fault injection disabled",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/stress")
async def stress_test(count: int = 100):
    """
    Generate load for testing
    Makes multiple internal requests
    """
    results = {
        "success": 0,
        "errors": 0
    }
    
    for _ in range(min(count, 1000)):  # Cap at 1000 to prevent abuse
        try:
            # Simulate internal processing
            time.sleep(0.001)
            results["success"] += 1
        except Exception:
            results["errors"] += 1
    
    return {
        "message": f"Stress test completed with {count} iterations",
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)