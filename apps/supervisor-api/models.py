"""
Data models for Supervisor API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ServiceHealthStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    """Types of remediation actions"""
    ROLLBACK = "ROLLBACK"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    REDEPLOY = "REDEPLOY"
    NONE = "NONE"


class IncidentStatus(str, Enum):
    """Incident status"""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    ACTION_PENDING = "action_pending"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"
    FAILED = "failed"


class HealthMetrics(BaseModel):
    """Health metrics for a service"""
    error_rate: float = Field(..., description="Error rate percentage (0-100)")
    latency_p50: Optional[float] = Field(None, description="50th percentile latency in ms")
    latency_p95: Optional[float] = Field(None, description="95th percentile latency in ms")
    latency_p99: Optional[float] = Field(None, description="99th percentile latency in ms")
    request_count: int = Field(..., description="Total request count in window")
    success_count: int = Field(..., description="Successful requests")
    error_count: int = Field(..., description="Failed requests")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LogSample(BaseModel):
    """Sample log entry"""
    timestamp: datetime
    severity: str
    message: str
    resource: Optional[Dict[str, Any]] = None


class ServiceHealth(BaseModel):
    """Complete health assessment of a service"""
    service_name: str
    region: str
    status: ServiceHealthStatus
    metrics: HealthMetrics
    log_samples: List[LogSample] = []
    has_anomaly: bool = False
    anomaly_summary: Optional[str] = None
    error_rate: float
    latency_p95: Optional[float]
    request_count: int
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class AIRecommendation(BaseModel):
    """AI-generated recommendation"""
    action: ActionType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str
    risk_assessment: str
    expected_impact: str
    target_revision: Optional[str] = None
    scale_params: Optional[Dict[str, int]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionRequest(BaseModel):
    """Action request sent to fixer agent via Pub/Sub"""
    incident_id: str
    service_name: str
    region: str
    action_type: ActionType
    target_revision: Optional[str] = None
    scale_params: Optional[Dict[str, int]] = None
    reason: str
    confidence: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActionResult(BaseModel):
    """Result of an action execution"""
    action_id: str
    incident_id: str
    action_type: ActionType
    status: str  # success, failed, partial
    executed_at: datetime
    result_details: Dict[str, Any]
    error_message: Optional[str] = None


class Incident(BaseModel):
    """Incident record"""
    id: str
    service_name: str
    region: str
    status: IncidentStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    metrics_snapshot: HealthMetrics
    log_samples: List[LogSample] = []
    anomaly_description: str
    recommendation: Optional[AIRecommendation] = None
    action_taken: Optional[ActionResult] = None
    explanation: Optional[str] = None
    mttr_seconds: Optional[int] = None


class HealthScanResponse(BaseModel):
    """Response from health scan endpoint"""
    scan_id: str
    timestamp: datetime
    services_scanned: int
    anomalies_detected: int
    actions_recommended: int
    details: List[Dict[str, Any]]


class IncidentResponse(BaseModel):
    """Response for incident queries"""
    id: str
    service_name: str
    status: IncidentStatus
    started_at: datetime
    ended_at: Optional[datetime]
    error_rate: float
    latency_p95: Optional[float]
    recommendation: Optional[str]
    action_taken: Optional[str]
    mttr_seconds: Optional[int]


class ServiceStatus(BaseModel):
    """Current status of a service"""
    name: str
    region: str
    status: ServiceHealthStatus
    error_rate: float
    latency_p95: Optional[float]
    request_count: int
    last_checked: datetime


class ServiceConfig(BaseModel):
    """Configuration for a monitored service"""
    name: str
    region: str
    error_threshold: float = 5.0  # percentage
    latency_p95_threshold_ms: float = 600.0
    latency_p99_threshold_ms: float = 1000.0
    min_request_count: int = 100
    confirmation_windows: int = 2
    rollback_enabled: bool = True
    auto_scale_enabled: bool = True
    min_instances_range: tuple = (0, 5)
    max_instances_range: tuple = (10, 100)