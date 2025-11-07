"""
Supervisor API - Enhanced Version with Real Cloud Monitoring
Fetches actual metrics from Cloud Monitoring for Cloud Run services
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional
from google.cloud import monitoring_v3, logging as cloud_logging
from google.api_core import retry
import asyncio

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

# Global clients
monitoring_client = None
logging_client = None

@app.on_event("startup")
async def startup_event():
    """Startup event - initialize Cloud clients"""
    global monitoring_client, logging_client
    
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")
    
    if not project_id:
        logger.error("PROJECT_ID environment variable not set!")
        return
    
    try:
        monitoring_client = monitoring_v3.MetricServiceClient()
        logging_client = cloud_logging.Client(project=project_id)
        logger.info(f"Supervisor API started for project: {project_id}, region: {region}")
        logger.info("Cloud Monitoring and Logging clients initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Cloud clients: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgentOps Supervisor API",
        "status": "healthy",
        "version": "1.0.0",
        "monitoring_enabled": monitoring_client is not None,
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
            "health_scanner": monitoring_client is not None,
            "logging_client": logging_client is not None,
            "gemini_reasoner": False,
            "pubsub_publisher": True,
            "firestore_client": False
        }
    }

async def fetch_metric_from_monitoring(
    project_id: str,
    metric_type: str,
    service_name: str,
    region: str,
    minutes: int = 5,
    aligner: str = "ALIGN_SUM",
    reducer: Optional[str] = None,
    filter_suffix: str = ""
) -> float:
    """
    Fetch a metric value from Cloud Monitoring
    
    Args:
        project_id: GCP project ID
        metric_type: Full metric type (e.g., 'run.googleapis.com/request_count')
        service_name: Cloud Run service name
        region: GCP region
        minutes: Time window in minutes
        aligner: Alignment method
        reducer: Cross-series reducer
        filter_suffix: Additional filter conditions
    
    Returns:
        Metric value as float
    """
    if not monitoring_client:
        logger.warning("Monitoring client not initialized")
        return 0.0
    
    try:
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        # Convert to timestamp format
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": int(end_time.timestamp())},
            "start_time": {"seconds": int(start_time.timestamp())}
        })
        
        # Build filter
        metric_filter = (
            f'resource.type="cloud_run_revision" '
            f'AND resource.labels.service_name="{service_name}" '
            f'AND resource.labels.location="{region}" '
            f'AND metric.type="{metric_type}"'
        )
        
        if filter_suffix:
            metric_filter += f" AND {filter_suffix}"
        
        # Build aggregation
        aggregation = monitoring_v3.Aggregation({
            "alignment_period": {"seconds": 60},
            "per_series_aligner": getattr(
                monitoring_v3.Aggregation.Aligner, 
                aligner
            )
        })
        
        if reducer:
            aggregation.cross_series_reducer = getattr(
                monitoring_v3.Aggregation.Reducer,
                reducer
            )
            aggregation.group_by_fields = ["resource.service_name"]
        
        project_name = f"projects/{project_id}"
        
        # Execute query in thread pool (sync API)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: monitoring_client.list_time_series(
                request={
                    "name": project_name,
                    "filter": metric_filter,
                    "interval": interval,
                    "aggregation": aggregation,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                }
            )
        )
        
        # Extract value from results
        total_value = 0.0
        point_count = 0
        
        for result in results:
            if result.points:
                for point in result.points:
                    if hasattr(point.value, 'int64_value'):
                        total_value += float(point.value.int64_value)
                        point_count += 1
                    elif hasattr(point.value, 'double_value'):
                        total_value += point.value.double_value
                        point_count += 1
        
        logger.debug(f"Metric {metric_type}: {total_value} (from {point_count} points)")
        return total_value
        
    except Exception as e:
        logger.error(f"Error fetching metric {metric_type}: {str(e)}")
        return 0.0

async def fetch_error_logs(
    project_id: str,
    service_name: str,
    region: str,
    minutes: int = 5,
    max_entries: int = 10
) -> List[dict]:
    """Fetch recent error logs for a service"""
    if not logging_client:
        logger.warning("Logging client not initialized")
        return []
    
    try:
        # Build log filter
        filter_str = (
            f'resource.type="cloud_run_revision" '
            f'resource.labels.service_name="{service_name}" '
            f'resource.labels.location="{region}" '
            f'severity>=ERROR '
            f'timestamp>="{(datetime.utcnow() - timedelta(minutes=minutes)).isoformat()}Z"'
        )
        
        # Execute query in thread pool (sync API)
        loop = asyncio.get_event_loop()
        entries = await loop.run_in_executor(
            None,
            lambda: list(logging_client.list_entries(
                filter_=filter_str,
                page_size=max_entries,
                order_by=cloud_logging.DESCENDING
            ))
        )
        
        log_samples = []
        for entry in entries[:max_entries]:
            log_samples.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "severity": entry.severity,
                "message": str(entry.payload)[:500]  # Truncate long messages
            })
        
        logger.info(f"Found {len(log_samples)} error logs for {service_name}")
        return log_samples
        
    except Exception as e:
        logger.error(f"Error fetching logs for {service_name}: {str(e)}")
        return []

async def scan_service_health(service_name: str, region: str, project_id: str) -> dict:
    """
    Scan a single Cloud Run service and get real metrics
    
    Returns:
        Dictionary with service health metrics
    """
    logger.info(f"Scanning {service_name} in {region}...")
    
    # Get thresholds from environment
    error_threshold = float(os.getenv("ERROR_THRESHOLD", "5.0"))
    latency_threshold = float(os.getenv("LATENCY_P95_THRESHOLD_MS", "600"))
    min_request_count = int(os.getenv("MIN_REQUEST_COUNT", "100"))
    scan_window = int(os.getenv("SCAN_WINDOW_MINUTES", "5"))
    
    try:
        # Fetch metrics concurrently
        request_count_task = fetch_metric_from_monitoring(
            project_id,
            "run.googleapis.com/request_count",
            service_name,
            region,
            minutes=scan_window,
            aligner="ALIGN_SUM"
        )
        
        error_count_task = fetch_metric_from_monitoring(
            project_id,
            "run.googleapis.com/request_count",
            service_name,
            region,
            minutes=scan_window,
            aligner="ALIGN_SUM",
            filter_suffix='metric.label.response_code_class="5xx"'
        )
        
        latency_task = fetch_metric_from_monitoring(
            project_id,
            "run.googleapis.com/request_latencies",
            service_name,
            region,
            minutes=scan_window,
            aligner="ALIGN_DELTA",
            reducer="REDUCE_PERCENTILE_95"
        )
        
        error_logs_task = fetch_error_logs(
            project_id,
            service_name,
            region,
            minutes=scan_window
        )
        
        # Wait for all metrics
        request_count, error_count, latency_p95, error_logs = await asyncio.gather(
            request_count_task,
            error_count_task,
            latency_task,
            error_logs_task
        )
        
        # Calculate metrics
        total_requests = int(request_count)
        total_errors = int(error_count)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
        
        # Determine health status
        has_anomaly = False
        anomalies = []
        status = "healthy"
        
        # Check if we have enough data
        if total_requests >= min_request_count:
            # Check error rate
            if error_rate > error_threshold:
                has_anomaly = True
                anomalies.append(f"High error rate: {error_rate:.2f}% (threshold: {error_threshold}%)")
                status = "unhealthy"
            
            # Check latency
            if latency_p95 and latency_p95 > latency_threshold:
                has_anomaly = True
                anomalies.append(f"High latency p95: {latency_p95:.2f}ms (threshold: {latency_threshold}ms)")
                if status != "unhealthy":
                    status = "degraded"
        else:
            logger.info(f"{service_name}: Insufficient data ({total_requests} requests < {min_request_count} threshold)")
        
        anomaly_summary = "; ".join(anomalies) if anomalies else None
        
        if has_anomaly:
            logger.warning(f"{service_name} anomalies detected: {anomaly_summary}")
        
        return {
            "service": service_name,
            "region": region,
            "status": status,
            "has_anomaly": has_anomaly,
            "error_rate": round(error_rate, 2),
            "latency_p95": round(latency_p95, 2) if latency_p95 else None,
            "request_count": total_requests,
            "error_count": total_errors,
            "success_count": total_requests - total_errors,
            "anomaly_summary": anomaly_summary,
            "error_logs": error_logs[:5],  # Top 5 errors
            "recommendation": None  # AI recommendation would go here
        }
        
    except Exception as e:
        logger.error(f"Error scanning {service_name}: {str(e)}", exc_info=True)
        return {
            "service": service_name,
            "region": region,
            "status": "unknown",
            "has_anomaly": False,
            "error_rate": 0.0,
            "latency_p95": None,
            "request_count": 0,
            "error": str(e)
        }

@app.post("/health/scan")
async def scan_services():
    """
    Scan all monitored services for anomalies using real Cloud Monitoring data
    """
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")
    
    if not project_id:
        raise HTTPException(status_code=500, detail="PROJECT_ID not configured")
    
    if not monitoring_client:
        raise HTTPException(status_code=500, detail="Monitoring client not initialized")
    
    logger.info("Starting health scan with real Cloud Monitoring data...")
    
    # Get target services
    target_services = _get_target_services()
    
    # Scan all services concurrently
    scan_tasks = [
        scan_service_health(service["name"], service["region"], project_id)
        for service in target_services
    ]
    
    scan_results = await asyncio.gather(*scan_tasks)
    
    # Count anomalies
    anomalies_detected = sum(1 for result in scan_results if result.get("has_anomaly", False))
    
    response = {
        "scan_id": f"scan_{int(datetime.utcnow().timestamp())}",
        "timestamp": datetime.utcnow().isoformat(),
        "services_scanned": len(target_services),
        "anomalies_detected": anomalies_detected,
        "actions_recommended": anomalies_detected,  # Would come from AI
        "details": scan_results
    }
    
    logger.info(
        f"Scan complete: {len(target_services)} services scanned, "
        f"{anomalies_detected} anomalies detected"
    )
    
    return response

@app.get("/incidents")
async def get_incidents(limit: int = 50, status: Optional[str] = None):
    """Get recent incidents (mock data for now)"""
    return []

@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get specific incident details (mock)"""
    raise HTTPException(status_code=404, detail="Incident not found")

@app.get("/services/status")
async def get_services_status():
    """Get current status of all monitored services with real metrics"""
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION", "us-central1")
    
    if not project_id or not monitoring_client:
        # Fallback to mock data
        target_services = _get_target_services()
        return [
            {
                "name": service["name"],
                "region": service["region"],
                "status": "healthy",
                "error_rate": 0.5,
                "latency_p95": 150.0,
                "request_count": 1000,
                "last_checked": datetime.utcnow().isoformat(),
                "real_data": False
            }
            for service in target_services
        ]
    
    # Get real data
    target_services = _get_target_services()
    
    # Scan all services
    scan_tasks = [
        scan_service_health(service["name"], service["region"], project_id)
        for service in target_services
    ]
    
    scan_results = await asyncio.gather(*scan_tasks)
    
    # Format response
    statuses = []
    for result in scan_results:
        statuses.append({
            "name": result["service"],
            "region": result["region"],
            "status": result["status"],
            "error_rate": result["error_rate"],
            "latency_p95": result["latency_p95"],
            "request_count": result["request_count"],
            "last_checked": datetime.utcnow().isoformat(),
            "real_data": True
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