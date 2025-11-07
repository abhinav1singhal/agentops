"""
Pub/Sub Publisher - Sends action requests to fixer agent
"""

import logging
import json
import os
from google.cloud import pubsub_v1
from google.api_core import retry
import asyncio

from models import ActionRequest

logger = logging.getLogger(__name__)


class PubSubPublisher:
    """Publishes action requests to Pub/Sub for fixer agent"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_name = os.getenv("PUBSUB_TOPIC", "agent-actions")
        self.topic_path = self.publisher.topic_path(project_id, self.topic_name)
        
        logger.info(f"PubSubPublisher initialized for topic: {self.topic_path}")
    
    async def publish_action(self, action_request: ActionRequest) -> str:
        """
        Publish an action request to Pub/Sub
        
        Args:
            action_request: The action to be executed by fixer agent
            
        Returns:
            Message ID from Pub/Sub
        """
        try:
            # Convert to JSON
            message_data = action_request.model_dump_json()
            
            logger.info(
                f"Publishing action to Pub/Sub: {action_request.action_type} "
                f"for {action_request.service_name}"
            )
            
            # Publish message
            loop = asyncio.get_event_loop()
            future = await loop.run_in_executor(
                None,
                lambda: self.publisher.publish(
                    self.topic_path,
                    message_data.encode("utf-8"),
                    incident_id=action_request.incident_id,
                    service_name=action_request.service_name,
                    action_type=action_request.action_type.value
                )
            )
            
            # Wait for result
            message_id = await loop.run_in_executor(None, future.result)
            
            logger.info(f"Action published successfully. Message ID: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error publishing to Pub/Sub: {str(e)}", exc_info=True)
            raise