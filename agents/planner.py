import json
from typing import Dict, List, Any
from utils.llm_client import LLMClient
import re
from models.blackboard_models import BlackboardMixin

class Planner(BlackboardMixin):

    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.conversation_history = []
    
    def generate_initial_plan(self, regulation_text: str) -> Dict[str, Any]:
        try:
            print("Planner: Analyzing regulation text and generating initial plan...")
            
            # Use blackboard if available, otherwise use parameter
            if hasattr(self, '_blackboard') and self._blackboard:
                regulation_text = regulation_text or self.get_regulation_text()
                self.log_communication("coordinator", "plan_generation", {"regulation_length": len(regulation_text)})
            
            # Analyze regulation to extract requirements
            regulation_analysis = self._analyze_regulation(regulation_text)
            
            # Generate structured plan
            plan_steps = self._generate_plan_steps(regulation_analysis, regulation_text)
            
            plan = {
                "plan_id": self._generate_plan_id(),
                "regulation_summary": regulation_analysis.get("summary", ""),
                "steps": plan_steps,
                "modification_count": 0
            }
            
            self.conversation_history.append({
                "type": "plan_generation",
                "timestamp": self._get_timestamp(),
                "plan_id": plan["plan_id"],
                "steps_count": len(plan_steps)
            })
            
            print(f"Planner: Generated initial plan with {len(plan_steps)} steps")
            
            # Update blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                self.blackboard.update_plan(plan, "initial_plan_generated")
            
            return plan
            
        except Exception as e:
            print(f"Planner: Failed to generate initial plan: {e}")
            raise RuntimeError(f"Plan generation failed: {e}") from e
    
    def modify_plan(self, current_plan: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify plan based on executor feedback using LLM
        
        Args:
            current_plan: Current execution plan
            feedback: Feedback from executor
            
        Returns:
            Dict: Modified plan
        """
        try:
            print(f"Planner: Received feedback from Executor: {feedback.get('issue_type', 'unknown')}")
            
            # Log to blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                self.log_communication("executor", "plan_modification_request", feedback)
            
            # Use LLM to dynamically modify the plan based on feedback
            modified_plan = self._llm_modify_plan(current_plan, feedback)
            
            # Update plan metadata
            modified_plan["status"] = "modified"
            modified_plan["modification_count"] = current_plan.get("modification_count", 0) + 1
            modified_plan["last_modified"] = self._get_timestamp()
            modified_plan["modification_reason"] = feedback.get("issue_description", "Unknown issue")
            
            self.conversation_history.append({
                "type": "plan_modification",
                "timestamp": self._get_timestamp(),
                "plan_id": modified_plan["plan_id"],
                "feedback_type": feedback.get("issue_type"),
                "modification_count": modified_plan["modification_count"]
            })
            
            print(f"Planner: Plan modified (modification #{modified_plan['modification_count']})")
            
            # Update blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                self.blackboard.update_plan(modified_plan, feedback.get('issue_description', 'Unknown issue'))
            
            return modified_plan
            
        except Exception as e:
            print(f"Planner: Failed to modify plan: {e}")
            raise RuntimeError(f"Plan modification failed: {e}") from e
    
    def _analyze_regulation(self, regulation_text: str) -> Dict[str, Any]:
        """Analyze regulation text to extract key requirements"""
        system_prompt = """You are a building code regulation analysis expert.
        
        Analyze the regulation text and extract:
        1. Main compliance requirements
        2. Technical specifications
        3. Measurable criteria
        4. Potential check points
        
        Return JSON format:
        {
            "summary": "Brief summary of the regulation",
            "requirements": [
                {
                    "id": "req_1",
                    "description": "Requirement description",
                    "type": "structural|safety|accessibility|other",
                    "measurable": true/false,
                    "criteria": "Specific measurement criteria if applicable"
                }
            ],
            "complexity": "low|medium|high",
            "estimated_checks": 3
        } """
        
        prompt = f""" 
        Please analyze this building regulation text: {regulation_text}
        """
        response = self.llm_client.generate_response(prompt, system_prompt)
       
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)  
                return json.loads(json_str)
            else:
                return json.loads(response)
            
        except Exception as e:
            print(f"Parse error: {e}")
            raise RuntimeError(f"Failed to parse regulation analysis response: {e}") from e
    
    def _generate_plan_steps(self, regulation_analysis: Dict[str, Any], regulation_text: str) -> List[Dict[str, Any]]:
        """Generate structured plan steps based on regulation analysis"""

        system_prompt = """You are a building compliance plan generator.
        
        Based on the regulation analysis, create a step-by-step execution plan.
        Each step should be actionable and specific.
        only include intermediate information extraction steps.
        Do **not** include any comparison, final summary or overall validation step.

        Return JSON array of steps:
        [
            {
                "step_id": "step_1",
                "description": "Clear description of what to check",
                "priority": "high|medium|low",
                "expected_output": "Description of expected result",
                "dependencies": ["step_id_that_must_complete_first"]
            }
        ]"""
        
        prompt = f"""
        Regulation Analysis: {json.dumps(regulation_analysis, indent=2)}
        Original Regulation: {regulation_text}
        Generate a detailed execution plan:
        """
        
        response = self.llm_client.generate_response(prompt, system_prompt)
        
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)  
                parsed_result = json.loads(json_str)
            else:
                parsed_result = json.loads(response)
            
            # Validate that the result is a list
            if not isinstance(parsed_result, list):
                raise ValueError(f"Expected list of steps, got {type(parsed_result).__name__}")
            
            return parsed_result
            
        except Exception as e:
            print(f"Parse error: {e}")
            raise RuntimeError(f"Failed to parse plan steps response: {e}") from e
    
    def _llm_modify_plan(self, current_plan: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to dynamically modify plan based on feedback
        
        Args:
            current_plan: Current execution plan
            feedback: Feedback from executor
            
        Returns:
            Dict: Modified plan
        """
        system_prompt = """You are an expert building compliance plan modifier.
        
        Based on the executor feedback, intelligently modify the current plan to address the issues.
        You can:
        1. Modify existing steps (change description, tools, approach)
        2. Add new prerequisite steps
        3. Remove or skip problematic steps
        4. Reorganize step order
        5. Split complex steps into simpler ones
        6. Combine simple steps if appropriate
        
        IMPORTANT: Return the COMPLETE modified plan in the same JSON format, preserving all existing fields and structure.
        Only modify what's necessary to address the feedback.
        
        Return JSON format:
        {
            "plan_id": "keep_same_id",  
            "regulation_summary": "keep_existing",
            "requirements": [...keep_existing...],
            "steps": [
                {
                    "step_id": "step_1",  // keep existing or create new IDs
                    "description": "Modified or new description",
                    "task_type": "file_analysis|element_check|measurement|calculation|validation",
                    "priority": "high|medium|low",
                    "tool_description": "Description of tool needed",
                    "expected_output": "Expected result",
                    "dependencies": ["step_dependencies"]
                }
            ]
        }"""
        
        prompt = f"""
        CURRENT PLAN:
        {json.dumps(current_plan, indent=2)}
        
        EXECUTOR FEEDBACK:
        - Issue Type: {feedback.get('issue_type', 'unknown')}
        - Issue Description: {feedback.get('issue_description', 'No description')}
        - Failed Step: {json.dumps(feedback.get('failed_step', {}), indent=2)}
        - Step Index: {feedback.get('step_index', 'unknown')}
        - Error Message: {feedback.get('error_message', 'No error message')}
        - Execution Context: {json.dumps(feedback.get('execution_context', {}), indent=2)}
        
        Please analyze the feedback and modify the plan to address the issues. 
        Be smart and practical - if a tool failed, suggest alternatives. 
        If information is missing, add steps to gather it.
        If a step is unclear, clarify or break it down.
        
        Provide the complete modified plan:
        """
        
        response = self.llm_client.generate_response(prompt, system_prompt)
        
        try:
            modified_plan = json.loads(response)
            
            # Validate the modified plan has required structure
            if not isinstance(modified_plan.get("steps"), list):
                raise ValueError("Modified plan must have steps as list")
            
            if len(modified_plan["steps"]) == 0:
                raise ValueError("Modified plan must have at least one step")
            
            # Preserve original plan metadata that shouldn't change
            modified_plan["plan_id"] = current_plan["plan_id"]
            
            return modified_plan
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Failed to parse LLM plan modification: {e}")
            raise RuntimeError(f"Plan modification failed: {e}") from e
    
    def _generate_plan_id(self) -> str:
        """Generate unique plan ID"""
        import uuid
        return f"plan_{uuid.uuid4().hex[:8]}"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history with executor"""
        return self.conversation_history.copy()