import json
from typing import Dict, Any, List, Tuple
from datetime import datetime

from utils.llm_client import LLMClient
from .data_models import ToolRequirement, AnalysisResult
from models.blackboard_models import BlackboardMixin


class SpecGenerator(BlackboardMixin):
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
    
    def analyze_step(self, step_content: str) -> AnalysisResult:
       
        try:
            print(f"SpecGenerator: Analyzing step - {step_content[:50]}...")
            
            # Step 1: Get data from blackboard
            current_step, execution_history = self._get_blackboard_data()
            
            # Step 2: Get real IFC file path from blackboard
            ifc_file_path = self._get_ifc_file_path()
            
            # Step 3: Use LLM to analyze step requirements with context including real IFC path
            analysis = self._llm_analyze_step_requirements(step_content, current_step, execution_history, ifc_file_path)
            
            # Step 3: Create structured tool requirement and extract IFC dependencies
            tool_req_data = analysis.get("tool_requirement", {})
            tool_requirement = ToolRequirement(
                description=tool_req_data.get("description", "Auto-generated tool"),
                function_name=tool_req_data.get("function_name", "generated_tool"), 
                parameters=tool_req_data.get("parameters", [
                    {"name": "ifc_file_path", "type": "str", "description": "Path to IFC file"}
                ]),
                return_type=tool_req_data.get("return_type", "Dict[str, Any]"),
                examples=tool_req_data.get("examples", [])
            )
            ifc_dependencies = analysis.get("ifc_dependencies", {})
            
            # Step 4: Get test parameters directly from LLM analysis 
            test_parameters = analysis.get("test_parameters", {})
            print(f"SpecGenerator: Test parameters from LLM: {list(test_parameters.keys())}")
            print(f"SpecGenerator: IFC file path in test params: {test_parameters.get('ifc_file_path', 'NOT_FOUND')}")
            
            result = AnalysisResult(
                tool_requirement=tool_requirement,
                ifc_dependencies=ifc_dependencies,
                test_parameters=test_parameters,
                reasoning=analysis.get("reasoning", "Step analysis completed successfully")
            )
            
            
            print(f"SpecGenerator: Analysis completed successfully")
            return result
            
        except Exception as e:
            print(f"SpecGenerator: Analysis failed - {e}")
            raise RuntimeError(f"Step analysis failed: {e}")
    
    def _get_blackboard_data(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Get current step and execution history from blackboard"""
        if not hasattr(self, '_blackboard') or not self._blackboard:
            print("SpecGenerator: No blackboard available, using empty context")
            return {}, []
        
        # Get current step information
        current_step_index = self.blackboard.current_step_index
        current_plan = self.blackboard.current_plan
        current_step = {}
        
        if current_plan and "steps" in current_plan:
            steps = current_plan["steps"]
            if 0 <= current_step_index < len(steps):
                current_step = steps[current_step_index]
                print(f"SpecGenerator: Retrieved current step {current_step_index + 1}/{len(steps)}")
            else:
                print(f"SpecGenerator: Step index {current_step_index} out of range")
        
        # Get execution history
        execution_history = self.blackboard.step_execution_history
        print(f"SpecGenerator: Retrieved {len(execution_history)} execution history entries")
        
        return current_step, execution_history
    
    def _get_ifc_file_path(self) -> str:
        """Get real IFC file path from blackboard"""
        if hasattr(self, '_blackboard') and self._blackboard:
            ifc_file_path = self.get_ifc_file_path()
            print(f"SpecGenerator: Retrieved IFC file path from blackboard: {ifc_file_path}")
            return ifc_file_path
        else:
            print("SpecGenerator: Warning - No blackboard available, using empty IFC path")
            return ""
    
    def _llm_analyze_step_requirements(self, step_content: str, current_step: Dict[str, Any] = None, 
                                     execution_history: List[Dict[str, Any]] = None, ifc_file_path: str = "") -> Dict[str, Any]:
        
        # Build context from current step and execution history
        context_info = ""
        if current_step:
            context_info += f"\nCURRENT STEP CONTEXT:\n{json.dumps(current_step, indent=2)}\n"
        
        if execution_history:
            history_summary = []
            for i, step in enumerate(execution_history[-3:]):  # Last 3 steps
                if step.get("step_status") == "success":
                    summary = {
                        "step_index": step.get("step_index", i),
                        "description": step.get("step", {}).get("description", ""),
                        "tool_results_count": len(step.get("tool_results", [])),
                        "key_results": [result.get("result", "") for result in step.get("tool_results", [])][:2]
                    }
                    history_summary.append(summary)
            
            if history_summary:
                context_info += f"\nEXECUTION HISTORY (last {len(history_summary)} successful steps):\n{json.dumps(history_summary, indent=2)}\n"
        
        prompt = f"""
        Analyze the execution step and generate comprehensive tool requirement specification with three outputs:
        1. ToolRequirement - for code generation
        2. IFC dependencies - for data availability checking  
        3. Test parameters - function parameters for testing (simple key-value pairs)
        
        EXECUTION STEP: {step_content}
        {context_info}
        
        REAL IFC FILE PATH: {ifc_file_path}
        
        Based on the step description and context, generate a tool specification for IFC file processing.
        Use the real IFC file path provided above in test parameters.
        
        Return JSON in this exact format:
        {{
            "tool_requirement": {{
                "description": "Clear description of what the tool should do",
                "function_name": "snake_case_function_name",
                "parameters": [
                    {{"name": "ifc_file_path", "type": "str", "description": "Path to IFC file"}},
                    {{"name": "param2", "type": "str", "description": "Additional parameter if needed"}}
                ],
                "return_type": "Dict[str, Any]",
                "examples": [
                    "function_name('path.ifc', 'param') -> {{'result': 'success', 'data': [...]}}"
                ]
            }},
            "ifc_dependencies": {{
                "IfcWall": ["Thickness", "Height"],
                "IfcDoor": ["Width", "Height"]
            }},
            "test_parameters": {{
                "ifc_file_path": "{ifc_file_path}",
                "param2": "example_value"
            }},
            "reasoning": "Explanation of why this tool design was chosen based on current step and execution history"
        }}
        
        Guidelines:
        - Analyze execution history to determine what data might be available for testing
        - Choose commonly used IFC element types (IfcWall, IfcDoor, IfcWindow, etc.)
        - Specify commonly available properties (Width, Height, Thickness, etc.)
        - Test parameters should contain all function parameter values including ifc_file_path
        - Keep the tool focused and simple
        - Function name should be descriptive and snake_case
        - Return type should be informative (usually Dict[str, Any])
        - Consider context from previous steps when designing the tool
        """
        
        try:
            response = self.llm_client.generate_response(prompt)
            analysis = json.loads(response)
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response: {e}")
            raise RuntimeError(f"Failed to parse LLM response: {e}")
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            raise RuntimeError(f"LLM analysis failed: {e}")
    