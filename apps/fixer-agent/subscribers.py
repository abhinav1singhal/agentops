"""
Pub/Sub Subscriber - Processes action requests from supervisor
"""

import logging
import os
import asyncio
from typing import Optional
from datetime import datetime
from google.cloud import pubsub_v1, firestore
from concurrent.futures import TimeoutError

from models import ActionRequest, ActionResult, ActionStatus, ActionType
from cloud_run_manager import CloudRunManager

logger = logging.getLogger(__name__)


class PubSubSubscriber:
    """Subscribes to action requests and executes them"""
    
    def __init__(self, project_id: str, cloud_run_manager: CloudRunManager):
        self.project_id = project_id
        self.cloud_run_manager = cloud_run_manager
        
        # Firestore for reporting results
        self.firestore_client = firestore.Client(project=project_id)
        self.incidents_collection = os.getenv("INCIDENTS_COLLECTION", "incidents")
        self.actions_collection = os.getenv("ACTIONS_COLLECTION", "actions")
        
        # Pub/Sub subscriber (for pull subscription - optional)
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_name = os.getenv("PUBSUB_SUBSCRIPTION", "agent-actions-sub")
        self.subscription_path = self.subscriber.subscription_path(
            project_id, 
            self.subscription_name
        )
        
        self.streaming_pull_future: Optional[pubsub_v1.subscriber.futures.StreamingPullFuture] = None
        
        logger.info(f"PubSubSubscriber initialized for subscription: {self.subscription_path}")
    
    async def process_action(self, action_request: ActionRequest) -> ActionResult:
        """
        Process a single action request
        
        Args:
            action_request: The action to execute
            
        Returns:
            ActionResult with execution details
        """
        action_id = f"action_{action_request.incident_id}_{int(datetime.utcnow().timestamp())}"
        
        logger.info(
            f"Processing action {action_id}: {action_request.action_type} "
            f"for {action_request.service_name}"
        )
        
        # Initialize result
        result = ActionResult(
            action_id=action_id,
            incident_id=action_request.incident_id,
            action_type=action_request.action_type,
            status=ActionStatus.IN_PROGRESS,
            executed_at=datetime.utcnow(),
            result_details={}
        )
        
        try:
            # Execute action based on type
            if action_request.action_type == ActionType.ROLLBACK:
                details = await self._execute_rollback(action_request)
                result.status = ActionStatus.SUCCESS
                result.result_details = details
                
            elif action_request.action_type == ActionType.SCALE_UP:
                details = await self._execute_scale_up(action_request)
                result.status = ActionStatus.SUCCESS
                result.result_details = details
                
            elif action_request.action_type == ActionType.SCALE_DOWN:
                details = await self._execute_scale_down(action_request)
                result.status = ActionStatus.SUCCESS
                result.result_details = details
                
            elif action_request.action_type == ActionType.REDEPLOY:
                details = await self._execute_redeploy(action_request)
                result.status = ActionStatus.SUCCESS
                result.result_details = details
                
            elif action_request.action_type == ActionType.NONE:
                logger.info("Action type is NONE - no action taken")
                result.status = ActionStatus.SUCCESS
                result.result_details = {"message": "No action required"}
                
            else:
                raise ValueError(f"Unknown action type: {action_request.action_type}")
            
            logger.info(f"✅ Action {action_id} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Action {action_id} failed: {str(e)}", exc_info=True)
            result.status = ActionStatus.FAILED
            result.error_message = str(e)
            result.result_details = {"error": str(e)}
        
        # Report result back to Firestore
        await self._report_result(result)
        
        return result
    
    async def _execute_rollback(self, action_request: ActionRequest) -> dict:
        """Execute traffic rollback action"""
        
        if not action_request.target_revision:
            raise ValueError("target_revision is required for ROLLBACK action")
        
        logger.info(
            f"Executing rollback: {action_request.service_name} → "
            f"{action_request.target_revision}"
        )
        
        result = await self.cloud_run_manager.rollback_traffic(
            service_name=action_request.service_name,
            region=action_request.region,
            target_revision=action_request.target_revision,
            percentage=100
        )
        
        return {
            "action": "rollback",
            "target_revision": action_request.target_revision,
            "traffic_percentage": 100,
            "old_traffic": result.get("old_traffic"),
            "new_traffic": result.get("new_traffic"),
            "reason": action_request.reason
        }
    
    async def _execute_scale_up(self, action_request: ActionRequest) -> dict:
        """Execute scale up action"""
        
        # Get current service info
        service_info = await self.cloud_run_manager.get_service_info(
            action_request.service_name,
            action_request.region
        )
        
        # Calculate new scaling (increase by 50% or at least +2)
        old_min = service_info.min_instances
        old_max = service_info.max_instances
        
        new_min = max(old_min + 2, int(old_min * 1.5))
        new_max = max(old_max + 5, int(old_max * 1.5))
        
        logger.info(
            f"Scaling up {action_request.service_name}: "
            f"min {old_min}→{new_min}, max {old_max}→{new_max}"
        )
        
        result = await self.cloud_run_manager.update_scaling(
            service_name=action_request.service_name,
            region=action_request.region,
            min_instances=new_min,
            max_instances=new_max
        )
        
        return {
            "action": "scale_up",
            "old_min_instances": old_min,
            "old_max_instances": old_max,
            "new_min_instances": new_min,
            "new_max_instances": new_max,
            "reason": action_request.reason
        }
    
    async def _execute_scale_down(self, action_request: ActionRequest) -> dict:
        """Execute scale down action"""
        
        # Get current service info
        service_info = await self.cloud_run_manager.get_service_info(
            action_request.service_name,
            action_request.region
        )
        
        # Calculate new scaling (decrease by 30% or at least -2)
        old_min = service_info.min_instances
        old_max = service_info.max_instances
        
        new_min = max(0, old_min - 2, int(old_min * 0.7))
        new_max = max(10, old_max - 5, int(old_max * 0.7))
        
        logger.info(
            f"Scaling down {action_request.service_name}: "
            f"min {old_min}→{new_min}, max {old_max}→{new_max}"
        )
        
        result = await self.cloud_run_manager.update_scaling(
            service_name=action_request.service_name,
            region=action_request.region,
            min_instances=new_min,
            max_instances=new_max
        )
        
        return {
            "action": "scale_down",
            "old_min_instances": old_min,
            "old_max_instances": old_max,
            "new_min_instances": new_min,
            "new_max_instances": new_max,
            "reason": action_request.reason
        }
    
    async def _execute_redeploy(self, action_request: ActionRequest) -> dict:
        """Execute redeploy action (trigger Cloud Build)"""
        
        logger.warning("REDEPLOY action not yet implemented")
        
        # TODO: Implement Cloud Build trigger
        # from google.cloud import cloudbuild_v1
        # trigger_id = get_trigger_for_service(action_request.service_name)
        # cloudbuild_client.run_build_trigger(...)
        
        return {
            "action": "redeploy",
            "status": "not_implemented",
            "message": "Redeploy functionality coming soon",
            "reason": action_request.reason
        }
    
    async def _report_result(self, result: ActionResult) -> None:
        """Report action result back to Firestore"""
        
        try:
            # Store action result
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.firestore_client.collection(self.actions_collection).document(
                    result.action_id
                ).set(result.model_dump(mode='json'))
            )
            
            # Update incident record
            incident_updates = {
                'action_taken': result.model_dump(mode='json'),
                'status': 'resolved' if result.status == ActionStatus.SUCCESS else 'failed'
            }
            
            # Add end time and MTTR if successful
            if result.status == ActionStatus.SUCCESS:
                incident_updates['ended_at'] = datetime.utcnow()
                
                # Get incident start time to calculate MTTR
                incident_doc = await loop.run_in_executor(
                    None,
                    lambda: self.firestore_client.collection(self.incidents_collection).document(
                        result.incident_id
                    ).get()
                )
                
                if incident_doc.exists:
                    incident_data = incident_doc.to_dict()
                    started_at = incident_data.get('started_at')
                    if started_at:
                        mttr_seconds = int((datetime.utcnow() - started_at).total_seconds())
                        incident_updates['mttr_seconds'] = mttr_seconds
            
            await loop.run_in_executor(
                None,
                lambda: self.firestore_client.collection(self.incidents_collection).document(
                    result.incident_id
                ).update(incident_updates)
            )
            
            logger.info(f"Reported result for action {result.action_id}")
            
        except Exception as e:
            logger.error(f"Error reporting result: {str(e)}", exc_info=True)
    
    async def start_listening(self):
        """Start listening to Pub/Sub subscription (pull mode)"""
        
        logger.info("Starting Pub/Sub pull subscriber...")
        
        def callback(message: pubsub_v1.subscriber.message.Message):
            """Callback for incoming messages"""
            try:
                logger.info(f"Received message: {message.message_id}")
                
                # Parse action request
                import json
                action_data = json.loads(message.data.decode('utf-8'))
                action_request = ActionRequest(**action_data)
                
                # Process action (run in event loop)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.process_action(action_request))
                loop.close()
                
                # Acknowledge message
                message.ack()
                
                logger.info(f"Message processed: {result.status}")
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                message.nack()  # Requeue for retry
        
        # Start streaming pull
        self.streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path,
            callback=callback
        )
        
        logger.info(f"Listening to {self.subscription_path}...")
    
    async def stop_listening(self):
        """Stop listening to Pub/Sub subscription"""
        
        if self.streaming_pull_future:
            logger.info("Stopping Pub/Sub subscriber...")
            self.streaming_pull_future.cancel()
            self.streaming_pull_future = None