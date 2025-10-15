from utils.llm_client import LLMClient
from models.common_models import ToolSpec


class SpecGenerator:
    """Agent to generate ToolSpec based on task description"""

    def __init__(self):
        self.llm_client = LLMClient()

    def generate_spec(self, task_description: str) -> ToolSpec:
        """Generate a ToolSpec based on the provided task description

        Args:
            task_description: Description of what the tool should do

        Returns:
            ToolSpec for tool creation
        """

        system_prompt = """You are an expert Python developer specializing in IFC (Industry Foundation Classes) file processing and building compliance checking.
        Your task is to analyze the current task requirements and generate precise tool specifications for automated code generation.

        CORE RESPONSIBILITIES:
        - Analyze step requirements comprehensively
        - Generate accurate ToolSpec with appropriate parameters
        - Select optimal libraries for the specific task
        - Consider building regulation compliance context
        - Ensure tools are focused, efficient, and reusable

        ## CRITICAL: SIMPLICITY FIRST
        - Generate tools that do ONE thing well
        - If task description mentions multiple approaches (e.g., "property sets, geometry, or other sources"),
          CHOOSE THE MOST DIRECT ONE (usually property sets for attributes)
        - Ignore vague phrases like "or any other relevant information", "or any other sources"
        - Focus on the PRIMARY data source mentioned
        - Priority: property sets > geometry > relationships

        TOOLSPEC GENERATION GUIDELINES:

        1. FUNCTION NAMING (avoid duplicate tools):
        - Use three-part naming: {action}_{target}_{attribute}
          * action(required): Main operation of the tool. e.g. extract/validate/calculate/check/get/find/list
          * target(required): Object the tool acts on. e.g.wall/door/window/space/element/property
          * attribute_or_rule (optional but recommended): The specific property, attribute, or rule the tool handles. e.g. thickness, width, height, area, count, compliance, fire_rating, consistency, adjacency
        
        - Examples: extract_wall_thickness, validate_door_width, calculate_space_area
        - Keep names concise and readable
        - Use consistent naming patterns for similar functionality, differentiate by specific attributes
       
        2. PARAMETER DESIGN:
        - Always include 'ifc_file_path: str' as first parameter for IFC operations
        - Use specific parameter names (e.g., 'element_id: str', 'property_name: str')
        - Include type hints for all parameters: str, int, float, List[str], Dict[str, Any]
        - Add meaningful descriptions explaining expected values

        3. RETURN TYPE SELECTION:
        - Simple values: str, int, float, bool
        - Collections: List[str], List[Dict[str, Any]], Dict[str, Any]
        - Use Dict[str, Any] for complex structured results

        4. LIBRARY SELECTION:
        - "ifcopenshell" - Primary choice for IFC file processing, element extraction, property access
        - Choose based on the primary function of the tool
        """

        user_prompt = f"""Generate a ToolSpec for the following task:

        TASK DESCRIPTION:
        {task_description}

        Generate a ToolSpec that:
        1. Addresses the specific task requirements
        2. Uses appropriate IFC processing techniques
        3. Considers the compliance checking context
        4. Produces clear, structured output

        Create a focused, single-purpose tool that efficiently accomplishes the task objective."""

        try:
            response = self.llm_client.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_model=ToolSpec
            )
            print(f"SpecGenerator: ToolSpec generated - {response.function_name}")
            return response

        except Exception as e:
            print(f"SpecGenerator: Analysis failed - {e}")
            raise RuntimeError(f"Step analysis failed: {e}")

