"""
Firestore Updater - Updates incident records after action execution
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreUpdater:
    """Updates incidents in Firestore as actions execute"""

    def __init__(self, project_id: str):
        """
        Initialize Firestore client

        Args:
            project_id: GCP project ID
        """
        self.db = firestore.Client(project=project_id)
        self.incidents_collection = os.getenv("INCIDENTS_COLLECTION", "incidents")
        self.actions_collection = os.getenv("ACTIONS_COLLECTION", "actions")

        logger.info(f"FirestoreUpdater initialized for project: {project_id}")
        logger.info(f"Incidents collection: {self.incidents_collection}")
        logger.info(f"Actions collection: {self.actions_collection}")

    async def update_incident_status(
        self,
        incident_id: str,
        status: str,
        action_result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update incident status as action progresses

        Status transitions:
        - action_pending → remediating (when action starts)
        - remediating → resolved (when action succeeds)
        - remediating → failed (when action fails)

        Args:
            incident_id: Incident identifier
            status: New status (remediating, resolved, failed)
            action_result: Result details from action execution
            error_message: Error message if action failed
        """

        try:
            incident_ref = self.db.collection(self.incidents_collection).document(incident_id)

            # Check if incident exists
            doc = incident_ref.get()
            if not doc.exists:
                logger.warning(f"Incident {incident_id} not found in Firestore")
                # Create minimal incident record
                incident_ref.set({
                    "id": incident_id,
                    "status": status,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                return

            # Build update data
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }

            if status == "remediating":
                # Action execution started
                update_data["remediation_started_at"] = datetime.utcnow()
                logger.info(f"📝 Incident {incident_id}: action_pending → remediating")

            elif status == "resolved":
                # Action succeeded
                update_data["resolved_at"] = datetime.utcnow()

                if action_result:
                    update_data["action_result"] = action_result

                # Calculate MTTR (Mean Time To Recovery)
                incident_data = doc.to_dict()
                detected_at = incident_data.get("detected_at")

                if detected_at:
                    # Handle both datetime objects and timestamps
                    if isinstance(detected_at, datetime):
                        detection_time = detected_at
                    else:
                        detection_time = detected_at  # Assume it's a Firestore timestamp

                    mttr_seconds = (datetime.utcnow() - detection_time).total_seconds()
                    update_data["mttr_seconds"] = mttr_seconds

                    logger.info(
                        f"✅ Incident {incident_id}: remediating → resolved "
                        f"(MTTR: {mttr_seconds:.1f}s)"
                    )
                else:
                    logger.info(f"✅ Incident {incident_id}: remediating → resolved")

            elif status == "failed":
                # Action failed
                update_data["resolved_at"] = datetime.utcnow()

                if error_message:
                    update_data["error_message"] = error_message

                logger.error(f"❌ Incident {incident_id}: remediating → failed: {error_message}")

            # Update incident in Firestore
            incident_ref.update(update_data)

            logger.debug(f"Updated incident {incident_id} with status: {status}")

        except Exception as e:
            logger.error(
                f"Failed to update incident {incident_id} status to {status}: {e}",
                exc_info=True
            )
            # Don't raise - Firestore update failure shouldn't break action execution
            # The action may have succeeded even if we can't record it

    async def record_action_result(
        self,
        incident_id: str,
        action_type: str,
        result: Dict[str, Any]
    ) -> None:
        """
        Record action execution details in actions collection

        This creates an audit trail of all actions taken by the fixer agent.

        Args:
            incident_id: Related incident identifier
            action_type: Type of action (ROLLBACK, SCALE_UP, etc.)
            result: Execution result details
        """

        try:
            action_doc = {
                "incident_id": incident_id,
                "action_type": action_type,
                "executed_at": datetime.utcnow(),
                "result": result,
                "success": result.get("success", False)
            }

            # Add optional fields if present
            if "service" in result:
                action_doc["service_name"] = result["service"]

            if "old_traffic" in result:
                action_doc["old_traffic"] = result["old_traffic"]

            if "new_traffic" in result:
                action_doc["new_traffic"] = result["new_traffic"]

            if "old_min" in result:
                action_doc["scaling_before"] = {
                    "min": result.get("old_min"),
                    "max": result.get("old_max")
                }

            if "new_min" in result:
                action_doc["scaling_after"] = {
                    "min": result.get("new_min"),
                    "max": result.get("new_max")
                }

            # Store in actions collection
            doc_ref = self.db.collection(self.actions_collection).add(action_doc)

            logger.info(
                f"📊 Recorded {action_type} action result for incident {incident_id} "
                f"(action_id: {doc_ref[1].id})"
            )

        except Exception as e:
            logger.error(
                f"Failed to record action result for incident {incident_id}: {e}",
                exc_info=True
            )
            # Don't raise - audit logging failure shouldn't break execution

    async def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve incident details from Firestore

        Args:
            incident_id: Incident identifier

        Returns:
            Incident data dict or None if not found
        """

        try:
            incident_ref = self.db.collection(self.incidents_collection).document(incident_id)
            doc = incident_ref.get()

            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"Incident {incident_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error retrieving incident {incident_id}: {e}")
            return None
