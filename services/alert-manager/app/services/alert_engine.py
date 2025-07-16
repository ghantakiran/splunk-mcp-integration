"""
Alert Creation Engine with Natural Language Processing support.
"""
import re
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.logging import AlertLogger
from ..models.alert import (
    AlertRule, AlertIncident, AlertCondition,
    AlertRuleCreate, AlertIncidentCreate,
    NaturalLanguageAlertRequest, AlertTestRequest, AlertTestResponse,
    ConditionType, IncidentSeverity, AlertStatus
)


class AlertEngine:
    """Core alert creation and processing engine."""
    
    def __init__(self):
        self.logger = AlertLogger("alert_engine")
        self.nlp_service_url = settings.nlp_service_url
        
        # Predefined alert patterns for common use cases
        self.alert_patterns = {
            "threshold": {
                "patterns": [
                    r"(?:alert|notify).*when\s+(.+?)\s+(?:exceeds?|goes?\s+above|is\s+greater\s+than|>)\s+(.+)",
                    r"(?:alert|notify).*when\s+(.+?)\s+(?:falls?\s+below|goes?\s+under|is\s+less\s+than|<)\s+(.+)",
                    r"(?:alert|notify).*when\s+(.+?)\s+(?:equals?|is)\s+(.+)",
                ],
                "type": ConditionType.THRESHOLD
            },
            "statistical": {
                "patterns": [
                    r"(?:alert|notify).*when\s+(?:average|avg|mean)\s+(.+?)\s+(?:exceeds?|>)\s+(.+)",
                    r"(?:alert|notify).*when\s+(?:count|number)\s+of\s+(.+?)\s+(?:exceeds?|>)\s+(.+)",
                    r"(?:alert|notify).*when\s+(?:sum|total)\s+of\s+(.+?)\s+(?:exceeds?|>)\s+(.+)",
                ],
                "type": ConditionType.STATISTICAL
            },
            "pattern": {
                "patterns": [
                    r"(?:alert|notify).*when\s+(.+?)\s+(?:contains?|includes?|matches?)\s+[\"'](.+?)[\"']",
                    r"(?:alert|notify).*when\s+(.+?)\s+(?:pattern|regex)\s+[\"'](.+?)[\"']",
                ],
                "type": ConditionType.PATTERN
            },
            "anomaly": {
                "patterns": [
                    r"(?:alert|notify).*when\s+(.+?)\s+(?:is\s+)?(?:anomalous|unusual|abnormal)",
                    r"(?:alert|notify).*when\s+(?:there\s+is\s+an?\s+)?(?:anomaly|spike|drop)\s+in\s+(.+)",
                ],
                "type": ConditionType.ANOMALY
            }
        }
        
        # Common field mappings
        self.field_mappings = {
            "cpu": "cpu_usage",
            "memory": "memory_usage",
            "disk": "disk_usage",
            "response time": "response_time",
            "error rate": "error_rate",
            "throughput": "throughput",
            "latency": "latency",
            "status code": "status_code",
            "log level": "log_level",
            "severity": "severity"
        }
        
        # Operator mappings
        self.operator_mappings = {
            "exceeds": ">",
            "goes above": ">",
            "is greater than": ">",
            "above": ">",
            "falls below": "<",
            "goes under": "<",
            "is less than": "<",
            "below": "<",
            "equals": "==",
            "is": "==",
            "not equals": "!=",
            "is not": "!="
        }
    
    async def create_alert_from_natural_language(
        self,
        request: NaturalLanguageAlertRequest,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> AlertRule:
        """Create an alert rule from natural language description."""
        try:
            # Parse the natural language description
            parsed_alert = await self._parse_natural_language(request.description)
            
            # Convert to SPL query using NLP service
            spl_query = await self._generate_spl_query(parsed_alert, request.additional_context)
            
            # Create alert rule
            alert_data = AlertRuleCreate(
                name=parsed_alert.get("name", f"Alert from: {request.description[:50]}..."),
                description=request.description,
                spl_query=spl_query,
                conditions=parsed_alert.get("conditions", []),
                severity=request.severity,
                threshold_value=parsed_alert.get("threshold_value"),
                threshold_operator=parsed_alert.get("threshold_operator"),
                time_window=parsed_alert.get("time_window", 300),
                evaluation_interval=parsed_alert.get("evaluation_interval", 300),
                tags=request.tags,
                metadata=request.additional_context
            )
            
            # TODO: Save to database
            self.logger.log_alert_created(
                alert_id="generated",
                rule_name=alert_data.name,
                user_id=user_id,
                conditions=parsed_alert.get("conditions", [])
            )
            
            return alert_data
            
        except Exception as e:
            self.logger.log_error("create_alert_from_natural_language", str(e))
            raise
    
    async def _parse_natural_language(self, description: str) -> Dict[str, Any]:
        """Parse natural language description to extract alert components."""
        description_lower = description.lower()
        parsed = {
            "conditions": [],
            "threshold_value": None,
            "threshold_operator": None,
            "time_window": 300,
            "evaluation_interval": 300
        }
        
        # Try to match against predefined patterns
        for category, config in self.alert_patterns.items():
            for pattern in config["patterns"]:
                match = re.search(pattern, description_lower)
                if match:
                    field = match.group(1).strip()
                    value = match.group(2).strip()
                    
                    # Map field names
                    mapped_field = self.field_mappings.get(field, field)
                    
                    # Extract operator and numeric value
                    operator, numeric_value = self._extract_operator_and_value(description_lower, value)
                    
                    parsed["conditions"].append({
                        "condition_type": config["type"].value,
                        "field_name": mapped_field,
                        "operator": operator,
                        "value": value,
                        "pattern": pattern if config["type"] == ConditionType.PATTERN else None
                    })
                    
                    if numeric_value is not None:
                        parsed["threshold_value"] = numeric_value
                        parsed["threshold_operator"] = operator
                    
                    break
        
        # Extract time window if mentioned
        time_match = re.search(r"(?:for|over|in)\s+(\d+)\s*(minutes?|mins?|seconds?|secs?|hours?|hrs?)", description_lower)
        if time_match:
            time_value = int(time_match.group(1))
            time_unit = time_match.group(2)
            
            if "hour" in time_unit:
                parsed["time_window"] = time_value * 3600
            elif "minute" in time_unit or "min" in time_unit:
                parsed["time_window"] = time_value * 60
            else:  # seconds
                parsed["time_window"] = time_value
        
        # Generate alert name
        parsed["name"] = self._generate_alert_name(description)
        
        return parsed
    
    def _extract_operator_and_value(self, description: str, value_str: str) -> Tuple[Optional[str], Optional[float]]:
        """Extract operator and numeric value from description."""
        # Try to extract numeric value
        numeric_match = re.search(r"(\d+(?:\.\d+)?)\s*(%|percent)?", value_str)
        numeric_value = None
        if numeric_match:
            numeric_value = float(numeric_match.group(1))
            if numeric_match.group(2):  # percentage
                numeric_value = numeric_value / 100
        
        # Determine operator from context
        operator = None
        for text_op, symbol_op in self.operator_mappings.items():
            if text_op in description:
                operator = symbol_op
                break
        
        return operator, numeric_value
    
    def _generate_alert_name(self, description: str) -> str:
        """Generate a concise alert name from description."""
        # Extract key components
        words = description.split()
        
        # Find the main subject (usually after "when")
        when_index = -1
        for i, word in enumerate(words):
            if word.lower() in ["when", "if"]:
                when_index = i
                break
        
        if when_index >= 0 and when_index < len(words) - 1:
            # Take a few words after "when"
            key_words = words[when_index + 1:when_index + 6]
            name = " ".join(key_words)
        else:
            # Fallback: take first few words
            name = " ".join(words[:6])
        
        # Clean up and capitalize
        name = re.sub(r"[^\w\s]", "", name)
        name = " ".join(name.split())  # Clean whitespace
        return name.title()
    
    async def _generate_spl_query(self, parsed_alert: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate SPL query using the NLP service."""
        try:
            # Prepare request for NLP service
            nlp_request = {
                "description": f"Create SPL query for alert: {parsed_alert}",
                "context": context,
                "query_type": "alert",
                "conditions": parsed_alert.get("conditions", [])
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.nlp_service_url}/api/v1/spl/translate/enhanced",
                    json=nlp_request,
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("spl_query", "search index=main")
                
        except Exception as e:
            self.logger.log_error("generate_spl_query", str(e))
            # Fallback to basic query
            return self._generate_fallback_spl_query(parsed_alert)
    
    def _generate_fallback_spl_query(self, parsed_alert: Dict[str, Any]) -> str:
        """Generate a basic SPL query as fallback."""
        conditions = parsed_alert.get("conditions", [])
        if not conditions:
            return "search index=main"
        
        # Build basic query from conditions
        query_parts = ["search index=main"]
        
        for condition in conditions:
            field = condition.get("field_name", "")
            operator = condition.get("operator", "")
            value = condition.get("value", "")
            
            if field and operator and value:
                if operator == ">":
                    query_parts.append(f"| where {field} > {value}")
                elif operator == "<":
                    query_parts.append(f"| where {field} < {value}")
                elif operator == "==":
                    query_parts.append(f"| where {field} = \"{value}\"")
        
        return " ".join(query_parts)
    
    async def evaluate_alert_rule(
        self,
        rule: AlertRule,
        db: AsyncSession
    ) -> List[AlertIncident]:
        """Evaluate an alert rule and create incidents if conditions are met."""
        try:
            # Execute SPL query
            query_result = await self._execute_spl_query(rule.spl_query)
            
            # Check if conditions are met
            incidents = []
            if await self._check_alert_conditions(rule, query_result):
                # Create incident
                incident = await self._create_incident(rule, query_result, db)
                incidents.append(incident)
                
                self.logger.log_alert_triggered(
                    alert_id=rule.id,
                    incident_id=incident.id,
                    rule_name=rule.name,
                    trigger_value=incident.trigger_value,
                    threshold=rule.threshold_value
                )
            
            # Update rule evaluation timestamp
            rule.last_evaluated_at = datetime.utcnow()
            if incidents:
                rule.last_triggered_at = datetime.utcnow()
            
            return incidents
            
        except Exception as e:
            self.logger.log_error("evaluate_alert_rule", str(e), {"rule_id": rule.id})
            return []
    
    async def _execute_spl_query(self, spl_query: str) -> Dict[str, Any]:
        """Execute SPL query and return results."""
        # TODO: Integrate with actual Splunk API
        # For now, return mock data
        return {
            "results": [
                {"_time": datetime.utcnow().isoformat(), "value": 85.5, "host": "server1"},
                {"_time": datetime.utcnow().isoformat(), "value": 92.1, "host": "server2"}
            ],
            "count": 2,
            "summary": {"max_value": 92.1, "avg_value": 88.8}
        }
    
    async def _check_alert_conditions(self, rule: AlertRule, query_result: Dict[str, Any]) -> bool:
        """Check if alert conditions are met based on query results."""
        if not query_result.get("results"):
            return False
        
        # Check threshold condition
        if rule.threshold_value is not None and rule.threshold_operator:
            max_value = query_result.get("summary", {}).get("max_value", 0)
            
            if rule.threshold_operator == ">" and max_value > rule.threshold_value:
                return True
            elif rule.threshold_operator == "<" and max_value < rule.threshold_value:
                return True
            elif rule.threshold_operator == "==" and max_value == rule.threshold_value:
                return True
        
        # Check other conditions
        for condition in rule.conditions_rel:
            if condition.condition_type == ConditionType.THRESHOLD.value:
                # Additional threshold checks
                pass
            elif condition.condition_type == ConditionType.STATISTICAL.value:
                # Statistical condition checks
                pass
        
        return False
    
    async def _create_incident(
        self,
        rule: AlertRule,
        query_result: Dict[str, Any],
        db: AsyncSession
    ) -> AlertIncident:
        """Create a new alert incident."""
        # Determine trigger value
        trigger_value = None
        if query_result.get("summary", {}).get("max_value"):
            trigger_value = query_result["summary"]["max_value"]
        
        # Create incident
        incident_data = AlertIncidentCreate(
            rule_id=rule.id,
            severity=IncidentSeverity(rule.severity),
            title=f"Alert: {rule.name}",
            description=f"Alert triggered: {rule.description}",
            trigger_value=trigger_value,
            trigger_data=query_result.get("results", []),
            trigger_query_result=query_result
        )
        
        # TODO: Save to database and return actual incident
        # For now, create a mock incident object
        incident = AlertIncident(
            id=f"incident_{datetime.utcnow().timestamp()}",
            rule_id=rule.id,
            status="open",
            severity=rule.severity,
            title=incident_data.title,
            description=incident_data.description,
            trigger_value=trigger_value,
            triggered_at=datetime.utcnow()
        )
        
        return incident
    
    async def test_alert_rule(
        self,
        request: AlertTestRequest,
        db: AsyncSession
    ) -> AlertTestResponse:
        """Test an alert rule without creating actual incidents."""
        try:
            # TODO: Get rule from database
            rule = None  # await get_alert_rule(request.rule_id, db)
            
            if not rule:
                return AlertTestResponse(
                    rule_id=request.rule_id,
                    test_passed=False,
                    would_trigger=False,
                    evaluation_result={},
                    errors=["Alert rule not found"]
                )
            
            # Use test data or execute actual query
            if request.test_data:
                query_result = request.test_data
            else:
                query_result = await self._execute_spl_query(rule.spl_query)
            
            # Check conditions
            would_trigger = await self._check_alert_conditions(rule, query_result)
            
            # Determine trigger value
            trigger_value = None
            if query_result.get("summary", {}).get("max_value"):
                trigger_value = query_result["summary"]["max_value"]
            
            return AlertTestResponse(
                rule_id=request.rule_id,
                test_passed=True,
                would_trigger=would_trigger,
                trigger_value=trigger_value,
                evaluation_result=query_result
            )
            
        except Exception as e:
            self.logger.log_error("test_alert_rule", str(e))
            return AlertTestResponse(
                rule_id=request.rule_id,
                test_passed=False,
                would_trigger=False,
                evaluation_result={},
                errors=[str(e)]
            )
    
    async def acknowledge_incident(
        self,
        incident_id: str,
        acknowledged_by: str,
        db: AsyncSession
    ) -> bool:
        """Acknowledge an alert incident."""
        try:
            # TODO: Update incident in database
            self.logger.log_alert_acknowledged(
                incident_id=incident_id,
                acknowledged_by=acknowledged_by
            )
            return True
            
        except Exception as e:
            self.logger.log_error("acknowledge_incident", str(e))
            return False
    
    async def resolve_incident(
        self,
        incident_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None,
        db: AsyncSession = None
    ) -> bool:
        """Resolve an alert incident."""
        try:
            # TODO: Update incident in database
            # Calculate resolution time
            resolution_time = 15.5  # Mock resolution time in minutes
            
            self.logger.log_alert_resolved(
                incident_id=incident_id,
                resolved_by=resolved_by,
                resolution_time=resolution_time
            )
            return True
            
        except Exception as e:
            self.logger.log_error("resolve_incident", str(e))
            return False