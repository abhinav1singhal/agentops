"""
Cloud Run Manager - Executes actions on Cloud Run services
"""

import logging
import os
import asyncio
from typing import Optional, Dict, List, Any
from google.cloud import run_v2
from google.cloud.run_v2 import Service, Revision
from google.api_core import exceptions
from datetime import datetime

from models import ServiceInfo, TrafficTarget

logger = logging.getLogger(__name__)


class CloudRunManager:
    """Manages Cloud Run service operations"""
    
    def __init__(self, project_id: str, default_region: str):
        self.project_id = project_id
        self.default_region = default_region
        self.client = run_v2.ServicesClient()
        
        # Safety limits
        self.min_instances_floor = int(os.getenv("MIN_INSTANCES_FLOOR", "0"))
        self.min_instances_ceiling = int(os.getenv("MIN_INSTANCES_CEILING", "5"))
        self.max_instances_floor = int(os.getenv("MAX_INSTANCES_FLOOR", "10"))
        self.max_instances_ceiling = int(os.getenv("MAX_INSTANCES_CEILING", "100"))
        
        # Dry run mode for testing
        self.dry_run = os.getenv("DRY_RUN_MODE", "false").lower() == "true"
        
        logger.info(f"CloudRunManager initialized for project: {project_id}")
        if self.dry_run:
            logger.warning("⚠️  DRY RUN MODE ENABLED - No actual changes will be made")
    
    async def rollback_traffic(
        self,
        service_name: str,
        region: str,
        target_revision: str,
        percentage: int = 100
    ) -> Dict[str, Any]:
        """
        Rollback traffic to a specific revision
        
        Args:
            service_name: Name of the Cloud Run service
            region: GCP region
            target_revision: Revision to route traffic to
            percentage: Percentage of traffic (default: 100)
            
        Returns:
            Dictionary with rollback details
        """
        logger.info(
            f"Rolling back {service_name} to {target_revision} "
            f"({percentage}% traffic)"
        )
        
        try:
            # Get current service state
            service_path = self._get_service_path(service_name, region)
            service = await self._get_service(service_path)
            
            if not service:
                raise ValueError(f"Service {service_name} not found")
            
            # Verify target revision exists
            available_revisions = await self.list_revisions(service_name, region)
            if target_revision not in available_revisions:
                raise ValueError(
                    f"Target revision {target_revision} not found. "
                    f"Available: {available_revisions}"
                )
            
            # Record old traffic split
            old_traffic = self._get_traffic_split(service)
            
            logger.info(f"Current traffic split: {old_traffic}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would rollback to {target_revision}")
                return {
                    "dry_run": True,
                    "service": service_name,
                    "target_revision": target_revision,
                    "old_traffic": old_traffic,
                    "new_traffic": {target_revision: percentage}
                }
            
            # Build new traffic configuration
            new_traffic = [
                run_v2.TrafficTarget(
                    type_=run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION,
                    revision=self._get_revision_path(service_name, region, target_revision),
                    percent=percentage
                )
            ]
            
            # Update service with new traffic split
            service.traffic = new_traffic
            
            update_mask = {"paths": ["traffic"]}
            
            loop = asyncio.get_event_loop()
            operation = await loop.run_in_executor(
                None,
                lambda: self.client.update_service(
                    service=service,
                    update_mask=update_mask
                )
            )
            
            # Wait for operation to complete
            updated_service = await loop.run_in_executor(
                None,
                operation.result,
                300  # 5 minute timeout
            )
            
            new_traffic_split = self._get_traffic_split(updated_service)
            
            logger.info(f"✅ Rollback complete. New traffic: {new_traffic_split}")
            
            return {
                "success": True,
                "service": service_name,
                "target_revision": target_revision,
                "old_traffic": old_traffic,
                "new_traffic": new_traffic_split,
                "operation_id": operation.operation.name
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}", exc_info=True)
            raise
    
    async def update_scaling(
        self,
        service_name: str,
        region: str,
        min_instances: Optional[int] = None,
        max_instances: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update service scaling configuration
        
        Args:
            service_name: Name of the Cloud Run service
            region: GCP region
            min_instances: New minimum instance count
            max_instances: New maximum instance count
            
        Returns:
            Dictionary with scaling update details
        """
        logger.info(
            f"Updating scaling for {service_name}: "
            f"min={min_instances}, max={max_instances}"
        )
        
        try:
            # Get current service state
            service_path = self._get_service_path(service_name, region)
            service = await self._get_service(service_path)
            
            if not service:
                raise ValueError(f"Service {service_name} not found")
            
            # Get current scaling settings
            current_scaling = service.template.scaling
            old_min = current_scaling.min_instance_count if current_scaling else 0
            old_max = current_scaling.max_instance_count if current_scaling else 100
            
            logger.info(f"Current scaling: min={old_min}, max={old_max}")
            
            # Apply safety limits
            if min_instances is not None:
                min_instances = max(self.min_instances_floor, min(min_instances, self.min_instances_ceiling))
            
            if max_instances is not None:
                max_instances = max(self.max_instances_floor, min(max_instances, self.max_instances_ceiling))
            
            # Validate min <= max
            effective_min = min_instances if min_instances is not None else old_min
            effective_max = max_instances if max_instances is not None else old_max
            
            if effective_min > effective_max:
                raise ValueError(
                    f"min_instances ({effective_min}) cannot be greater than "
                    f"max_instances ({effective_max})"
                )
            
            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would update scaling to min={effective_min}, max={effective_max}"
                )
                return {
                    "dry_run": True,
                    "service": service_name,
                    "old_min": old_min,
                    "old_max": old_max,
                    "new_min": effective_min,
                    "new_max": effective_max
                }
            
            # Update scaling configuration
            if not service.template.scaling:
                service.template.scaling = run_v2.RevisionScaling()
            
            if min_instances is not None:
                service.template.scaling.min_instance_count = min_instances
            
            if max_instances is not None:
                service.template.scaling.max_instance_count = max_instances
            
            update_mask = {"paths": ["template.scaling"]}
            
            loop = asyncio.get_event_loop()
            operation = await loop.run_in_executor(
                None,
                lambda: self.client.update_service(
                    service=service,
                    update_mask=update_mask
                )
            )
            
            # Wait for operation to complete
            updated_service = await loop.run_in_executor(
                None,
                operation.result,
                300
            )
            
            new_scaling = updated_service.template.scaling
            new_min = new_scaling.min_instance_count if new_scaling else 0
            new_max = new_scaling.max_instance_count if new_scaling else 100
            
            logger.info(f"✅ Scaling updated: min={new_min}, max={new_max}")
            
            return {
                "success": True,
                "service": service_name,
                "old_min": old_min,
                "old_max": old_max,
                "new_min": new_min,
                "new_max": new_max,
                "operation_id": operation.operation.name
            }
            
        except Exception as e:
            logger.error(f"Scaling update failed: {str(e)}", exc_info=True)
            raise
    
    async def get_service_info(
        self,
        service_name: str,
        region: str
    ) -> ServiceInfo:
        """Get detailed information about a service"""
        
        try:
            service_path = self._get_service_path(service_name, region)
            service = await self._get_service(service_path)
            
            if not service:
                raise ValueError(f"Service {service_name} not found")
            
            traffic_split = self._get_traffic_split(service)
            current_revision = self._get_current_revision(service)
            
            scaling = service.template.scaling
            min_instances = scaling.min_instance_count if scaling else 0
            max_instances = scaling.max_instance_count if scaling else 100
            
            available_revisions = await self.list_revisions(service_name, region)
            
            return ServiceInfo(
                name=service_name,
                region=region,
                current_revision=current_revision,
                traffic_split=traffic_split,
                min_instances=min_instances,
                max_instances=max_instances,
                available_revisions=available_revisions
            )
            
        except Exception as e:
            logger.error(f"Error getting service info: {str(e)}")
            raise
    
    async def list_revisions(
        self,
        service_name: str,
        region: str,
        limit: int = 10
    ) -> List[str]:
        """List available revisions for a service"""
        
        try:
            parent = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            
            request = run_v2.ListRevisionsRequest(
                parent=parent,
                page_size=limit
            )
            
            loop = asyncio.get_event_loop()
            revisions = await loop.run_in_executor(
                None,
                lambda: list(self.client.list_revisions(request=request))
            )
            
            revision_names = [rev.name.split('/')[-1] for rev in revisions]
            
            logger.debug(f"Found {len(revision_names)} revisions for {service_name}")
            
            return revision_names
            
        except Exception as e:
            logger.error(f"Error listing revisions: {str(e)}")
            return []
    
    async def _get_service(self, service_path: str) -> Optional[Service]:
        """Get service object from Cloud Run API"""
        try:
            loop = asyncio.get_event_loop()
            service = await loop.run_in_executor(
                None,
                lambda: self.client.get_service(name=service_path)
            )
            return service
        except exceptions.NotFound:
            return None
        except Exception as e:
            logger.error(f"Error getting service: {str(e)}")
            raise
    
    def _get_service_path(self, service_name: str, region: str) -> str:
        """Build service path for API calls"""
        return f"projects/{self.project_id}/locations/{region}/services/{service_name}"
    
    def _get_revision_path(self, service_name: str, region: str, revision_name: str) -> str:
        """Build revision path for API calls"""
        return f"projects/{self.project_id}/locations/{region}/services/{service_name}/revisions/{revision_name}"
    
    def _get_traffic_split(self, service: Service) -> Dict[str, int]:
        """Extract traffic split from service"""
        traffic_split = {}
        
        if service.traffic:
            for target in service.traffic:
                if target.revision:
                    revision_name = target.revision.split('/')[-1]
                    traffic_split[revision_name] = target.percent
        
        return traffic_split
    
    def _get_current_revision(self, service: Service) -> str:
        """Get the current (latest) revision name"""
        if service.traffic:
            for target in service.traffic:
                if target.type_ == run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST:
                    return target.revision.split('/')[-1] if target.revision else "unknown"
        
        # Fallback: return first revision with traffic
        if service.traffic and service.traffic[0].revision:
            return service.traffic[0].revision.split('/')[-1]
        
        return "unknown"