"""
Health Scanner - Monitors Cloud Run services using Cloud Monitoring and Logging
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional
from google.cloud import monitoring_v3, logging as cloud_logging
from google.api_core import retry
import asyncio

from models import (
    ServiceHealth, 
    ServiceHealthStatus, 
    HealthMetrics, 
    LogSample
)

logger = logging.getLogger(__name__)


class HealthScanner:
    """Scans Cloud Run services for health issues"""
    
    def __init__(self, project_id: str, region: str):
        self.project_id = project_id
        self.region = region
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.logging_client = cloud_logging.Client(project=project_id)
        
        # Thresholds from environment
        self.error_threshold = float(os.getenv("ERROR_THRESHOLD", "5.0"))
        self.latency_p95_threshold = float(os.getenv("LATENCY_P95_THRESHOLD_MS", "600"))
        self.latency_p99_threshold = float(os.getenv("LATENCY_P99_THRESHOLD_MS", "1000"))
        self.min_request_count = int(os.getenv("MIN_REQUEST_COUNT", "100"))
        self.scan_window_minutes = int(os.getenv("SCAN_WINDOW_MINUTES", "5"))
        
        logger.info(f"HealthScanner initialized for project {project_id}, region {region}")
        logger.info(f"Thresholds: error={self.error_threshold}%, latency_p95={self.latency_p95_threshold}ms")
    
    async def scan_service(self, service_name: str, region: str) -> ServiceHealth:
        """
        Scan a single Cloud Run service for health issues
        
        Args:
            service_name: Name of the Cloud Run service
            region: GCP region where service is deployed
            
        Returns:
            ServiceHealth object with current health status
        """
        logger.info(f"Scanning {service_name} in {region}")
        
        try:
            # Run metrics and logs fetching concurrently
            metrics_task = asyncio.create_task(self._get_metrics(service_name, region))
            logs_task = asyncio.create_task(self._get_error_logs(service_name, region))
            
            metrics, log_samples = await asyncio.gather(metrics_task, logs_task)
            
            # Determine health status
            status, has_anomaly, anomaly_summary = self._assess_health(
                metrics, service_name
            )
            
            return ServiceHealth(
                service_name=service_name,
                region=region,
                status=status,
                metrics=metrics,
                log_samples=log_samples,
                has_anomaly=has_anomaly,
                anomaly_summary=anomaly_summary,
                error_rate=metrics.error_rate,
                latency_p95=metrics.latency_p95,
                request_count=metrics.request_count
            )
            
        except Exception as e:
            logger.error(f"Error scanning {service_name}: {str(e)}", exc_info=True)
            # Return unknown status on error
            return ServiceHealth(
                service_name=service_name,
                region=region,
                status=ServiceHealthStatus.UNKNOWN,
                metrics=HealthMetrics(
                    error_rate=0.0,
                    request_count=0,
                    success_count=0,
                    error_count=0
                ),
                error_rate=0.0,
                latency_p95=None,
                request_count=0,
                has_anomaly=False
            )
    
    async def _get_metrics(self, service_name: str, region: str) -> HealthMetrics:
        """Fetch metrics from Cloud Monitoring"""
        
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=self.scan_window_minutes)
        
        # Convert to timestamp format
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": int(end_time.timestamp())},
            "start_time": {"seconds": int(start_time.timestamp())}
        })
        
        project_name = f"projects/{self.project_id}"
        
        try:
            # Get request count metric
            request_count = await self._query_metric(
                project_name,
                "run.googleapis.com/request_count",
                service_name,
                region,
                interval,
                "ALIGN_SUM"
            )
            
            # Get request latencies (for percentiles)
            latencies = await self._query_metric(
                project_name,
                "run.googleapis.com/request_latencies",
                service_name,
                region,
                interval,
                "ALIGN_DELTA",
                reducer="REDUCE_PERCENTILE_95"
            )
            
            # Calculate error rate from request count by response code
            error_count = await self._query_metric(
                project_name,
                "run.googleapis.com/request_count",
                service_name,
                region,
                interval,
                "ALIGN_SUM",
                filter_suffix='metric.label.response_code_class="5xx"'
            )
            
            # Calculate metrics
            total_requests = int(request_count or 0)
            total_errors = int(error_count or 0)
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
            
            # Latency in milliseconds
            latency_p95 = float(latencies) if latencies else None
            
            metrics = HealthMetrics(
                error_rate=round(error_rate, 2),
                latency_p95=round(latency_p95, 2) if latency_p95 else None,
                request_count=total_requests,
                success_count=total_requests - total_errors,
                error_count=total_errors
            )
            
            logger.info(
                f"Metrics for {service_name}: "
                f"requests={total_requests}, errors={total_errors}, "
                f"error_rate={error_rate:.2f}%, latency_p95={latency_p95}ms"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error fetching metrics for {service_name}: {str(e)}")
            # Return zero metrics on error
            return HealthMetrics(
                error_rate=0.0,
                request_count=0,
                success_count=0,
                error_count=0
            )
    
    async def _query_metric(
        self,
        project_name: str,
        metric_type: str,
        service_name: str,
        region: str,
        interval: monitoring_v3.TimeInterval,
        aligner: str,
        reducer: Optional[str] = None,
        filter_suffix: str = ""
    ) -> float:
        """Query a single metric from Cloud Monitoring"""
        
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
        
        # Execute query in thread pool (sync API)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.monitoring_client.list_time_series(
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
        for result in results:
            if result.points:
                point = result.points[0]
                if hasattr(point.value, 'int64_value'):
                    return float(point.value.int64_value)
                elif hasattr(point.value, 'double_value'):
                    return point.value.double_value
        
        return 0.0
    
    async def _get_error_logs(
        self, 
        service_name: str, 
        region: str,
        max_entries: int = 50
    ) -> List[LogSample]:
        """Fetch recent error logs from Cloud Logging"""
        
        # Build log filter
        filter_str = (
            f'resource.type="cloud_run_revision" '
            f'resource.labels.service_name="{service_name}" '
            f'resource.labels.location="{region}" '
            f'severity>=ERROR '
            f'timestamp>="{(datetime.utcnow() - timedelta(minutes=self.scan_window_minutes)).isoformat()}Z"'
        )
        
        try:
            # Execute query in thread pool (sync API)
            loop = asyncio.get_event_loop()
            entries = await loop.run_in_executor(
                None,
                lambda: list(self.logging_client.list_entries(
                    filter_=filter_str,
                    page_size=max_entries,
                    order_by=cloud_logging.DESCENDING
                ))
            )
            
            log_samples = []
            for entry in entries[:max_entries]:
                log_samples.append(LogSample(
                    timestamp=entry.timestamp,
                    severity=entry.severity,
                    message=str(entry.payload)[:500],  # Truncate long messages
                    resource=entry.resource._properties if hasattr(entry, 'resource') else None
                ))
            
            logger.info(f"Found {len(log_samples)} error logs for {service_name}")
            return log_samples
            
        except Exception as e:
            logger.error(f"Error fetching logs for {service_name}: {str(e)}")
            return []
    
    def _assess_health(
        self,
        metrics: HealthMetrics,
        service_name: str
    ) -> tuple[ServiceHealthStatus, bool, Optional[str]]:
        """
        Assess service health based on metrics
        
        Returns:
            (status, has_anomaly, anomaly_summary)
        """
        
        # Not enough data
        if metrics.request_count < self.min_request_count:
            logger.info(
                f"{service_name}: Insufficient data "
                f"({metrics.request_count} requests < {self.min_request_count} threshold)"
            )
            return ServiceHealthStatus.HEALTHY, False, None
        
        anomalies = []
        
        # Check error rate
        if metrics.error_rate > self.error_threshold:
            anomalies.append(
                f"High error rate: {metrics.error_rate:.2f}% "
                f"(threshold: {self.error_threshold}%)"
            )
        
        # Check latency
        if metrics.latency_p95 and metrics.latency_p95 > self.latency_p95_threshold:
            anomalies.append(
                f"High latency p95: {metrics.latency_p95:.2f}ms "
                f"(threshold: {self.latency_p95_threshold}ms)"
            )
        
        # Determine status
        if not anomalies:
            return ServiceHealthStatus.HEALTHY, False, None
        
        # Multiple anomalies = unhealthy
        if len(anomalies) > 1:
            status = ServiceHealthStatus.UNHEALTHY
        else:
            status = ServiceHealthStatus.DEGRADED
        
        anomaly_summary = "; ".join(anomalies)
        logger.warning(f"{service_name} anomalies detected: {anomaly_summary}")
        
        return status, True, anomaly_summary