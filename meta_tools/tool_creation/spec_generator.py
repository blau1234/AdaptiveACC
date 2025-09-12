
from utils.llm_client import LLMClient
from data_models.shared_models import ToolRequirement


class SpecGenerator:
    
    def __init__(self):
        pass
        self.llm_client = LLMClient()
    
    def analyze_step(self, step_content: str) -> ToolRequirement:
       
        print(f"SpecGenerator: Analyzing step - {step_content[:50]}...")
            
        # Build context 
        context_info = ""
     
        prompt = f"""
        Analyze the execution step and generate comprehensive tool requirement for code generation
        
        EXECUTION STEP: {step_content}
        {context_info}
        
        Based on the step description and context, generate a tool specification for IFC file processing.
        
        LIBRARY SELECTION:
        Choose the primary Python library this tool will use based on the task:
        - "ifcopenshell" - For IFC file processing, building element analysis, property extraction
        
        Guidelines:
        - Choose commonly used IFC element types (IfcWall, IfcDoor, IfcWindow, etc.)
        - Specify commonly available properties (Width, Height, Thickness, etc.)
        - Keep the tool focused and simple
        - Function name should be descriptive and snake_case
        - Consider context from previous steps when designing the tool
        - Select the most appropriate library based on the tool's primary function
        """
        
        try:
            response = self.llm_client.generate_response(prompt, response_model=ToolRequirement)
            print(f"SpecGenerator:  ToolRequirement generated")
            return response

        except Exception as e:
            print(f"SpecGenerator: Analysis failed - {e}")
            raise RuntimeError(f"Step analysis failed: {e}")
