"""
Data models for Fixer Agent
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """Types of remediation actions"""
    ROLLBACK = "ROLLBACK"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    REDEPLOY = "REDEPLOY"
    NONE = "NONE"


class ActionStatus(str, Enum):
    """Status of action execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ActionRequest(BaseModel):
    """Action request from supervisor (via Pub/Sub)"""
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
    status: ActionStatus
    executed_at: datetime
    result_details: Dict[str, Any]
    error_message: Optional[str] = None


class TrafficTarget(BaseModel):
    """Traffic target for a revision"""
    revision_name: str
    percent: int
    is_latest: bool = False


class ServiceInfo(BaseModel):
    """Cloud Run service information"""
    name: str
    region: str
    current_revision: str
    traffic_split: Dict[str, int]
    min_instances: int
    max_instances: int
    available_revisions: list[str]