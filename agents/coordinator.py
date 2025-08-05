import json
from typing import Dict, List, Any
from agents.planner import Planner
from agents.executor import Executor
from agents.checker import Checker
from datetime import datetime
from utils.validation import validate_regulation_text, validate_plan_structure, safe_validate

class AgentCoordinator:
    def __init__(self):
        self.planner = Planner()
        self.executor = Executor()
        self.checker = Checker()
        self.communication_log = []
        self.max_feedback_rounds = 3
    
    def execute_compliance_check(self, regulation_text: str, ifc_file_path: str) -> Dict[str, Any]:
        print("Coordinator: Starting compliance check with step-by-step coordination")
        
        # Validate input
        try:
            validated_regulation = validate_regulation_text(regulation_text)
            print("Coordinator: Regulation text validated")
        except ValueError as e:
            print(f"Coordinator: Regulation validation failed: {e}")
            raise
        
        # Generate initial plan from Planner
        current_plan = self._request_initial_plan(validated_regulation)
        
        # Validate plan structure
        current_plan = safe_validate(validate_plan_structure, current_plan, current_plan)
        
        # Execute plan using the unified execution method
        print("Coordinator: Starting plan execution...")
        execution_result = self.execute_plan(current_plan, ifc_file_path, self.max_feedback_rounds)
        
        # Extract results from unified execution
        all_execution_results = execution_result.get("execution_results", [])
        step_execution_history = execution_result.get("step_execution_history", [])
        execution_status = execution_result.get("execution_status", "unknown")
        feedback_round = execution_result.get("feedback_rounds_used", 0)
        current_step_index = execution_result.get("steps_completed", 0)
        current_plan = execution_result.get("final_plan", current_plan)  # Use the potentially modified plan
        steps = current_plan.get("steps", [])
        
        # Call Checker
        print("Coordinator: Starting final compliance checking...")
        final_report = self._request_compliance_check(all_execution_results, regulation_text, current_plan)
        print("Coordinator: Final compliance checking completed")
        
        # Compile complete results
        return {
            "plan": current_plan,
            "final_plan": current_plan,  # The potentially modified final plan
            "execution_results": all_execution_results,
            "step_execution_history": step_execution_history,
            "execution_status": execution_status,
            "feedback_rounds_used": feedback_round,
            "steps_completed": current_step_index,
            "total_steps": len(steps),
            "final_report": final_report,
            "communication_log": self.communication_log.copy(),
            "planner_history": self.planner.get_conversation_history(),
            "executor_history": self.executor.get_execution_history()
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
        
        self._log_communication(request_message)
        
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
        
        self._log_communication(response_message)
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
        
        self._log_communication(request_message)
        
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
        
        self._log_communication(response_message)
        
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
        
        self._log_communication(request_message)
        
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
        
        self._log_communication(response_message)
        
        return step_result
    
    def _request_compliance_check(self, execution_results: List[Dict[str, Any]], regulation_text: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Request compliance checking from Checker with three components"""
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
        
        self._log_communication(request_message)
        
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
        
        self._log_communication(response_message)
        
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
                
                # Collect tool execution results directly
                tool_results = step_result.get("tool_results", [])
                if tool_results:
                    # Add each tool result to execution results for checker
                    all_execution_results.extend(tool_results)
                    print(f"Coordinator: Collected {len(tool_results)} tool results from step")
                else:
                    # Fallback: use step_result if no tool_results
                    all_execution_results.append(step_result.get("step_result", {}))
                
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
    
