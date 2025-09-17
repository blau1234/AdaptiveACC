import json
from typing import Dict, List, Any
from utils.llm_client import LLMClient
from models.common_models import PlanModel, RegulationAnalysis, StepModel
from models.shared_context import SharedContext

class Planner:

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()
   
    def generate_initial_plan(self) -> PlanModel:
        """Generate initial plan using regulation text from shared context"""
        try:
            
            # Get regulation text from shared context
            if not self.shared_context:
                raise RuntimeError("Shared context not available")
            
            regulation_text = self.shared_context.session_info.get("regulation_text")
            if not regulation_text:
                raise RuntimeError("Regulation text not found in shared context")
            
            # Analyze regulation to extract requirements
            regulation_analysis = self._analyze_regulation(regulation_text)
            
            # Generate structured plan
            plan = self._generate_plan(regulation_analysis)

            print(f"Planner: Generated initial plan with {len(plan.steps)} steps")
            return plan
            
        except Exception as e:
            print(f"Planner: Failed to generate initial plan: {e}")
            raise RuntimeError(f"Plan generation failed: {e}") from e
    

    def generate_modified_plan(self) -> PlanModel:
        """Modify existing plan based on execution history in shared context"""

        try:
            # Get execution context from shared context
            process_trace = self.shared_context.process_trace

            # Use LLM to dynamically modify the plan based on execution history
            modified_plan = self._modify_plan(process_trace)

            print(f"Planner: Plan modified based on execution history")

            return modified_plan
            
        except Exception as e:
            print(f"Planner: Failed to modify plan: {e}")
            raise RuntimeError(f"Plan modification failed: {e}") from e
    
    def _analyze_regulation(self, regulation_text: str) -> RegulationAnalysis:
        """Analyze regulation text to extract comprehensive compliance checking information"""
        
        system_prompt = """You are a building code regulation analysis expert specializing in IFC-based compliance checking.
        Perform comprehensive analysis to extract all necessary information for automated building compliance verification:

        ## Analysis Framework:
        1. **Core Information**:
           - Create a concise summary of the regulation's main requirements
           - Identify the specific scope (e.g., means of egress, accessibility, structural)

        2. **Applicability Analysis**:
           - Determine when this regulation applies (building type, occupancy, element type, etc.)
           - Extract any conditional requirements or thresholds

        3. **IFC Mapping**:
           - Identify target IFC entities that need to be checked (e.g., IfcDoor, IfcStair, IfcWall, IfcSpace, IfcBeam)
           - List required IFC attributes/properties for verification (e.g., Height, Width, Material, FireRating)

        4. **Compliance Logic**:
           - Classify the check type: e.g. "existence", "comparison", "range", "relation", "geometry", or "aggregation"
           - Extract logical conditions as measurable criteria (e.g., "width >= 800mm", "height <= 2100mm")

        5. **Regulatory Context**:
           - Identify references to other regulations or standards this depends on
           - Note any exceptions, exemptions, or special cases mentioned

        ## Common IFC Entities:
        IfcDoor, IfcWindow, IfcWall, IfcStair, IfcRamp, IfcSpace, IfcBeam, IfcColumn, IfcSlab, IfcRailing

        ## Example Check Types:
        - existence: Verify element exists
        - comparison: Compare value to threshold (>, <, =)
        - range: Check if value falls within range
        - relation: Check relationships between elements
        - geometry: Verify geometric properties
        - aggregation: Check counts or totals

        Provide detailed, structured analysis suitable for automated compliance checking."""

        prompt = f"""Analyze this building regulation text for automated compliance checking:

        REGULATION TEXT:
        {regulation_text}

        Extract all information needed to implement automated IFC-based compliance verification."""

        return self.llm_client.generate_response(
            prompt,
            system_prompt,
            response_model=RegulationAnalysis
        )
    
    def _generate_plan(self, regulation_analysis: RegulationAnalysis) -> PlanModel:
        """Generate structured plan steps based on regulation analysis"""

        system_prompt = """You are a building compliance plan generator.
        Based on the regulation analysis, create a step-by-step execution plan.
        
        ## Step Design Principles:
        - Break complex operations into multiple simple steps
        - Ensure clear data flow between steps
        - Each step must be atomic - completable by one tool in one execution
        - Avoid steps that require multiple tool calls or complex coordination
        - Only include intermediate information extraction steps. 
        - Do **not** include any comparison, final summary or overall validation step.


        For each step, provide these exact fields:
        - **description**: Clear, specific action that one tool can perform (e.g., "Extract height measurements from IfcDoor elements")
        - **task_type**: Type of operation (e.g., "measurement", "extraction", "parsing", "analysis", "validation")
        - **inputs**: Step-specific parameters needed (e.g., {"element_type": "IfcDoor", "property": "Height"})
        - **expected_output**: Precise format of results (e.g., "List of door heights in millimeters")
        """
        
        prompt = f"""
        Regulation Analysis: {regulation_analysis.model_dump_json(indent=2)}
        Generate a detailed execution plan with actionable steps:
        """
    
        return self.llm_client.generate_response(
            prompt, 
            system_prompt,
            response_model=PlanModel
        )
    
    def _modify_plan(self, process_trace: List[Dict[str, Any]]) -> PlanModel:
        """Use LLM to intelligently modify the current plan based on executor feedback"""
        
        system_prompt = """You are an expert building compliance plan modifier. Your role is to intelligently adapt execution plans based on process trace analysis.

        ## Core Capabilities
        - Extract and analyze current plan from process trace history
        - Identify failure patterns and root causes from execution results
        - Generate optimized plan modifications using proven strategies

        ## Step Design Principles:
        - Break complex operations into multiple simple steps
        - Ensure clear data flow between steps
        - Each step must be atomic - completable by one tool in one execution
        - Avoid steps that require multiple tool calls or complex coordination
        - Only include intermediate information extraction steps. 
        - Do **not** include any comparison, final summary or overall validation step.

        ## Plan Structure Requirements
        Each step must conform to PlanModel with these exact fields:
        - **description**: Clear, specific action (e.g., "Extract height measurements from IfcDoor elements")
        - **task_type**: Operation type (measurement, extraction, parsing, analysis, validation)
        - **inputs**: Step-specific parameters (e.g., {"element_type": "IfcDoor", "property": "Height"})
        - **expected_output**: Precise result format (e.g., "List of door heights in millimeters")

        ## Modification Strategies by Error Type
        **execution_failure**: Alternative tools/approaches, break into simpler sub-steps, add prerequisites
        **timeout**: Reduce scope, add checkpoints, split large operations
        **tool_missing**: Suggest alternatives, add tool creation steps, modify requirements
        """
        
        prompt = f"""
        PROCESS TRACE DATA:
        {json.dumps(process_trace[-10:], indent=2)}

        TASK: Create a modified plan based on the execution history above.

        INSTRUCTIONS:
        1. Extract the current plan (look for 'initial_plan' or 'revised_plan' in key_data)
        2. Identify the specific failure from step execution results
        3. Generate an improved plan that addresses the identified issues

        Return the complete modified plan as PlanModel with all steps."""
        
        modified_plan_result = self.llm_client.generate_response(
            prompt,
            system_prompt,
            response_model=PlanModel
        )

        return modified_plan_result
    

 
