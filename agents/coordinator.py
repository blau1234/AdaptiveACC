import json
from typing import Dict, List, Any
from agents.planner import Planner
from agents.executor import Executor
from agents.checker import Checker
from models.common_models import ComplianceEvaluationModel, PlanModel, StepExecutionResult
from models.shared_context import SharedContext
import uuid

class AgentCoordinator:
    def __init__(self):
        
        # Initialize shared context 
        self.shared_context = SharedContext.get_instance()

        # Initialize agents 
        self.planner = Planner()
        self.executor = Executor()  
        self.checker = Checker()
        
        self.max_feedback_rounds = 3
    

    def execute_compliance_check(self, regulation_text: str, ifc_file_path: str) -> Dict[str, Any]:
        """Main coordination method to execute compliance checking process"""
        
        # Generate session ID for tracking
        session_id = str(uuid.uuid4())[:8]
        print(f"Coordinator: Session {session_id} initialized")
        
        # Initialize shared context
        self.shared_context.initialize_session(session_id, regulation_text, ifc_file_path)
        
        # Planner：Generate initial plan
        self.shared_context.current_task.update(active_agent="planner", stage="initial_plan")
        initial_plan = self.planner.generate_initial_plan()
        self.log_initial_plan(initial_plan)

        # Executor: Execute plan with step-by-step coordination and feedback loops 
        # Initialize execution state
        feedback_round = 0
        execution_status = "in_progress"
        steps = initial_plan.steps
        current_step_index = 0

        while current_step_index < len(steps) and feedback_round < self.max_feedback_rounds:
            
            # Execute single step
            self.shared_context.current_task.update(active_agent="executor", stage="step_execution", step_index=current_step_index, step=steps[current_step_index])
            step_result = self.executor.execute_step()
            self._log_step_result(step_result)

            if step_result.status == "success":
                current_step_index += 1

            elif step_result.status in ["failed", "timeout"]:
                # Request plan modification from Planner
                self.shared_context.current_task.update(active_agent="planner", stage="plan_modification")
                modified_plan = self.planner.generate_modified_plan()

                # Log the plan modification
                issue_type = "timeout" if step_result.status == "timeout" else "execution_failure"
                self._log_modified_plan(modified_plan, issue_type, current_step_index)

                steps = modified_plan.steps
                
                feedback_round += 1

            else:
                execution_status = "error"
                break

        # Determine final execution status
        if current_step_index >= len(steps):
            execution_status = "completed"
        elif feedback_round >= self.max_feedback_rounds:
            execution_status = "max_feedback_rounds_exceeded"

        # Log execution status to process trace
        self._log_execution_status(execution_status, current_step_index, len(steps), feedback_round)

        # Only run compliance check if execution completed successfully
        if execution_status == "completed":
            # Prepare final trace before checker execution
            self.shared_context.prepare_final_trace()

            # Run compliance evaluation
            self.shared_context.current_task.update(active_agent="checker", stage="compliance_check")
            evaluation_result = self.checker.evaluate_compliance()
            self._log_compliance_evaluation(evaluation_result)
            print("Coordinator: Process completed with compliance check")
        else:
            print(f"Coordinator: Process {execution_status}, skipping compliance check")
        
        # Return complete process trace
        return self.shared_context.process_trace


    def log_initial_plan(self, plan: PlanModel) -> None:
        """Log initial plan to shared context"""

        plan_result = {
            "agent": "planner",
            "phase": "initial_plan",
            "status": "success",
            "summary": f"Generated initial plan with {len(plan.steps)} steps",
            "key_data": {
                "step_count": len(plan.steps),
                "initial_plan": [step.model_dump() for step in plan.steps]
            }
        }
        self.shared_context.process_trace.append(plan_result)


    def _log_modified_plan(self, plan: PlanModel, issue_type: str, failed_step_index: int) -> None:
        """Log modified plan to shared context"""

        modification_result = {
            "agent": "planner",
            "phase": "plan_modification",
            "status": "success",
            "summary": f"Plan modified due to: {issue_type}",
            "key_data": {
                "failed_step_index": failed_step_index,
                "modification_reason": issue_type,
                "revised_plan": [step.model_dump() for step in plan.steps]
            }
        }
        self.shared_context.process_trace.append(modification_result)


    def _log_step_result(self, step_result: StepExecutionResult) -> None:
        """Log single step execution result to shared context"""

        step_index = self.shared_context.current_task.get("step_index")

        log_entry = {
            "agent": "executor",
            "phase": "step_execution",
            "status": step_result.status,
            "summary": f"Step {step_index + 1}: {step_result.status}",
            "key_data": {
                "step_index": step_index,
            }
        }

        if step_result.tool_results:
            log_entry["key_data"]["step_result"] = step_result.tool_results
        if step_result.status in ["failed", "timeout"]:
            log_entry["key_data"]["error"] = step_result.error or "No error message"

        self.shared_context.process_trace.append(log_entry)


    def _log_execution_status(self, status: str, steps_completed: int, total_steps: int, feedback_rounds: int) -> None:
        """Log final execution status to process trace"""

        status_result = {
            "agent": "coordinator",
            "phase": "plan_execution_summary",
            "status": "success" if status == "completed" else "failed",
            "summary": f"Execution {status}: {steps_completed}/{total_steps} steps completed",
            "key_data": {
                "execution_status": status,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "feedback_rounds_used": feedback_rounds
            }
        }
        self.shared_context.process_trace.append(status_result)


    def _log_compliance_evaluation(self, evaluation_result: ComplianceEvaluationModel) -> None:
        """Log complete compliance evaluation result to shared context"""

        compliance_result = {
            "agent": "checker",
            "phase": "compliance_check",
            "status": "success",
            "summary": f"Compliance evaluation: {evaluation_result.overall_status}, {len(evaluation_result.non_compliant_components)} non-compliant components",
            "key_data": {
                # Overall status and summary
                "overall_status": evaluation_result.overall_status,

                # Component-level results (complete)
                "compliant_components": [comp.model_dump() for comp in evaluation_result.compliant_components],
                "non_compliant_components": [comp.model_dump() for comp in evaluation_result.non_compliant_components],
                "uncertain_components": [comp.model_dump() for comp in evaluation_result.uncertain_components],

                # Relationship checks (complete)
                "relationship_checks": [rel.model_dump() for rel in evaluation_result.relationship_checks] if evaluation_result.relationship_checks else [],

                # Statistics summary
                "statistics": {
                    "total_components_checked": len(evaluation_result.compliant_components) + len(evaluation_result.non_compliant_components) + len(evaluation_result.uncertain_components) ,
                    "compliant_count": len(evaluation_result.compliant_components),
                    "non_compliant_count": len(evaluation_result.non_compliant_components),
                    "uncertain_count": len(evaluation_result.uncertain_components),
                    "relationship_checks_count": len(evaluation_result.relationship_checks) if evaluation_result.relationship_checks else 0
                }
            }
        }
        self.shared_context.process_trace.append(compliance_result)


