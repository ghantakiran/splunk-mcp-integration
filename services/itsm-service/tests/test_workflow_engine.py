"""
Tests for ITSM Workflow Engine functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.workflow_engine import (
    WorkflowEngine, WorkflowStep, WorkflowExecution, StepType, WorkflowStatus
)
from app.models.itsm_models import ITSMWorkflow


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    return ITSMWorkflow(
        id="workflow-123",
        user_id="user-123",
        name="Test Workflow",
        description="A test workflow for automation",
        trigger_type="manual",
        trigger_config={},
        steps=[
            {
                "id": "step1",
                "name": "Create Incident",
                "type": "create_ticket",
                "config": {
                    "provider": "servicenow",
                    "table": "incident",
                    "ticket_data": {
                        "title": "Test Incident ${priority}",
                        "description": "Automated incident creation",
                        "priority": "${priority}"
                    }
                },
                "on_success": {
                    "set_variables": {
                        "incident_id": {"from_result": "sys_id"}
                    }
                }
            },
            {
                "id": "step2",
                "name": "Send Notification",
                "type": "send_notification",
                "config": {
                    "message": "Incident ${incident_id} created",
                    "recipients": ["admin@example.com"]
                },
                "conditions": [
                    {
                        "type": "previous_step_success",
                        "step_id": "step1"
                    }
                ]
            }
        ],
        variables={"priority": "high"},
        is_active=True
    )


@pytest.fixture
def workflow_engine():
    """Create a workflow engine instance."""
    return WorkflowEngine()


@pytest.fixture
def mock_servicenow_manager():
    """Create a mock ServiceNow manager."""
    manager = AsyncMock()
    manager.create_ticket.return_value = {
        "sys_id": "incident-123",
        "number": "INC0001234",
        "short_description": "Test Incident high"
    }
    manager.update_ticket.return_value = {
        "sys_id": "incident-123",
        "state": "2",
        "short_description": "Updated Incident"
    }
    manager.search_tickets.return_value = [
        {"sys_id": "inc1", "number": "INC001"},
        {"sys_id": "inc2", "number": "INC002"}
    ]
    return manager


@pytest.fixture
def mock_jira_manager():
    """Create a mock Jira manager."""
    manager = AsyncMock()
    manager.create_ticket.return_value = {
        "key": "TEST-123",
        "id": "10001",
        "summary": "Test Issue high"
    }
    manager.update_ticket.return_value = {
        "key": "TEST-123",
        "summary": "Updated Issue"
    }
    manager.search_tickets.return_value = [
        {"key": "TEST-123", "summary": "Issue 1"},
        {"key": "TEST-124", "summary": "Issue 2"}
    ]
    return manager


class TestWorkflowStep:
    """Test WorkflowStep class."""
    
    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        step_config = {
            "id": "test-step",
            "name": "Test Step",
            "type": "create_ticket",
            "config": {"provider": "servicenow"},
            "timeout_seconds": 120,
            "retry_attempts": 2
        }
        
        step = WorkflowStep(step_config)
        
        assert step.id == "test-step"
        assert step.name == "Test Step"
        assert step.type == StepType.CREATE_TICKET
        assert step.config == {"provider": "servicenow"}
        assert step.timeout_seconds == 120
        assert step.retry_attempts == 2
        assert step.retry_delay_seconds == 60  # default
    
    def test_workflow_step_defaults(self):
        """Test workflow step with default values."""
        step_config = {
            "id": "minimal-step",
            "type": "wait"
        }
        
        step = WorkflowStep(step_config)
        
        assert step.id == "minimal-step"
        assert step.name is None
        assert step.type == StepType.WAIT
        assert step.config == {}
        assert step.timeout_seconds == 300  # default
        assert step.retry_attempts == 3  # default


class TestWorkflowExecution:
    """Test WorkflowExecution class."""
    
    def test_workflow_execution_creation(self, sample_workflow):
        """Test creating a workflow execution."""
        trigger_data = {"source": "manual", "user": "admin"}
        
        execution = WorkflowExecution(sample_workflow, trigger_data)
        
        assert execution.workflow == sample_workflow
        assert execution.trigger_data == trigger_data
        assert execution.status == WorkflowStatus.PENDING
        assert execution.variables == {"priority": "high"}
        assert execution.current_step_index == 0
        assert len(execution.steps) == 2
        assert execution.execution_id.startswith("exec_")
    
    def test_workflow_execution_without_trigger_data(self, sample_workflow):
        """Test creating execution without trigger data."""
        execution = WorkflowExecution(sample_workflow)
        
        assert execution.trigger_data == {}
        assert execution.variables == {"priority": "high"}


class TestWorkflowEngine:
    """Test WorkflowEngine functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(
        self, workflow_engine, sample_workflow, 
        mock_servicenow_manager, mock_jira_manager
    ):
        """Test successful workflow execution."""
        execution = await workflow_engine.execute_workflow(
            sample_workflow,
            trigger_data={"source": "test"},
            servicenow_manager=mock_servicenow_manager,
            jira_manager=mock_jira_manager
        )
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert len(execution.step_results) == 2
        
        # Check first step (create ticket)
        first_result = execution.step_results[0]
        assert first_result["step_id"] == "step1"
        assert first_result["status"] == "success"
        assert "incident-123" in str(first_result["result"])
        
        # Check second step (send notification)
        second_result = execution.step_results[1]
        assert second_result["step_id"] == "step2"
        assert second_result["status"] == "success"
        
        # Verify ServiceNow manager was called
        mock_servicenow_manager.create_ticket.assert_called_once()
        call_args = mock_servicenow_manager.create_ticket.call_args[0]
        assert call_args[0]["title"] == "Test Incident high"  # Variable substituted
    
    @pytest.mark.asyncio
    async def test_execute_workflow_step_failure(
        self, workflow_engine, sample_workflow, mock_servicenow_manager
    ):
        """Test workflow execution with step failure."""
        # Make the first step fail
        mock_servicenow_manager.create_ticket.side_effect = Exception("ServiceNow error")
        
        execution = await workflow_engine.execute_workflow(
            sample_workflow,
            servicenow_manager=mock_servicenow_manager
        )
        
        assert execution.status == WorkflowStatus.FAILED
        assert execution.error_message is not None
        assert "ServiceNow error" in execution.error_message
        assert len(execution.step_results) == 1
        assert execution.step_results[0]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_step_conditions_not_met(self, workflow_engine):
        """Test workflow execution when step conditions are not met."""
        # Create a workflow where second step requires first step to succeed
        workflow = ITSMWorkflow(
            id="conditional-workflow",
            user_id="user-123",
            name="Conditional Workflow",
            steps=[
                {
                    "id": "step1",
                    "type": "wait",
                    "config": {"seconds": 0.1}
                },
                {
                    "id": "step2",
                    "type": "wait", 
                    "config": {"seconds": 0.1},
                    "conditions": [
                        {
                            "type": "variable_equals",
                            "variable": "skip_step",
                            "value": "false"
                        }
                    ]
                }
            ],
            variables={"skip_step": "true"}  # This will cause step2 to be skipped
        )
        
        execution = await workflow_engine.execute_workflow(workflow)
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.step_results) == 1  # Only step1 executed
        assert execution.step_results[0]["step_id"] == "step1"
    
    @pytest.mark.asyncio
    async def test_variable_substitution(self, workflow_engine):
        """Test variable substitution in step configurations."""
        context = {
            "variables": {"user_name": "john", "priority": "high"},
            "trigger_data": {"incident_type": "critical"}
        }
        
        # Test string substitution
        template = "Hello ${user_name}, priority is ${priority}, type: $trigger.incident_type"
        result = workflow_engine._substitute_variables(template, context)
        assert result == "Hello john, priority is high, type: critical"
        
        # Test dict substitution
        template_dict = {
            "title": "Issue for ${user_name}",
            "priority": "${priority}",
            "metadata": {
                "type": "$trigger.incident_type"
            }
        }
        result_dict = workflow_engine._substitute_variables(template_dict, context)
        assert result_dict["title"] == "Issue for john"
        assert result_dict["priority"] == "high"
        assert result_dict["metadata"]["type"] == "critical"
        
        # Test list substitution
        template_list = ["${user_name}", "${priority}", "$trigger.incident_type"]
        result_list = workflow_engine._substitute_variables(template_list, context)
        assert result_list == ["john", "high", "critical"]
    
    @pytest.mark.asyncio
    async def test_create_ticket_step_servicenow(
        self, workflow_engine, mock_servicenow_manager
    ):
        """Test create ticket step with ServiceNow."""
        step = WorkflowStep({
            "id": "create-step",
            "type": "create_ticket",
            "config": {
                "provider": "servicenow",
                "table": "incident",
                "ticket_data": {
                    "title": "Test ${priority}",
                    "priority": "${priority}"
                }
            }
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "servicenow_manager": mock_servicenow_manager,
            "variables": {"priority": "high"},
            "trigger_data": {}
        }
        context["execution"].workflow.user_id = "user-123"
        
        result = await workflow_engine._handle_create_ticket(context)
        
        assert result["sys_id"] == "incident-123"
        mock_servicenow_manager.create_ticket.assert_called_once()
        call_args = mock_servicenow_manager.create_ticket.call_args[0]
        assert call_args[0]["title"] == "Test high"
    
    @pytest.mark.asyncio
    async def test_create_ticket_step_jira(
        self, workflow_engine, mock_jira_manager
    ):
        """Test create ticket step with Jira."""
        step = WorkflowStep({
            "id": "create-step",
            "type": "create_ticket",
            "config": {
                "provider": "jira",
                "project_key": "TEST",
                "issue_type": "Bug",
                "ticket_data": {
                    "title": "Bug ${severity}",
                    "priority": "${severity}"
                }
            }
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "jira_manager": mock_jira_manager,
            "variables": {"severity": "critical"},
            "trigger_data": {}
        }
        context["execution"].workflow.user_id = "user-123"
        
        result = await workflow_engine._handle_create_ticket(context)
        
        assert result["key"] == "TEST-123"
        mock_jira_manager.create_ticket.assert_called_once()
        call_args = mock_jira_manager.create_ticket.call_args[0]
        assert call_args[0]["title"] == "Bug critical"
    
    @pytest.mark.asyncio
    async def test_update_ticket_step(
        self, workflow_engine, mock_servicenow_manager
    ):
        """Test update ticket step."""
        step = WorkflowStep({
            "id": "update-step",
            "type": "update_ticket",
            "config": {
                "provider": "servicenow",
                "ticket_id": "${ticket_id}",
                "ticket_data": {
                    "status": "in_progress",
                    "comments": "Updated by workflow"
                }
            }
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "servicenow_manager": mock_servicenow_manager,
            "variables": {"ticket_id": "INC123"},
            "trigger_data": {}
        }
        
        result = await workflow_engine._handle_update_ticket(context)
        
        assert result["sys_id"] == "incident-123"
        mock_servicenow_manager.update_ticket.assert_called_once()
        call_args = mock_servicenow_manager.update_ticket.call_args
        assert call_args[0][0] == "INC123"  # ticket_id
        assert call_args[0][1]["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_search_tickets_step(
        self, workflow_engine, mock_servicenow_manager
    ):
        """Test search tickets step."""
        step = WorkflowStep({
            "id": "search-step",
            "type": "search_tickets",
            "config": {
                "provider": "servicenow",
                "table": "incident",
                "query": {
                    "status": "new",
                    "priority": "${priority}"
                },
                "limit": 50
            }
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "servicenow_manager": mock_servicenow_manager,
            "variables": {"priority": "high"},
            "trigger_data": {}
        }
        
        result = await workflow_engine._handle_search_tickets(context)
        
        assert len(result) == 2
        assert result[0]["sys_id"] == "inc1"
        mock_servicenow_manager.search_tickets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_step(self, workflow_engine):
        """Test send notification step."""
        step = WorkflowStep({
            "id": "notify-step",
            "type": "send_notification",
            "config": {
                "message": "Ticket ${ticket_id} needs attention",
                "recipients": ["admin@example.com", "${assignee_email}"]
            }
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "variables": {"ticket_id": "INC123", "assignee_email": "user@example.com"},
            "trigger_data": {}
        }
        context["execution"].workflow.id = "workflow-123"
        context["execution"].execution_id = "exec-123"
        
        result = await workflow_engine._handle_send_notification(context)
        
        assert result["sent"] is True
        assert result["message"] == "Ticket INC123 needs attention"
        assert "user@example.com" in result["recipients"]
    
    @pytest.mark.asyncio
    async def test_wait_step(self, workflow_engine):
        """Test wait step."""
        step = WorkflowStep({
            "id": "wait-step",
            "type": "wait",
            "config": {"seconds": 0.1}  # Short wait for testing
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "variables": {},
            "trigger_data": {}
        }
        
        start_time = asyncio.get_event_loop().time()
        result = await workflow_engine._handle_wait(context)
        end_time = asyncio.get_event_loop().time()
        
        assert result["waited_seconds"] == 0.1
        assert end_time - start_time >= 0.1
    
    @pytest.mark.asyncio
    async def test_condition_evaluation(self, workflow_engine):
        """Test condition evaluation."""
        context = {
            "variables": {"priority": "high", "count": 10, "status": "active"}
        }
        
        # Test equals condition
        condition = {"type": "variable_equals", "variable": "priority", "value": "high"}
        result = await workflow_engine._evaluate_condition(condition, context)
        assert result is True
        
        condition = {"type": "variable_equals", "variable": "priority", "value": "low"}
        result = await workflow_engine._evaluate_condition(condition, context)
        assert result is False
        
        # Test greater than condition
        condition = {"type": "variable_greater_than", "variable": "count", "value": 5}
        result = await workflow_engine._evaluate_condition(condition, context)
        assert result is True
        
        condition = {"type": "variable_greater_than", "variable": "count", "value": 15}
        result = await workflow_engine._evaluate_condition(condition, context)
        assert result is False
        
        # Test contains condition
        condition = {"type": "variable_contains", "variable": "status", "value": "act"}
        result = await workflow_engine._evaluate_condition(condition, context)
        assert result is True
        
        condition = {"type": "variable_contains", "variable": "status", "value": "inactive"}
        result = await workflow_engine._evaluate_condition(condition, context)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_result_handling(self, workflow_engine):
        """Test handling of step results and variable updates."""
        step = WorkflowStep({
            "id": "test-step",
            "type": "create_ticket",
            "on_success": {
                "set_variables": {
                    "new_ticket_id": {"from_result": "sys_id"},
                    "static_value": {"static_value": "completed"}
                }
            }
        })
        
        execution = MagicMock()
        execution.variables = {"existing_var": "value"}
        
        result = {"sys_id": "INC123", "number": "INC0001234"}
        
        await workflow_engine._handle_step_result(step, result, execution)
        
        assert execution.variables["new_ticket_id"] == "INC123"
        assert execution.variables["static_value"] == "completed"
        assert execution.variables["existing_var"] == "value"  # Preserved
    
    @pytest.mark.asyncio
    async def test_step_timeout_handling(self, workflow_engine, sample_workflow):
        """Test step timeout handling."""
        # Create a step that will timeout
        long_running_workflow = ITSMWorkflow(
            id="timeout-workflow",
            user_id="user-123",
            name="Timeout Workflow",
            steps=[
                {
                    "id": "timeout-step",
                    "type": "wait",
                    "config": {"seconds": 2},  # Long wait
                    "timeout_seconds": 0.1  # Short timeout
                }
            ],
            variables={}
        )
        
        execution = await workflow_engine.execute_workflow(long_running_workflow)
        
        assert execution.status == WorkflowStatus.FAILED
        assert len(execution.step_results) == 1
        assert execution.step_results[0]["status"] == "timeout"
        assert "timeout" in execution.step_results[0]["error"]
    
    @pytest.mark.asyncio
    async def test_unsupported_step_type(self, workflow_engine):
        """Test handling of unsupported step types."""
        step = WorkflowStep({
            "id": "unknown-step",
            "type": "unknown_type"  # This will cause an error
        })
        
        context = {
            "step": step,
            "execution": MagicMock(),
            "variables": {},
            "trigger_data": {}
        }
        
        with pytest.raises(ValueError, match="Unsupported step type"):
            await workflow_engine._execute_step(step, context["execution"])
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, workflow_engine):
        """Test cancelling a workflow execution."""
        execution = MagicMock()
        execution.workflow.id = "workflow-123"
        execution_id = "exec-123"
        
        # Add execution to running executions
        workflow_engine.running_executions[execution_id] = execution
        
        result = await workflow_engine.cancel_execution(execution_id)
        
        assert result is True
        assert execution.status == WorkflowStatus.CANCELLED
        assert execution.completed_at is not None
        assert execution_id not in workflow_engine.running_executions
        
        # Test cancelling non-existent execution
        result = await workflow_engine.cancel_execution("non-existent")
        assert result is False
    
    def test_get_execution_status(self, workflow_engine, sample_workflow):
        """Test getting execution status."""
        execution = WorkflowExecution(sample_workflow)
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow()
        execution_id = execution.execution_id
        
        workflow_engine.running_executions[execution_id] = execution
        
        status = workflow_engine.get_execution_status(execution_id)
        
        assert status is not None
        assert status["execution_id"] == execution_id
        assert status["workflow_id"] == "workflow-123"
        assert status["status"] == "running"
        assert status["current_step"] == 0
        assert status["total_steps"] == 2
        assert status["started_at"] is not None
        
        # Test getting status for non-existent execution
        status = workflow_engine.get_execution_status("non-existent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_check_conditions_previous_step_success(self, workflow_engine):
        """Test checking conditions for previous step success."""
        step = WorkflowStep({
            "id": "conditional-step",
            "type": "wait",
            "conditions": [
                {
                    "type": "previous_step_success",
                    "step_id": "step1"
                }
            ]
        })
        
        execution = MagicMock()
        execution.step_results = [
            {
                "step_id": "step1",
                "status": "success",
                "result": {"success": True}
            }
        ]
        
        # Should pass when previous step succeeded
        result = await workflow_engine._check_conditions(step, execution)
        assert result is True
        
        # Should fail when previous step failed
        execution.step_results[0]["status"] = "error"
        result = await workflow_engine._check_conditions(step, execution)
        assert result is False
        
        # Should fail when previous step not found
        execution.step_results = []
        result = await workflow_engine._check_conditions(step, execution)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_conditions_variable_exists(self, workflow_engine):
        """Test checking conditions for variable existence."""
        step = WorkflowStep({
            "id": "conditional-step",
            "type": "wait",
            "conditions": [
                {
                    "type": "variable_exists",
                    "variable": "required_var"
                }
            ]
        })
        
        execution = MagicMock()
        execution.variables = {"required_var": "value", "other_var": "other"}
        
        # Should pass when variable exists
        result = await workflow_engine._check_conditions(step, execution)
        assert result is True
        
        # Should fail when variable doesn't exist
        execution.variables = {"other_var": "other"}
        result = await workflow_engine._check_conditions(step, execution)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])