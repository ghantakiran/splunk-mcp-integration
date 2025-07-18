"""
Workflow engine for ITSM Service automation.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum

from ..core.logging import get_logger, add_workflow_context, add_performance_context
from ..models.itsm_models import ITSMWorkflow, WorkflowStatus
from .servicenow_manager import ServiceNowManager
from .jira_manager import JiraManager

logger = get_logger(__name__)


class StepType(Enum):
    """Workflow step types."""
    CREATE_TICKET = "create_ticket"
    UPDATE_TICKET = "update_ticket"
    SEARCH_TICKETS = "search_tickets"
    SEND_NOTIFICATION = "send_notification"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    API_CALL = "api_call"
    SCRIPT = "script"
    APPROVAL = "approval"


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class WorkflowStep:
    """Represents a single workflow step."""
    
    def __init__(self, step_config: Dict[str, Any]):
        self.id = step_config.get("id")
        self.name = step_config.get("name")
        self.type = StepType(step_config.get("type"))
        self.config = step_config.get("config", {})
        self.conditions = step_config.get("conditions", [])
        self.on_success = step_config.get("on_success", {})
        self.on_failure = step_config.get("on_failure", {})
        self.timeout_seconds = step_config.get("timeout_seconds", 300)
        self.retry_attempts = step_config.get("retry_attempts", 3)
        self.retry_delay_seconds = step_config.get("retry_delay_seconds", 60)


class WorkflowExecution:
    """Represents a workflow execution instance."""
    
    def __init__(self, workflow: ITSMWorkflow, trigger_data: Dict[str, Any] = None):
        self.workflow = workflow
        self.execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.status = WorkflowStatus.PENDING
        self.trigger_data = trigger_data or {}
        self.variables = dict(workflow.variables)
        self.current_step_index = 0
        self.step_results = []
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.steps = [WorkflowStep(step) for step in workflow.steps]


class WorkflowEngine:
    """Workflow automation engine for ITSM operations."""
    
    def __init__(self):
        self.running_executions: Dict[str, WorkflowExecution] = {}
        self.step_handlers: Dict[StepType, Callable] = {
            StepType.CREATE_TICKET: self._handle_create_ticket,
            StepType.UPDATE_TICKET: self._handle_update_ticket,
            StepType.SEARCH_TICKETS: self._handle_search_tickets,
            StepType.SEND_NOTIFICATION: self._handle_send_notification,
            StepType.WAIT: self._handle_wait,
            StepType.CONDITION: self._handle_condition,
            StepType.LOOP: self._handle_loop,
            StepType.API_CALL: self._handle_api_call,
            StepType.SCRIPT: self._handle_script,
            StepType.APPROVAL: self._handle_approval,
        }
    
    async def execute_workflow(
        self,
        workflow: ITSMWorkflow,
        trigger_data: Dict[str, Any] = None,
        servicenow_manager: ServiceNowManager = None,
        jira_manager: JiraManager = None
    ) -> WorkflowExecution:
        """Execute a workflow."""
        execution = WorkflowExecution(workflow, trigger_data)
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow()
        
        self.running_executions[execution.execution_id] = execution
        
        logger.info(
            "Workflow execution started",
            **add_workflow_context(
                workflow.id,
                "start",
                "execution",
                execution.execution_id
            )
        )
        
        try:
            await self._execute_steps(
                execution,
                servicenow_manager,
                jira_manager
            )
            
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            
            logger.info(
                "Workflow execution completed successfully",
                **add_workflow_context(
                    workflow.id,
                    "completed",
                    "execution",
                    execution.execution_id
                )
            )
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            logger.error(
                "Workflow execution failed",
                error=str(e),
                **add_workflow_context(
                    workflow.id,
                    "failed",
                    "execution",
                    execution.execution_id
                )
            )
        
        finally:
            # Clean up
            if execution.execution_id in self.running_executions:
                del self.running_executions[execution.execution_id]
        
        return execution
    
    async def _execute_steps(
        self,
        execution: WorkflowExecution,
        servicenow_manager: ServiceNowManager = None,
        jira_manager: JiraManager = None
    ) -> None:
        """Execute workflow steps sequentially."""
        
        while execution.current_step_index < len(execution.steps):
            step = execution.steps[execution.current_step_index]
            
            logger.info(
                "Executing workflow step",
                **add_workflow_context(
                    execution.workflow.id,
                    step.id,
                    step.type.value,
                    execution.execution_id
                )
            )
            
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Check step conditions
                if not await self._check_conditions(step, execution):
                    logger.info(
                        "Step conditions not met, skipping",
                        **add_workflow_context(
                            execution.workflow.id,
                            step.id,
                            step.type.value,
                            execution.execution_id
                        )
                    )
                    execution.current_step_index += 1
                    continue
                
                # Execute step with timeout
                step_result = await asyncio.wait_for(
                    self._execute_step(
                        step,
                        execution,
                        servicenow_manager,
                        jira_manager
                    ),
                    timeout=step.timeout_seconds
                )
                
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                execution.step_results.append({
                    "step_id": step.id,
                    "step_type": step.type.value,
                    "status": "success",
                    "result": step_result,
                    "duration_ms": duration_ms,
                    "executed_at": datetime.utcnow().isoformat()
                })
                
                logger.info(
                    "Workflow step completed successfully",
                    **add_performance_context("workflow_step", duration_ms),
                    **add_workflow_context(
                        execution.workflow.id,
                        step.id,
                        step.type.value,
                        execution.execution_id
                    )
                )
                
                # Handle step result
                await self._handle_step_result(step, step_result, execution)
                
            except asyncio.TimeoutError:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                error_msg = f"Step timeout after {step.timeout_seconds} seconds"
                
                execution.step_results.append({
                    "step_id": step.id,
                    "step_type": step.type.value,
                    "status": "timeout",
                    "error": error_msg,
                    "duration_ms": duration_ms,
                    "executed_at": datetime.utcnow().isoformat()
                })
                
                logger.error(
                    "Workflow step timeout",
                    error=error_msg,
                    **add_performance_context("workflow_step", duration_ms, False, "timeout"),
                    **add_workflow_context(
                        execution.workflow.id,
                        step.id,
                        step.type.value,
                        execution.execution_id
                    )
                )
                
                await self._handle_step_failure(step, error_msg, execution)
                
            except Exception as e:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                error_msg = str(e)
                
                execution.step_results.append({
                    "step_id": step.id,
                    "step_type": step.type.value,
                    "status": "error",
                    "error": error_msg,
                    "duration_ms": duration_ms,
                    "executed_at": datetime.utcnow().isoformat()
                })
                
                logger.error(
                    "Workflow step failed",
                    error=error_msg,
                    **add_performance_context("workflow_step", duration_ms, False, "error"),
                    **add_workflow_context(
                        execution.workflow.id,
                        step.id,
                        step.type.value,
                        execution.execution_id
                    )
                )
                
                await self._handle_step_failure(step, error_msg, execution)
            
            execution.current_step_index += 1
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        servicenow_manager: ServiceNowManager = None,
        jira_manager: JiraManager = None
    ) -> Any:
        """Execute a single workflow step."""
        
        # Get step handler
        handler = self.step_handlers.get(step.type)
        if not handler:
            raise ValueError(f"Unsupported step type: {step.type}")
        
        # Prepare step context
        context = {
            "execution": execution,
            "step": step,
            "servicenow_manager": servicenow_manager,
            "jira_manager": jira_manager,
            "variables": execution.variables,
            "trigger_data": execution.trigger_data
        }
        
        # Execute step
        return await handler(context)
    
    async def _check_conditions(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution
    ) -> bool:
        """Check if step conditions are met."""
        
        if not step.conditions:
            return True
        
        for condition in step.conditions:
            condition_type = condition.get("type")
            
            if condition_type == "variable_equals":
                variable_name = condition.get("variable")
                expected_value = condition.get("value")
                actual_value = execution.variables.get(variable_name)
                
                if actual_value != expected_value:
                    return False
            
            elif condition_type == "variable_exists":
                variable_name = condition.get("variable")
                if variable_name not in execution.variables:
                    return False
            
            elif condition_type == "previous_step_success":
                step_id = condition.get("step_id")
                step_found = False
                
                for result in execution.step_results:
                    if result["step_id"] == step_id:
                        step_found = True
                        if result["status"] != "success":
                            return False
                        break
                
                if not step_found:
                    return False
        
        return True
    
    async def _handle_step_result(
        self,
        step: WorkflowStep,
        result: Any,
        execution: WorkflowExecution
    ) -> None:
        """Handle step execution result."""
        
        # Update variables from step result
        if step.on_success.get("set_variables"):
            for var_name, var_config in step.on_success["set_variables"].items():
                if var_config.get("from_result"):
                    # Extract value from result
                    result_path = var_config["from_result"].split(".")
                    value = result
                    for path_part in result_path:
                        if isinstance(value, dict) and path_part in value:
                            value = value[path_part]
                        else:
                            value = None
                            break
                    
                    if value is not None:
                        execution.variables[var_name] = value
                
                elif var_config.get("static_value"):
                    execution.variables[var_name] = var_config["static_value"]
        
        # Handle next step logic
        if step.on_success.get("goto_step"):
            next_step_id = step.on_success["goto_step"]
            for i, workflow_step in enumerate(execution.steps):
                if workflow_step.id == next_step_id:
                    execution.current_step_index = i - 1  # -1 because it will be incremented
                    break
    
    async def _handle_step_failure(
        self,
        step: WorkflowStep,
        error_message: str,
        execution: WorkflowExecution
    ) -> None:
        """Handle step execution failure."""
        
        if step.on_failure.get("retry") and step.retry_attempts > 0:
            # Implement retry logic
            await asyncio.sleep(step.retry_delay_seconds)
            # This would need to be implemented in the calling function
            return
        
        if step.on_failure.get("continue"):
            # Continue to next step
            return
        
        if step.on_failure.get("goto_step"):
            next_step_id = step.on_failure["goto_step"]
            for i, workflow_step in enumerate(execution.steps):
                if workflow_step.id == next_step_id:
                    execution.current_step_index = i - 1  # -1 because it will be incremented
                    return
        
        # Default: fail the workflow
        raise Exception(f"Step {step.id} failed: {error_message}")
    
    # Step handlers
    async def _handle_create_ticket(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create ticket step."""
        step = context["step"]
        config = step.config
        
        provider = config.get("provider")
        ticket_data = self._substitute_variables(config.get("ticket_data", {}), context)
        
        if provider == "servicenow":
            servicenow_manager = context["servicenow_manager"]
            if not servicenow_manager:
                raise ValueError("ServiceNow manager not available")
            
            result = await servicenow_manager.create_ticket(
                ticket_data,
                context["execution"].workflow.user_id,
                config.get("table", "incident")
            )
            return result
        
        elif provider == "jira":
            jira_manager = context["jira_manager"]
            if not jira_manager:
                raise ValueError("Jira manager not available")
            
            result = await jira_manager.create_ticket(
                ticket_data,
                context["execution"].workflow.user_id,
                config.get("project_key"),
                config.get("issue_type", "Task")
            )
            return result
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def _handle_update_ticket(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update ticket step."""
        step = context["step"]
        config = step.config
        
        provider = config.get("provider")
        ticket_id = self._substitute_variables(config.get("ticket_id"), context)
        ticket_data = self._substitute_variables(config.get("ticket_data", {}), context)
        
        if provider == "servicenow":
            servicenow_manager = context["servicenow_manager"]
            if not servicenow_manager:
                raise ValueError("ServiceNow manager not available")
            
            result = await servicenow_manager.update_ticket(
                ticket_id,
                ticket_data,
                config.get("table", "incident")
            )
            return result
        
        elif provider == "jira":
            jira_manager = context["jira_manager"]
            if not jira_manager:
                raise ValueError("Jira manager not available")
            
            result = await jira_manager.update_ticket(ticket_id, ticket_data)
            return result
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def _handle_search_tickets(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle search tickets step."""
        step = context["step"]
        config = step.config
        
        provider = config.get("provider")
        query = self._substitute_variables(config.get("query", {}), context)
        
        if provider == "servicenow":
            servicenow_manager = context["servicenow_manager"]
            if not servicenow_manager:
                raise ValueError("ServiceNow manager not available")
            
            result = await servicenow_manager.search_tickets(
                query,
                config.get("table", "incident"),
                config.get("limit", 100),
                config.get("offset", 0)
            )
            return result
        
        elif provider == "jira":
            jira_manager = context["jira_manager"]
            if not jira_manager:
                raise ValueError("Jira manager not available")
            
            result = await jira_manager.search_tickets(
                query,
                config.get("limit", 100),
                config.get("offset", 0)
            )
            return result
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def _handle_send_notification(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle send notification step."""
        step = context["step"]
        config = step.config
        
        # This would integrate with notification service
        # For now, just log the notification
        message = self._substitute_variables(config.get("message"), context)
        recipients = self._substitute_variables(config.get("recipients", []), context)
        
        logger.info(
            "Workflow notification sent",
            message=message,
            recipients=recipients,
            **add_workflow_context(
                context["execution"].workflow.id,
                step.id,
                "notification",
                context["execution"].execution_id
            )
        )
        
        return {"sent": True, "message": message, "recipients": recipients}
    
    async def _handle_wait(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle wait step."""
        step = context["step"]
        config = step.config
        
        wait_seconds = config.get("seconds", 60)
        await asyncio.sleep(wait_seconds)
        
        return {"waited_seconds": wait_seconds}
    
    async def _handle_condition(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle condition step."""
        step = context["step"]
        config = step.config
        
        condition_result = await self._evaluate_condition(config.get("condition"), context)
        
        return {"condition_result": condition_result}
    
    async def _handle_loop(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle loop step."""
        step = context["step"]
        config = step.config
        
        # This would implement loop logic
        # For now, just return a placeholder
        return {"loop_completed": True}
    
    async def _handle_api_call(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API call step."""
        step = context["step"]
        config = step.config
        
        # This would implement HTTP API calls
        # For now, just return a placeholder
        return {"api_call_completed": True}
    
    async def _handle_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle script execution step."""
        step = context["step"]
        config = step.config
        
        # This would implement script execution (Python, JavaScript, etc.)
        # For now, just return a placeholder
        return {"script_executed": True}
    
    async def _handle_approval(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle approval step."""
        step = context["step"]
        config = step.config
        
        # This would implement approval workflow
        # For now, just return a placeholder
        return {"approval_status": "approved"}
    
    def _substitute_variables(self, value: Any, context: Dict[str, Any]) -> Any:
        """Substitute variables in step configuration."""
        if isinstance(value, str):
            # Simple variable substitution
            variables = context["variables"]
            trigger_data = context["trigger_data"]
            
            for var_name, var_value in variables.items():
                value = value.replace(f"${{{var_name}}}", str(var_value))
            
            for data_name, data_value in trigger_data.items():
                value = value.replace(f"$trigger.{data_name}", str(data_value))
            
            return value
        
        elif isinstance(value, dict):
            return {k: self._substitute_variables(v, context) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._substitute_variables(item, context) for item in value]
        
        else:
            return value
    
    async def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition."""
        
        condition_type = condition.get("type")
        
        if condition_type == "variable_equals":
            variable_name = condition.get("variable")
            expected_value = condition.get("value")
            actual_value = context["variables"].get(variable_name)
            return actual_value == expected_value
        
        elif condition_type == "variable_greater_than":
            variable_name = condition.get("variable")
            threshold = condition.get("value")
            actual_value = context["variables"].get(variable_name)
            return actual_value > threshold if actual_value is not None else False
        
        elif condition_type == "variable_contains":
            variable_name = condition.get("variable")
            search_value = condition.get("value")
            actual_value = context["variables"].get(variable_name, "")
            return search_value in str(actual_value)
        
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running workflow execution."""
        if execution_id in self.running_executions:
            execution = self.running_executions[execution_id]
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            
            logger.info(
                "Workflow execution cancelled",
                **add_workflow_context(
                    execution.workflow.id,
                    "cancelled",
                    "execution",
                    execution_id
                )
            )
            
            del self.running_executions[execution_id]
            return True
        
        return False
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution."""
        if execution_id in self.running_executions:
            execution = self.running_executions[execution_id]
            return {
                "execution_id": execution_id,
                "workflow_id": execution.workflow.id,
                "status": execution.status.value,
                "current_step": execution.current_step_index,
                "total_steps": len(execution.steps),
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "step_results": execution.step_results
            }
        
        return None