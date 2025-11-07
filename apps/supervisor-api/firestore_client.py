"""
Firestore Client - Stores and retrieves incidents
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from google.cloud import firestore
import asyncio

from models import (
    Incident,
    IncidentStatus,
    ServiceHealth,
    AIRecommendation,
    ActionResult,
    IncidentResponse
)

logger = logging.getLogger(__name__)


class FirestoreClient:
    """Manages incident data in Firestore"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.db = firestore.Client(project=project_id)
        self.incidents_collection = os.getenv("INCIDENTS_COLLECTION", "incidents")
        self.actions_collection = os.getenv("ACTIONS_COLLECTION", "actions")
        
        logger.info(f"FirestoreClient initialized for project: {project_id}")
    
    async def create_incident(
        self,
        service_name: str,
        health_status: ServiceHealth,
        recommendation: AIRecommendation
    ) -> Incident:
        """Create a new incident record"""
        
        incident_id = f"inc_{service_name}_{int(datetime.utcnow().timestamp())}"
        
        incident = Incident(
            id=incident_id,
            service_name=service_name,
            region=health_status.region,
            status=IncidentStatus.DETECTED,
            started_at=datetime.utcnow(),
            metrics_snapshot=health_status.metrics,
            log_samples=health_status.log_samples,
            anomaly_description=health_status.anomaly_summary or "Unknown anomaly",
            recommendation=recommendation
        )
        
        try:
            # Store in Firestore
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.db.collection(self.incidents_collection).document(incident_id).set(
                    incident.model_dump(mode='json')
                )
            )
            
            logger.info(f"Created incident: {incident_id}")
            return incident
            
        except Exception as e:
            logger.error(f"Error creating incident: {str(e)}", exc_info=True)
            raise
    
    async def update_incident(
        self,
        incident_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """Update an existing incident"""
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.db.collection(self.incidents_collection).document(incident_id).update(
                    updates
                )
            )
            
            logger.info(f"Updated incident {incident_id}: {list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"Error updating incident: {str(e)}", exc_info=True)
            raise
    
    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get a specific incident by ID"""
        
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(
                None,
                lambda: self.db.collection(self.incidents_collection).document(incident_id).get()
            )
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            return Incident(**data)
            
        except Exception as e:
            logger.error(f"Error fetching incident: {str(e)}", exc_info=True)
            return None
    
    async def get_incidents(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[IncidentResponse]:
        """Get list of incidents with optional filtering"""
        
        try:
            loop = asyncio.get_event_loop()
            
            # Build query
            query = self.db.collection(self.incidents_collection).order_by(
                'started_at', direction=firestore.Query.DESCENDING
            ).limit(limit)
            
            if status:
                query = query.where('status', '==', status)
            
            # Execute query
            docs = await loop.run_in_executor(
                None,
                lambda: list(query.stream())
            )
            
            # Convert to response objects
            incidents = []
            for doc in docs:
                data = doc.to_dict()
                
                # Calculate MTTR if resolved
                mttr_seconds = None
                if data.get('ended_at') and data.get('started_at'):
                    mttr_seconds = int(
                        (data['ended_at'] - data['started_at']).total_seconds()
                    )
                
                incidents.append(IncidentResponse(
                    id=data['id'],
                    service_name=data['service_name'],
                    status=data['status'],
                    started_at=data['started_at'],
                    ended_at=data.get('ended_at'),
                    error_rate=data['metrics_snapshot']['error_rate'],
                    latency_p95=data['metrics_snapshot'].get('latency_p95'),
                    recommendation=data.get('recommendation', {}).get('action') if data.get('recommendation') else None,
                    action_taken=data.get('action_taken', {}).get('action_type') if data.get('action_taken') else None,
                    mttr_seconds=mttr_seconds
                ))
            
            logger.info(f"Retrieved {len(incidents)} incidents")
            return incidents
            
        except Exception as e:
            logger.error(f"Error fetching incidents: {str(e)}", exc_info=True)
            return []
    
    async def record_action_result(
        self,
        incident_id: str,
        action_result: ActionResult
    ) -> None:
        """Record the result of an action execution"""
        
        try:
            # Update incident with action result
            updates = {
                'action_taken': action_result.model_dump(mode='json'),
                'status': IncidentStatus.RESOLVED if action_result.status == 'success' else IncidentStatus.FAILED
            }
            
            # If resolved, set end time and calculate MTTR
            if action_result.status == 'success':
                incident = await self.get_incident(incident_id)
                if incident:
                    updates['ended_at'] = datetime.utcnow()
                    mttr = int((datetime.utcnow() - incident.started_at).total_seconds())
                    updates['mttr_seconds'] = mttr
            
            await self.update_incident(incident_id, updates)
            
            # Also store action separately for audit trail
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.db.collection(self.actions_collection).document(action_result.action_id).set(
                    action_result.model_dump(mode='json')
                )
            )
            
            logger.info(f"Recorded action result for incident {incident_id}")
            
        except Exception as e:
            logger.error(f"Error recording action result: {str(e)}", exc_info=True)
            raise