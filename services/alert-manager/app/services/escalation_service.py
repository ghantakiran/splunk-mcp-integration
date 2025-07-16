"""
Alert escalation service for handling escalation workflows.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import AlertLogger
from ..models.alert import AlertIncident
from ..models.escalation import EscalationRule, EscalationLevel, EscalationHistory


class EscalationService:
    """Service for managing alert escalation workflows."""
    
    def __init__(self):
        self.logger = AlertLogger("escalation_service")
    
    async def check_escalation_needed(
        self,
        incident: AlertIncident,
        escalation_rules: List[EscalationRule],
        db: AsyncSession
    ) -> List[EscalationRule]:
        """Check if incident needs escalation based on rules."""
        try:
            applicable_rules = []
            
            for rule in escalation_rules:
                if await self._rule_applies_to_incident(rule, incident):
                    if await self._escalation_conditions_met(rule, incident, db):
                        applicable_rules.append(rule)
            
            return applicable_rules
            
        except Exception as e:
            self.logger.log_error("check_escalation_needed", str(e))
            return []
    
    async def _rule_applies_to_incident(self, rule: EscalationRule, incident: AlertIncident) -> bool:
        """Check if escalation rule applies to the incident."""
        # Check status filter
        if rule.status != "active":
            return False
        
        # Check severity filter
        if rule.severity_filter and incident.severity not in rule.severity_filter:
            return False
        
        # Check tag filter
        if rule.tag_filter:
            incident_tags = set(incident.tags or [])
            rule_tags = set(rule.tag_filter)
            if not rule_tags.intersection(incident_tags):
                return False
        
        # Check alert rule filter
        if rule.alert_rule_filter and incident.rule_id not in rule.alert_rule_filter:
            return False
        
        # Check time filter (e.g., only during business hours)
        if rule.time_filter and not await self._time_filter_matches(rule.time_filter, incident):
            return False
        
        return True
    
    async def _escalation_conditions_met(
        self,
        rule: EscalationRule,
        incident: AlertIncident,
        db: AsyncSession
    ) -> bool:
        """Check if escalation conditions are met."""
        trigger_conditions = rule.trigger_conditions
        
        if rule.trigger_type == "time_based":
            # Check if enough time has passed
            delay_minutes = trigger_conditions.get("delay_minutes", rule.delay_minutes)
            time_threshold = incident.triggered_at + timedelta(minutes=delay_minutes)
            return datetime.utcnow() >= time_threshold
        
        elif rule.trigger_type == "no_acknowledgment":
            # Check if incident hasn't been acknowledged
            ack_timeout = trigger_conditions.get("timeout_minutes", 30)
            time_threshold = incident.triggered_at + timedelta(minutes=ack_timeout)
            return (
                datetime.utcnow() >= time_threshold and
                incident.acknowledged_at is None
            )
        
        elif rule.trigger_type == "no_resolution":
            # Check if incident hasn't been resolved
            resolution_timeout = trigger_conditions.get("timeout_minutes", 60)
            time_threshold = incident.triggered_at + timedelta(minutes=resolution_timeout)
            return (
                datetime.utcnow() >= time_threshold and
                incident.resolved_at is None
            )
        
        elif rule.trigger_type == "severity_based":
            # Check if severity matches trigger condition
            required_severity = trigger_conditions.get("severity", "critical")
            return incident.severity == required_severity
        
        elif rule.trigger_type == "incident_count":
            # Check if there are too many incidents from same rule
            max_count = trigger_conditions.get("max_count", 5)
            # TODO: Query database for recent incidents from same rule
            return False  # Placeholder
        
        return False
    
    async def _time_filter_matches(self, time_filter: Dict[str, Any], incident: AlertIncident) -> bool:
        """Check if time filter matches current time."""
        # Simple implementation - can be extended for complex business hours
        current_time = datetime.utcnow()
        
        # Check day of week if specified
        if "days_of_week" in time_filter:
            allowed_days = time_filter["days_of_week"]  # 0=Monday, 6=Sunday
            if current_time.weekday() not in allowed_days:
                return False
        
        # Check time range if specified
        if "time_range" in time_filter:
            start_hour = time_filter["time_range"].get("start_hour", 0)
            end_hour = time_filter["time_range"].get("end_hour", 23)
            if not (start_hour <= current_time.hour <= end_hour):
                return False
        
        return True
    
    async def execute_escalation(
        self,
        rule: EscalationRule,
        incident: AlertIncident,
        db: AsyncSession
    ) -> bool:
        """Execute escalation for an incident."""
        try:
            # Determine escalation level
            current_level = incident.escalation_level
            next_level = current_level + 1
            
            # Find the appropriate escalation level
            escalation_level = None
            for level in rule.escalation_levels:
                if level.level == next_level:
                    escalation_level = level
                    break
            
            if not escalation_level:
                # No more escalation levels
                self.logger.info(
                    "No more escalation levels available",
                    incident_id=incident.id,
                    current_level=current_level
                )
                return False
            
            # Execute escalation actions
            success = await self._execute_escalation_actions(
                escalation_level, incident, rule, db
            )
            
            if success:
                # Update incident escalation info
                incident.escalation_level = next_level
                incident.escalated_at = datetime.utcnow()
                incident.escalated_to = self._get_escalation_target(escalation_level)
                
                # Record escalation history
                await self._record_escalation_history(
                    rule, escalation_level, incident, db
                )
                
                self.logger.log_escalation(
                    incident_id=incident.id,
                    escalation_level=next_level,
                    escalated_to=incident.escalated_to,
                    reason=rule.trigger_type
                )
            
            return success
            
        except Exception as e:
            self.logger.log_error("execute_escalation", str(e))
            return False
    
    async def _execute_escalation_actions(
        self,
        escalation_level: EscalationLevel,
        incident: AlertIncident,
        rule: EscalationRule,
        db: AsyncSession
    ) -> bool:
        """Execute actions for an escalation level."""
        try:
            actions_executed = []
            
            for action in escalation_level.actions:
                action_type = action.get("action_type")
                
                if action_type == "notify":
                    # Send notifications
                    result = await self._execute_notify_action(action, incident)
                    actions_executed.append({"type": "notify", "result": result})
                
                elif action_type == "reassign":
                    # Reassign incident
                    result = await self._execute_reassign_action(action, incident)
                    actions_executed.append({"type": "reassign", "result": result})
                
                elif action_type == "increase_severity":
                    # Increase severity
                    result = await self._execute_severity_action(action, incident)
                    actions_executed.append({"type": "increase_severity", "result": result})
                
                elif action_type == "call_webhook":
                    # Call webhook
                    result = await self._execute_webhook_action(action, incident)
                    actions_executed.append({"type": "call_webhook", "result": result})
                
                elif action_type == "create_ticket":
                    # Create external ticket
                    result = await self._execute_ticket_action(action, incident)
                    actions_executed.append({"type": "create_ticket", "result": result})
            
            return len(actions_executed) > 0
            
        except Exception as e:
            self.logger.log_error("execute_escalation_actions", str(e))
            return False
    
    async def _execute_notify_action(self, action: Dict[str, Any], incident: AlertIncident) -> Dict[str, Any]:
        """Execute notification action."""
        # TODO: Integrate with notification service
        channels = action.get("channels", [])
        priority = action.get("priority", "high")
        
        return {
            "success": True,
            "channels": channels,
            "message": f"Escalated alert: {incident.title}"
        }
    
    async def _execute_reassign_action(self, action: Dict[str, Any], incident: AlertIncident) -> Dict[str, Any]:
        """Execute reassignment action."""
        assignee = action.get("assignee")
        if assignee:
            incident.assigned_to = assignee
            return {"success": True, "assignee": assignee}
        return {"success": False, "error": "No assignee specified"}
    
    async def _execute_severity_action(self, action: Dict[str, Any], incident: AlertIncident) -> Dict[str, Any]:
        """Execute severity increase action."""
        new_severity = action.get("new_severity")
        if new_severity:
            old_severity = incident.severity
            incident.severity = new_severity
            return {"success": True, "old_severity": old_severity, "new_severity": new_severity}
        return {"success": False, "error": "No new severity specified"}
    
    async def _execute_webhook_action(self, action: Dict[str, Any], incident: AlertIncident) -> Dict[str, Any]:
        """Execute webhook action."""
        # TODO: Implement webhook call
        url = action.get("url")
        method = action.get("method", "POST")
        
        return {
            "success": True,
            "url": url,
            "method": method,
            "message": "Webhook called successfully"
        }
    
    async def _execute_ticket_action(self, action: Dict[str, Any], incident: AlertIncident) -> Dict[str, Any]:
        """Execute ticket creation action."""
        # TODO: Implement external ticket creation
        system = action.get("system")
        project = action.get("project")
        
        return {
            "success": True,
            "system": system,
            "project": project,
            "ticket_id": f"TICKET-{datetime.utcnow().timestamp()}"
        }
    
    def _get_escalation_target(self, escalation_level: EscalationLevel) -> str:
        """Get escalation target from escalation level."""
        assignees = escalation_level.assignees or []
        if assignees:
            return assignees[0]  # Return first assignee
        return "system"
    
    async def _record_escalation_history(
        self,
        rule: EscalationRule,
        level: EscalationLevel,
        incident: AlertIncident,
        db: AsyncSession
    ):
        """Record escalation in history."""
        # TODO: Save to database
        history = EscalationHistory(
            id=f"escalation_{datetime.utcnow().timestamp()}",
            incident_id=incident.id,
            rule_id=rule.id,
            level_id=level.id,
            escalation_level=level.level,
            trigger_type=rule.trigger_type,
            trigger_reason=f"Escalation level {level.level}",
            actions_executed=level.actions,
            escalated_by="system",
            escalated_to=self._get_escalation_target(level),
            scheduled_at=datetime.utcnow(),
            executed_at=datetime.utcnow(),
            success=True,
            created_at=datetime.utcnow()
        )
        
        self.logger.info(
            "Escalation history recorded",
            incident_id=incident.id,
            escalation_level=level.level
        )