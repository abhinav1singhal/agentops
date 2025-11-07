"""
Gemini Reasoner - Uses Gemini 1.5 Flash for intelligent decision-making
"""

import logging
import os
import json
from typing import Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import run_v2

from models import (
    ServiceHealth,
    AIRecommendation,
    ActionType,
    Incident
)

logger = logging.getLogger(__name__)


class GeminiReasoner:
    """Uses Gemini AI to analyze service health and recommend actions"""
    
    def __init__(self, project_id: str, region: str):
        self.project_id = project_id
        self.region = region
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=region)
        
        # Initialize Gemini model
        self.model = GenerativeModel("gemini-1.5-flash")
        
        # Generation config
        self.generation_config = GenerationConfig(
            temperature=0.2,  # Low temperature for consistent, factual responses
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )
        
        # Cloud Run client for getting revision info
        self.run_client = run_v2.ServicesClient()
        
        logger.info(f"GeminiReasoner initialized with model: gemini-1.5-flash")
    
    async def analyze_and_recommend(
        self, 
        health_status: ServiceHealth
    ) -> AIRecommendation:
        """
        Analyze service health and recommend remediation action
        
        Args:
            health_status: Current health status of the service
            
        Returns:
            AIRecommendation with suggested action
        """
        logger.info(f"Analyzing {health_status.service_name} with Gemini...")
        
        try:
            # Get service revision information
            revision_info = await self._get_revision_info(
                health_status.service_name,
                health_status.region
            )
            
            # Build prompt
            prompt = self._build_analysis_prompt(health_status, revision_info)
            
            # Call Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse response
            recommendation = self._parse_recommendation(
                response.text,
                health_status,
                revision_info
            )
            
            logger.info(
                f"Gemini recommendation for {health_status.service_name}: "
                f"{recommendation.action} (confidence: {recommendation.confidence:.2f})"
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {str(e)}", exc_info=True)
            # Return safe default: no action
            return AIRecommendation(
                action=ActionType.NONE,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                risk_assessment="Unable to assess risk due to analysis error",
                expected_impact="No action will be taken"
            )
    
    def _build_analysis_prompt(
        self,
        health_status: ServiceHealth,
        revision_info: dict
    ) -> str:
        """Build prompt for Gemini analysis"""
        
        # Format log samples
        log_summary = "\n".join([
            f"[{log.severity}] {log.message[:200]}"
            for log in health_status.log_samples[:5]  # Top 5 error logs
        ])
        
        prompt = f"""You are an expert Site Reliability Engineer (SRE) analyzing a Cloud Run service health issue.

SERVICE INFORMATION:
- Service Name: {health_status.service_name}
- Region: {health_status.region}
- Current Status: {health_status.status}

METRICS (Last 5 minutes):
- Error Rate: {health_status.metrics.error_rate:.2f}% (Threshold: 5%)
- Request Count: {health_status.metrics.request_count}
- Failed Requests: {health_status.metrics.error_count}
- Successful Requests: {health_status.metrics.success_count}
- Latency P95: {health_status.metrics.latency_p95}ms (Threshold: 600ms)

REVISION INFORMATION:
- Current Revision: {revision_info.get('current_revision', 'unknown')}
- Traffic Split: {json.dumps(revision_info.get('traffic_split', {}), indent=2)}
- Available Revisions: {', '.join(revision_info.get('available_revisions', []))}
- Previous Stable Revision: {revision_info.get('previous_revision', 'unknown')}

RECENT ERROR LOGS:
{log_summary if log_summary else "No recent error logs"}

ANOMALY DETECTED:
{health_status.anomaly_summary}

AVAILABLE ACTIONS:
1. ROLLBACK - Route 100% traffic to previous stable revision
2. SCALE_UP - Increase min/max instance counts
3. SCALE_DOWN - Decrease instance counts (if over-provisioned)
4. REDEPLOY - Trigger new build and deployment
5. NONE - Take no action (not serious enough)

YOUR TASK:
Analyze the situation and recommend the best remediation action. Consider:
- Severity of the issue (is it critical?)
- Likely root cause based on metrics and logs
- Risk vs benefit of each action
- Confidence in your recommendation

Respond in this EXACT JSON format:
{{
  "action": "ROLLBACK|SCALE_UP|SCALE_DOWN|REDEPLOY|NONE",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why you chose this action",
  "risk_assessment": "What could go wrong with this action",
  "expected_impact": "What should happen after this action",
  "root_cause_hypothesis": "Your best guess at what caused this issue"
}}

Be decisive but conservative. If uncertain, choose NONE and explain why more investigation is needed.
"""
        
        return prompt
    
    def _parse_recommendation(
        self,
        gemini_response: str,
        health_status: ServiceHealth,
        revision_info: dict
    ) -> AIRecommendation:
        """Parse Gemini's JSON response into AIRecommendation"""
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = gemini_response.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            data = json.loads(response_text.strip())
            
            # Parse action type
            action_str = data.get("action", "NONE").upper()
            action = ActionType[action_str] if action_str in ActionType.__members__ else ActionType.NONE
            
            # Get target revision for rollback
            target_revision = None
            if action == ActionType.ROLLBACK:
                target_revision = revision_info.get("previous_revision")
            
            # Build recommendation
            recommendation = AIRecommendation(
                action=action,
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", "No reasoning provided"),
                risk_assessment=data.get("risk_assessment", "Unknown risk"),
                expected_impact=data.get("expected_impact", "Unknown impact"),
                target_revision=target_revision
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            logger.debug(f"Raw response: {gemini_response}")
            
            # Fallback: return safe default
            return AIRecommendation(
                action=ActionType.NONE,
                confidence=0.0,
                reasoning=f"Failed to parse recommendation: {str(e)}",
                risk_assessment="Unable to assess risk",
                expected_impact="No action will be taken"
            )
    
    async def _get_revision_info(self, service_name: str, region: str) -> dict:
        """Get Cloud Run service revision information"""
        
        try:
            # Build service path
            service_path = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            
            # Get service details
            import asyncio
            loop = asyncio.get_event_loop()
            service = await loop.run_in_executor(
                None,
                self.run_client.get_service,
                {"name": service_path}
            )
            
            # Extract traffic split
            traffic_split = {}
            current_revision = None
            
            if service.traffic:
                for traffic_target in service.traffic:
                    if traffic_target.revision:
                        traffic_split[traffic_target.revision] = traffic_target.percent
                        if traffic_target.type_ == run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST:
                            current_revision = traffic_target.revision
            
            # List all revisions
            parent = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            revisions_request = run_v2.ListRevisionsRequest(parent=parent)
            
            revisions = await loop.run_in_executor(
                None,
                lambda: list(self.run_client.list_revisions(request=revisions_request))
            )
            
            available_revisions = [rev.name.split('/')[-1] for rev in revisions]
            
            # Determine previous stable revision (one with traffic but not latest)
            previous_revision = None
            for rev_name, percent in traffic_split.items():
                if rev_name != current_revision and percent > 0:
                    previous_revision = rev_name
                    break
            
            # If no previous revision with traffic, use the second-most-recent
            if not previous_revision and len(available_revisions) > 1:
                previous_revision = available_revisions[1]
            
            return {
                "current_revision": current_revision,
                "previous_revision": previous_revision,
                "traffic_split": traffic_split,
                "available_revisions": available_revisions
            }
            
        except Exception as e:
            logger.error(f"Error getting revision info: {str(e)}")
            return {
                "current_revision": "unknown",
                "previous_revision": None,
                "traffic_split": {},
                "available_revisions": []
            }
    
    async def generate_explanation(self, incident: Incident) -> str:
        """Generate human-readable explanation of an incident"""
        
        prompt = f"""You are writing a post-incident report for a Cloud Run service issue.

INCIDENT DETAILS:
- Service: {incident.service_name}
- Duration: {incident.started_at} to {incident.ended_at or 'ongoing'}
- Error Rate: {incident.metrics_snapshot.error_rate:.2f}%
- Requests Affected: {incident.metrics_snapshot.error_count} out of {incident.metrics_snapshot.request_count}

ANOMALY:
{incident.anomaly_description}

ACTION TAKEN:
{incident.recommendation.action if incident.recommendation else 'None'} - {incident.recommendation.reasoning if incident.recommendation else 'N/A'}

RESULT:
{incident.action_taken.status if incident.action_taken else 'Pending'}

Write a brief, clear explanation in plain English (2-3 sentences) suitable for:
1. Engineering team (technical but concise)
2. Non-technical stakeholders (what happened, what was done, outcome)

Focus on:
- What went wrong
- Why it happened (best hypothesis)
- What was done to fix it
- Next steps or learnings
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return f"Automated explanation unavailable. Manual review required. Error: {str(e)}"