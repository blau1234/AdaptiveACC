import json
from typing import Dict, List, Any
from agents.planner import Planner
from agents.executor import Executor
from agents.checker import Checker
from agents.tool_creator.tool_creator import ToolCreatorAgent
from tools.tool_registry import create_building_tool_registry
from toolregistry import ToolRegistry
from datetime import datetime
from utils.validation import validate_regulation_text, validate_plan_structure, safe_validate
from models.blackboard_models import ComplianceCheckBlackboard, BlackboardMixin
import uuid

class AgentCoordinator(BlackboardMixin):
    def __init__(self):
        super().__init__()
        
        # Initialize shared ToolRegistry directly
        self.tool_registry = create_building_tool_registry()
        
        # Initialize agents with shared tool registry
        self.planner = Planner()
        self.executor = Executor(tool_registry=self.tool_registry)
        self.checker = Checker()
        self.tool_creator = ToolCreatorAgent(tool_registry=self.tool_registry)
        
        self.communication_log = []
        self.max_feedback_rounds = 3
        
        # Initialize blackboard for the session
        self._init_blackboard()
    
    def _init_blackboard(self):
        """Initialize blackboard and set it for all agents"""
        blackboard = ComplianceCheckBlackboard()
        self.set_blackboard(blackboard)
        
        # Set blackboard for all agents
        if hasattr(self.planner, 'set_blackboard'):
            self.planner.set_blackboard(blackboard)
        if hasattr(self.executor, 'set_blackboard'):
            self.executor.set_blackboard(blackboard) 
        if hasattr(self.checker, 'set_blackboard'):
            self.checker.set_blackboard(blackboard)
        if hasattr(self.tool_creator, 'set_blackboard'):
            self.tool_creator.set_blackboard(blackboard)
    
    def set_blackboard_for_tool_creator(self, tool_creator_agent):
        """Set blackboard for ToolCreator components when needed"""
        if hasattr(self, '_blackboard') and self._blackboard:
            if hasattr(tool_creator_agent, 'set_blackboard'):
                tool_creator_agent.set_blackboard(self._blackboard)
            
            # Set blackboard for sub-components
            if hasattr(tool_creator_agent, 'requirement_agent') and hasattr(tool_creator_agent.requirement_agent, 'set_blackboard'):
                tool_creator_agent.requirement_agent.set_blackboard(self._blackboard)
            if hasattr(tool_creator_agent, 'code_generator') and hasattr(tool_creator_agent.code_generator, 'set_blackboard'):
                tool_creator_agent.code_generator.set_blackboard(self._blackboard)
    
    def _setup_session(self, regulation_text: str, ifc_file_path: str):
        """Setup session data in blackboard"""
        self.blackboard.session_id = str(uuid.uuid4())[:8]
        self.blackboard.regulation_text = regulation_text
        self.blackboard.ifc_file_path = ifc_file_path
        self.blackboard.max_feedback_rounds = self.max_feedback_rounds
        print(f"Coordinator: Session {self.blackboard.session_id} initialized")
    
    def execute_compliance_check(self, regulation_text: str, ifc_file_path: str) -> Dict[str, Any]:
        print("Coordinator: Starting compliance check with step-by-step coordination")
        
        # Initialize blackboard for this session
        self._setup_session(regulation_text, ifc_file_path)
        self.update_phase("validation")
        
        # Validate input
        try:
            validated_regulation = validate_regulation_text(regulation_text)
            print("Coordinator: Regulation text validated")
        except ValueError as e:
            print(f"Coordinator: Regulation validation failed: {e}")
            raise
        
        # Generate initial plan from Planner
        self.update_phase("planning")
        current_plan = self._request_initial_plan(validated_regulation)
        
        # Validate plan structure
        current_plan = safe_validate(validate_plan_structure, current_plan, current_plan)
        self.blackboard.update_plan(current_plan, "initial_plan")
        
        # Execute plan 
        print("Coordinator: Starting plan execution...")
        self.update_phase("execution")
        execution_result = self.execute_plan(current_plan, ifc_file_path, self.max_feedback_rounds)
        all_execution_results = execution_result.get("execution_results", [])
        
        # Call Checker
        print("Coordinator: Starting final compliance checking...")
        self.update_phase("checking")
        final_report = self._request_compliance_check(all_execution_results, regulation_text, current_plan)
        print("Coordinator: Final compliance checking completed")
        
        self.update_phase("completed")
        
        # Compile complete results with blackboard context
        return {
            "final_report": final_report,
            "session_summary": self.blackboard.get_context_summary(),
            "blackboard_data": {
                "communication_log": self.blackboard.communication_log,
                "created_tools": self.blackboard.created_tools,
                "plan_modifications": self.blackboard.plan_modifications
            }
        }

    def _request_initial_plan(self, regulation_text: str) -> Dict[str, Any]:
        """Request initial plan from Planner"""
        print("Coordinator: Requesting initial plan from Planner")
        
        request_message = {
            "message_type": "plan_request",
            "timestamp": self._get_timestamp(),
            "sender": "coordinator",
            "recipient": "planner",
            "payload": {
                "regulation_text": regulation_text,
                "request_type": "initial_plan"
            }
        }
        
        self.blackboard.add_communication("coordinator", "planner", "plan_request", request_message["payload"])
        
        # Call Planner
        plan = self.planner.generate_initial_plan(regulation_text)
        
        response_message = {
            "message_type": "plan_response",
            "timestamp": self._get_timestamp(),
            "sender": "planner",
            "recipient": "coordinator",
            "payload": {
                "plan": plan,
                "status": "success" if plan.get("steps") else "failed"
            }
        }
        
        self.blackboard.add_communication("planner", "coordinator", "plan_response", response_message["payload"])
        return plan
    
    
    def _request_plan_modification(self, current_plan: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Request plan modification from Planner based on Executor feedback"""
        print("Coordinator: Requesting plan modification from Planner")
        
        request_message = {
            "message_type": "modification_request",
            "timestamp": self._get_timestamp(),
            "sender": "coordinator",
            "recipient": "planner",
            "payload": {
                "current_plan": current_plan,
                "feedback": feedback,
                "request_type": "modify_plan"
            }
        }
        
        self.blackboard.add_communication("coordinator", "planner", "modification_request", request_message["payload"])
        
        # Call Planner
        modified_plan = self.planner.modify_plan(current_plan, feedback)
        
        response_message = {
            "message_type": "modification_response",
            "timestamp": self._get_timestamp(),
            "sender": "planner",
            "recipient": "coordinator",
            "payload": {
                "modified_plan": modified_plan,
                "status": "success",
                "modification_count": modified_plan.get("modification_count", 0)
            }
        }
        
        self.blackboard.add_communication("planner", "coordinator", "modification_response", response_message["payload"])
        
        return modified_plan
    
    def _request_step_execution(self, step: Dict[str, Any], ifc_file_path: str, step_index: int) -> Dict[str, Any]:
        """Request single step execution from Executor with immediate feedback"""
        print(f"Coordinator: Requesting execution of step {step_index + 1}: {step.get('description', 'Unknown')}")
        
        request_message = {
            "message_type": "step_execution_request",
            "timestamp": self._get_timestamp(),
            "sender": "coordinator",
            "recipient": "executor",
            "payload": {
                "step": step,
                "ifc_file_path": ifc_file_path,
                "step_index": step_index,
                "request_type": "execute_single_step"
            }
        }
        
        self.blackboard.add_communication("coordinator", "executor", "step_execution_request", request_message["payload"])
        
        # Call Executor for single step execution
        step_result = self.executor.execute_single_step(step, ifc_file_path, step_index)
        
        response_message = {
            "message_type": "step_execution_response",
            "timestamp": self._get_timestamp(),
            "sender": "executor",
            "recipient": "coordinator",
            "payload": {
                "step_result": step_result,
                "step_index": step_index,
                "status": step_result.get("step_status", "unknown")
            }
        }
        
        self.blackboard.add_communication("executor", "coordinator", "step_execution_response", response_message["payload"])
        
        return step_result
    
    def _request_compliance_check(self, execution_results: List[Dict[str, Any]], regulation_text: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        print("Coordinator: Requesting compliance check from Checker")
        
        request_message = {
            "message_type": "compliance_check_request",
            "timestamp": self._get_timestamp(),
            "sender": "coordinator",
            "recipient": "checker",
            "payload": {
                "execution_results": execution_results,
                "regulation_text": regulation_text,
                "plan": plan,
                "request_type": "check_compliance"
            }
        }
        
        self.blackboard.add_communication("coordinator", "checker", "compliance_check_request", request_message["payload"])
        
        # Call Checker with three components
        compliance_report = self.checker.check_and_report(execution_results, regulation_text, plan)
        
        response_message = {
            "message_type": "compliance_check_response",
            "timestamp": self._get_timestamp(),
            "sender": "checker",
            "recipient": "coordinator",
            "payload": {
                "compliance_report": compliance_report,
                "status": "success" if compliance_report else "failed"
            }
        }
        
        self.blackboard.add_communication("checker", "coordinator", "compliance_check_response", response_message["payload"])
        
        return compliance_report
    
    def _log_communication(self, message: Dict[str, Any]) -> None:
        """Log communication message"""
        self.communication_log.append(message)
        
        # Keep log size manageable
        if len(self.communication_log) > 100:
            self.communication_log = self.communication_log[-50:]  # Keep last 50 messages
    

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_communication_summary(self) -> Dict[str, Any]:
        """Get summary of communication between agents"""
        if not self.communication_log:
            return {"total_messages": 0, "message_types": {}}
        
        message_types = {}
        for message in self.communication_log:
            msg_type = message.get("message_type", "unknown")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        return {
            "total_messages": len(self.communication_log),
            "message_types": message_types,
            "first_message_time": self.communication_log[0].get("timestamp") if self.communication_log else None,
            "last_message_time": self.communication_log[-1].get("timestamp") if self.communication_log else None
        }
    
    def export_communication_log(self, file_path: str = None) -> str:
        """Export communication log to JSON file"""
        if file_path is None:
            file_path = f"communication_log_{self._get_timestamp().replace(':', '-').replace(' ', '_')}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "communication_log": self.communication_log,
                    "summary": self.get_communication_summary(),
                    "export_timestamp": self._get_timestamp()
                }, f, indent=2, ensure_ascii=False)
            
            return file_path
        except Exception as e:
            print(f"Failed to export communication log: {e}")
            return ""
    
    def execute_plan(self, plan: Dict[str, Any], ifc_file_path: str, max_feedback_rounds: int = 3) -> Dict[str, Any]:
        """
        Execute complete plan with step-by-step coordination and feedback loops
        
        Args:
            plan: Execution plan from Planner
            ifc_file_path: Path to IFC file
            max_feedback_rounds: Maximum feedback rounds for plan modification
            
        Returns:
            Dict: Complete execution results with feedback information
        """
        print(f"Coordinator: Starting step-by-step execution of plan {plan.get('plan_id', 'unknown')}")
        
        # Initialize execution state using blackboard
        current_plan = plan
        all_execution_results = []
        step_execution_history = []
        feedback_round = 0
        execution_status = "in_progress"
        
        # Update blackboard execution state
        self.blackboard.current_step_index = 0
        self.blackboard.feedback_rounds = 0
        self.blackboard.execution_status = execution_status
        
        # Step-by-step execution with immediate feedback
        steps = current_plan.get("steps", [])
        current_step_index = 0
        
        while current_step_index < len(steps) and feedback_round < max_feedback_rounds:
            step = steps[current_step_index]
            print(f"Coordinator: Executing step {current_step_index + 1}/{len(steps)}: {step.get('description', 'Unknown')}")
            
            # Execute single step
            self.blackboard.current_step_index = current_step_index
            step_result = self._request_step_execution(step, ifc_file_path, current_step_index)
            step_execution_history.append(step_result)
            self.blackboard.add_step_history(step_result)
            
            if step_result["step_status"] == "success":
                print(f"Coordinator: Step {current_step_index + 1} completed successfully")
                
                # Collect tool execution results directly
                tool_results = step_result.get("tool_results", [])
                if tool_results:
                    # Add each tool result to execution results for checker
                    all_execution_results.extend(tool_results)
                    for result in tool_results:
                        self.blackboard.add_execution_result(result)
                    print(f"Coordinator: Collected {len(tool_results)} tool results from step")
                else:
                    # Fallback: use step_result if no tool_results
                    result = step_result.get("step_result", {})
                    all_execution_results.append(result)
                    self.blackboard.add_execution_result(result)
                
                current_step_index += 1
                
            elif step_result["step_status"] == "failed":
                print(f"Coordinator: Step {current_step_index + 1} failed, requesting plan modification")
                
                # Request plan modification from Planner
                feedback_request = {
                    "issue_type": step_result.get("failure_reason", "execution_failure"),
                    "issue_description": step_result.get("error_message", "Step execution failed"),
                    "failed_step": step,
                    "step_index": current_step_index,
                    "execution_context": {
                        "completed_steps": current_step_index,
                        "total_steps": len(steps),
                        "step_history": step_execution_history[-3:]  # Last 3 steps for context
                    }
                }
                
                # Add failed step to blackboard
                self.blackboard.add_failed_step(step, step_result.get("error_message", "Unknown error"))
                
                # Get modified plan from Planner
                current_plan = self._request_plan_modification(current_plan, feedback_request)
                steps = current_plan.get("steps", [])
                feedback_round += 1
                self.blackboard.feedback_rounds = feedback_round
                self.blackboard.update_plan(current_plan, f"Feedback round {feedback_round}: {step_result.get('failure_reason', 'execution_failure')}")
                
                print(f"Coordinator: Plan modified (round {feedback_round}), continuing execution")
                # Continue from current step with new plan
                
            else:
                print(f"Coordinator: Unknown step status: {step_result.get('step_status')}")
                execution_status = "error"
                break
        
        # Determine final execution status
        if current_step_index >= len(steps):
            execution_status = "completed"
            print("Coordinator: All steps completed successfully")
        elif feedback_round >= max_feedback_rounds:
            execution_status = "max_feedback_rounds_exceeded"
            print("Coordinator: Maximum feedback rounds reached")
        
        # Update blackboard final status
        self.blackboard.execution_status = execution_status
        
        return {
            "status": execution_status,
            "execution_results": all_execution_results,
            "step_execution_history": step_execution_history,
            "execution_status": execution_status,
            "feedback_rounds_used": feedback_round,
            "steps_completed": current_step_index,
            "total_steps": len(steps),
        }
    
