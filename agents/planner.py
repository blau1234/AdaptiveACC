import json
from typing import Dict, List, Any
from utils.llm_client import LLMClient
from data_models.shared_models import PlanModel, RegulationAnalysis, StepModel, ModifiedPlan
from shared_context import SharedContext

class Planner:

    def __init__(self, shared_context: SharedContext = None):
        self.llm_client = LLMClient()
        self.shared_context = shared_context
        # Remove conversation_history as it's now in shared context
    
    def generate_initial_plan(self) -> Dict[str, Any]:
        """Generate initial plan using regulation text from shared context"""
        try:
            print("Planner: Analyzing regulation text and generating initial plan...")
            
            # Get regulation text from shared context
            if not self.shared_context:
                raise RuntimeError("Shared context not available")
            
            regulation_text = self.shared_context.session_info.get("regulation_text")
            if not regulation_text:
                raise RuntimeError("Regulation text not found in shared context")
            
            # Analyze regulation to extract requirements
            regulation_analysis = self._analyze_regulation(regulation_text)
            
            # Generate structured plan
            plan_steps = self._generate_plan_steps(regulation_analysis, regulation_text)
            
            # Convert StepModel objects to dict format for compatibility
            steps_dict = [step.model_dump() for step in plan_steps]
            
            plan = {
                "plan_id": self._generate_plan_id(),
                "regulation_summary": regulation_analysis.summary,
                "steps": steps_dict,
                "modification_count": 0
            }
            
            print(f"Planner: Generated initial plan with {len(plan_steps)} steps")
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
            
            # Get execution context from shared context for better plan modification
            context_info = None
            if self.shared_context:
                context_info = self.shared_context.get_context_for_agent("planner")
            
            # Use LLM to dynamically modify the plan based on feedback
            modified_plan = self._llm_modify_plan(current_plan, feedback, context_info)
            
            # Update plan metadata
            modified_plan["status"] = "modified"
            modified_plan["modification_count"] = current_plan.get("modification_count", 0) + 1
            modified_plan["last_modified"] = self._get_timestamp()
            modified_plan["modification_reason"] = feedback.get("issue_description", "Unknown issue")
            
            # Planning history is now managed in shared context by coordinator
            
            print(f"Planner: Plan modified (modification #{modified_plan['modification_count']})")
            
            
            return modified_plan
            
        except Exception as e:
            print(f"Planner: Failed to modify plan: {e}")
            raise RuntimeError(f"Plan modification failed: {e}") from e
    
    def _analyze_regulation(self, regulation_text: str) -> RegulationAnalysis:
        """Analyze regulation text to extract key requirements"""
        system_prompt = """You are a building code regulation analysis expert.
        
        Analyze the regulation text and extract:
        1. Main compliance requirements
        2. Technical specifications
        3. Measurable criteria
        4. Potential check points
        
        Provide comprehensive analysis with clear requirement identification."""
        
        prompt = f""" 
        Please analyze this building regulation text: {regulation_text}
        """
        
        return self.llm_client.generate_response(
            prompt, 
            system_prompt,
            response_model=RegulationAnalysis
        )
    
    def _generate_plan_steps(self, regulation_analysis: RegulationAnalysis, regulation_text: str) -> List[StepModel]:
        """Generate structured plan steps based on regulation analysis"""

        system_prompt = """You are a building compliance plan generator.
        
        Based on the regulation analysis, create a step-by-step execution plan.
        Each step should be actionable and specific.
        Only include intermediate information extraction steps.
        Do **not** include any comparison, final summary or overall validation step.

        For each step, provide:
        - Clear step identifier 
        - Detailed description of what to check/measure
        - Priority level based on regulation importance
        - Task type (measurement, analysis, etc.)
        - Expected output format
        - Any dependencies on other steps
        - Tool requirements if specific tools are needed"""
        
        prompt = f"""
        Regulation Analysis: {regulation_analysis.model_dump_json(indent=2)}
        Original Regulation: {regulation_text}
        Generate a detailed execution plan with actionable steps:
        """
        
        return self.llm_client.generate_response(
            prompt, 
            system_prompt,
            response_model=List[StepModel]
        )
    
    def _llm_modify_plan(self, current_plan: Dict[str, Any], feedback: Dict[str, Any], context_info: Dict[str, Any] = None) -> Dict[str, Any]:
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
        
        Focus on creating actionable, specific steps with clear:
        - Step identifiers
        - Detailed descriptions
        - Appropriate task types
        - Priority levels
        - Expected outputs
        - Tool requirements
        - Dependencies between steps
        
        Address the specific issues mentioned in the feedback."""
        
        # Include execution context if available
        execution_context_str = ""
        if context_info and context_info.get("relevant_history"):
            execution_context_str = f"""
        EXECUTION HISTORY (for context):
        {json.dumps(context_info['relevant_history'][:5], indent=2)}
        """

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
        {execution_context_str}
        
        Please analyze the feedback and modify the plan to address the issues. 
        Be smart and practical - if a tool failed, suggest alternatives. 
        If information is missing, add steps to gather it.
        If a step is unclear, clarify or break it down.
        Consider the execution history to avoid repeating past mistakes.
        """
        
        modified_plan_result = self.llm_client.generate_response(
            prompt, 
            system_prompt,
            response_model=ModifiedPlan
        )
        
        # Convert back to dict format with preserved metadata
        modified_plan_dict = modified_plan_result.model_dump()
        modified_plan_dict["plan_id"] = current_plan["plan_id"]  # Preserve original ID
        modified_plan_dict["regulation_summary"] = current_plan.get("regulation_summary", "")
        
        return modified_plan_dict
    
    def _generate_plan_id(self) -> str:
        """Generate unique plan ID"""
        import uuid
        return f"plan_{uuid.uuid4().hex[:8]}"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get execution context from shared context"""
        if self.shared_context:
            return self.shared_context.get_context_for_agent("planner")
        return {}