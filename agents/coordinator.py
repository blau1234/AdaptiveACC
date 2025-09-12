import json
from typing import Dict, List, Any
from agents.planner import Planner
from agents.executor import Executor
from agents.checker import Checker
from meta_tools import MetaToolManager
from domain_tools.tool_registry import create_building_tool_registry
from toolregistry import ToolRegistry
from datetime import datetime
from shared_context import SharedContext
# Simple validation function (inline replacement)
def validate_regulation_text(text: str) -> str:
    if not text or not isinstance(text, str):
        raise ValueError("Regulation text must be a non-empty string")
    return text.strip()
import uuid

class AgentCoordinator:
    def __init__(self, tool_vector_db=None):
        pass
        
        # Initialize shared context for multi-agent collaboration
        self.shared_context = SharedContext()
        
        # Initialize shared ToolRegistry directly
        self.tool_registry = create_building_tool_registry()
        
        # Store tool vector database
        self.tool_vector_db = tool_vector_db
        
        # Initialize Meta Tool Manager
        self.meta_tool_manager = MetaToolManager(
            domain_tool_registry=self.tool_registry,
            tool_vector_db=tool_vector_db,
            storage_dir="tools",
            vectordb_path="vectordb/docs"
        )
        
        # Set shared context for meta tool manager
        self.meta_tool_manager.set_shared_context(self.shared_context)
        
        # Register meta tools as ReAct tools for the Executor
        meta_tool_names = self.meta_tool_manager.register_meta_tools_to_registry(self.tool_registry)
        print(f"Registered {len(meta_tool_names)} meta tools: {meta_tool_names}")
        
        # Initialize agents with shared context
        self.planner = Planner(shared_context=self.shared_context)
        self.executor = Executor(shared_context=self.shared_context)
        # Register meta tools to executor
        self.meta_tool_manager.register_meta_tools_to_registry(self.executor.meta_tool_registry)
        self.checker = Checker(shared_context=self.shared_context)
        
        # Simplified communication log for monitoring only
        self.communication_log = []
        self.max_feedback_rounds = 3
    
    def execute_compliance_check(self, regulation_text: str, ifc_file_path: str) -> Dict[str, Any]:
        print("Coordinator: Starting compliance check with step-by-step coordination")
        
        # Generate session ID for tracking
        session_id = str(uuid.uuid4())[:8]
        print(f"Coordinator: Session {session_id} initialized")
        
        # Initialize shared context
        try:
            validated_regulation = validate_regulation_text(regulation_text)
            self.shared_context.initialize_session(session_id, validated_regulation, ifc_file_path)
            print("Coordinator: Shared context initialized and regulation text validated")
        except ValueError as e:
            print(f"Coordinator: Regulation validation failed: {e}")
            raise
        
        # Generate initial plan from Planner
        print("Coordinator: Planning phase")
        self.shared_context.update_current_state(active_agent="planner", phase="planning")
        current_plan = self._request_initial_plan()
        
        # Plan structure validation is now handled by Instructor in LLMClient
        
        # Execute plan 
        print("Coordinator: Starting plan execution...")
        print("Coordinator: Execution phase")
        self.shared_context.update_current_state(active_agent="executor", phase="execution")
        execution_result = self.execute_plan(current_plan, ifc_file_path, self.max_feedback_rounds)
        
        # Call Checker
        print("Coordinator: Starting final compliance checking...")
        print("Coordinator: Checking phase")
        self.shared_context.update_current_state(active_agent="checker", phase="checking")
        final_report = self._request_compliance_check(current_plan)
        print("Coordinator: Final compliance checking completed")
        
        # Clean up old results and get session summary
        self.shared_context.cleanup_old_results()
        session_summary = self.shared_context.get_session_summary()
        
        print("Coordinator: Process completed")
        
        # Compile complete results
        return {
            "final_report": final_report,
            "session_id": session_id,
            "session_summary": session_summary,
            "execution_summary": {
                "status": execution_result.get("status"),
                "feedback_rounds_used": execution_result.get("feedback_rounds_used", 0),
                "steps_completed": execution_result.get("steps_completed", 0),
                "total_steps": execution_result.get("total_steps", 0)
            }
        }

    def _request_initial_plan(self) -> Dict[str, Any]:
        """Request initial plan from Planner using shared context"""
        print("Coordinator: Requesting initial plan from Planner")
        
        # Simple communication log entry
        self._log_communication("plan_request", "coordinator", "planner")
        
        # Call Planner (planner will read from shared context)
        plan = self.planner.generate_initial_plan()
        
        # Log plan generation result in shared context
        plan_result = {
            "agent": "planner",
            "step_id": "initial_plan",
            "status": "success" if plan.get("steps") else "failed",
            "timestamp": self._get_timestamp(),
            "key_findings": [f"Generated plan with {len(plan.get('steps', []))} steps"]
        }
        self.shared_context.add_execution_result(plan_result)
        
        self._log_communication("plan_response", "planner", "coordinator")
        return plan
    
    
    def _request_plan_modification(self, current_plan: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Request plan modification from Planner based on Executor feedback"""
        print("Coordinator: Requesting plan modification from Planner")
        
        self._log_communication("modification_request", "coordinator", "planner")
        
        # Store feedback in shared context for planner to access
        self.shared_context.update_current_state(
            modification_feedback=feedback,
            current_plan_id=current_plan.get("plan_id")
        )
        
        # Call Planner
        modified_plan = self.planner.modify_plan(current_plan, feedback)
        
        # Log modification result
        modification_result = {
            "agent": "planner",
            "step_id": f"plan_modification_{modified_plan.get('modification_count', 0)}",
            "status": "success",
            "timestamp": self._get_timestamp(),
            "key_findings": [f"Plan modified due to: {feedback.get('issue_type', 'unknown')}"],
            "plan_modifications": feedback
        }
        self.shared_context.add_execution_result(modification_result)
        
        self._log_communication("modification_response", "planner", "coordinator")
        return modified_plan
    
    def _request_step_execution(self, step: Dict[str, Any], ifc_file_path: str, step_index: int) -> Dict[str, Any]:
        """Request single step execution from Executor with immediate feedback"""
        print(f"Coordinator: Requesting execution of step {step_index + 1}: {step.get('description', 'Unknown')}")
        
        self._log_communication("step_execution_request", "coordinator", "executor")
        
        # Update current step information in shared context
        self.shared_context.update_current_state(
            current_step=step,
            step_index=step_index,
            current_step_description=step.get('description', 'Unknown')
        )
        
        # Call Executor for single step execution
        step_result = self.executor.execute_single_step(step, ifc_file_path, step_index)
        
        # Log step execution in shared context
        execution_result = {
            "agent": "executor",
            "step_id": step.get("step_id", f"step_{step_index}"),
            "status": step_result.get("step_status", "unknown"),
            "timestamp": self._get_timestamp(),
            "tool_results": step_result.get("tool_results", []),
            "step_result": step_result.get("step_result", {}),
            "errors": step_result.get("errors", [])
        }
        self.shared_context.add_execution_result(execution_result)
        
        self._log_communication("step_execution_response", "executor", "coordinator")
        return step_result
    
    def _request_compliance_check(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Request compliance check from Checker using shared context"""
        print("Coordinator: Requesting compliance check from Checker")
        
        self._log_communication("compliance_check_request", "coordinator", "checker")
        
        # Store plan information for checker
        self.shared_context.update_current_state(current_plan=plan)
        
        # Call Checker (checker will read execution results from shared context)
        compliance_report = self.checker.check_and_report(plan)
        
        # Log compliance check result
        compliance_result = {
            "agent": "checker",
            "step_id": "compliance_check",
            "status": "success" if compliance_report else "failed",
            "timestamp": self._get_timestamp(),
            "compliance_status": compliance_report.get("executive_summary", {}).get("status", "unknown"),
            "key_findings": [
                f"Compliance: {compliance_report.get('executive_summary', {}).get('status', 'unknown')}",
                f"Critical issues: {compliance_report.get('executive_summary', {}).get('critical_issues', 0)}"
            ],
            "violations": compliance_report.get("compliance_details", {}).get("violations", [])
        }
        self.shared_context.add_execution_result(compliance_result)
        
        self._log_communication("compliance_check_response", "checker", "coordinator")
        return compliance_report
    
    def _log_communication(self, message_type: str, sender: str, recipient: str) -> None:
        """Simplified communication logging for monitoring"""
        log_entry = {
            "type": message_type,
            "from": sender,
            "to": recipient,
            "timestamp": self._get_timestamp()
        }
        self.communication_log.append(log_entry)
        
        # Keep log size manageable
        if len(self.communication_log) > 50:
            self.communication_log = self.communication_log[-25:]  # Keep last 25 messages
    

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
        
        # Initialize execution state
        current_plan = plan
        all_execution_results = []
        step_execution_history = []
        feedback_round = 0
        execution_status = "in_progress"
        
        # Step-by-step execution with immediate feedback
        steps = current_plan.get("steps", [])
        current_step_index = 0
        
        while current_step_index < len(steps) and feedback_round < max_feedback_rounds:
            step = steps[current_step_index]
            print(f"Coordinator: Executing step {current_step_index + 1}/{len(steps)}: {step.get('description', 'Unknown')}")
            
            # Execute single step
            step_result = self._request_step_execution(step, ifc_file_path, current_step_index)
            step_execution_history.append(step_result)
            
            if step_result["step_status"] == "success":
                print(f"Coordinator: Step {current_step_index + 1} completed successfully")
                
                # Results are already logged in shared context by _request_step_execution
                # Just collect them for legacy compatibility
                tool_results = step_result.get("tool_results", [])
                if tool_results:
                    all_execution_results.extend(tool_results)
                    print(f"Coordinator: Collected {len(tool_results)} tool results from step")
                else:
                    result = step_result.get("step_result", {})
                    all_execution_results.append(result)
                
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
                
                # Get modified plan from Planner
                current_plan = self._request_plan_modification(current_plan, feedback_request)
                steps = current_plan.get("steps", [])
                feedback_round += 1
                
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
        
        return {
            "status": execution_status,
            "execution_results": all_execution_results,
            "step_execution_history": step_execution_history,
            "execution_status": execution_status,
            "feedback_rounds_used": feedback_round,
            "steps_completed": current_step_index,
            "total_steps": len(steps),
        }