import json
from typing import List, Tuple, Optional
from utils.llm_client import LLMClient
from models.common_models import RetrievedDocument, ToolSpec, ToolCreatorOutput, ToolMetadata, ToolParam, IFCToolResult, FixedCodeOutput


class CodeGenerator:
    """Agent to generate Python code based on ToolSpec and relevant documentation"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    

    def generate_code(self, tool_spec: ToolSpec, relevant_docs: List[RetrievedDocument]) -> ToolCreatorOutput:
        """Generate complete tool with structured output using instructor"""

        system_prompt = """You are an expert Python developer specializing in IFC file processing and building compliance checking.
        Your task is to generate complete, production-ready Python functions based on precise tool specifications.

        ## CORE RESPONSIBILITIES:
        - Generate complete, runnable Python functions with a proper structure
        - Follow IFC processing best practices
        - Implement comprehensive and consistent error handling as defined below.
        - Create accurate metadata describing the tool

        ## AVAILABLE STANDARD LIBRARY FUNCTIONS:
        You have access to a rich utility library. To ensure you select the most appropriate function, find the function you need under the relevant category below.
        Pay close attention to the return types and comments, as they indicate how functions behave on failure (e.g., returning `None`).

        ### 1. File & Model Operations
        - `ifcopenshell.open(file_path)` - Opens an IFC file and returns an IFC file object. **Always use this to load IFC files.**

        ### 2. Element & Property Queries
        *From `ifc_tool_utils.ifcopenshell.element_queries`*:
        - `get_element_by_id(ifc_file, global_id: str) -> element | None`
          Returns None if the ID is not found.
        - `get_elements_by_type(ifc_file, element_type: str) -> List[element]`
          Returns an empty list if no elements of that type are found.
        - `get_elements_by_ids(ifc_file, global_ids: List[str]) -> List[element]`
          Returns list of found elements (excludes not found elements).
        - `get_element_guid(element) -> str`
          Returns GlobalId string or empty string if not available.
        - `get_element_name(element) -> str`
          Returns element name or empty string if not available.
        - `get_element_description(element) -> str`
          Returns element description or empty string if not available.
        - `get_element_type_name(element) -> str`
          Returns IFC type string (e.g., "IfcWall").

        *From `ifc_tool_utils.ifcopenshell.property_queries`*:
        - `get_basic_property(element, property_name: str) -> Any | None`
          For simple properties directly on the element. Returns None if not found.
        - `get_pset_property(element, pset_name: str, property_name: str) -> Any | None`
          Returns None if the PropertySet or the property is not found.
        - `get_all_psets(element) -> Dict[str, Dict[str, Any]]`
          Returns dict mapping property set names to nested dicts of {property_name: value}. Returns empty dict {} if no property sets.
        - `get_quantity_value(element, quantity_name: str) -> float | None`
          Returns quantity value from IfcElementQuantity. Returns None if not found.

        ### 3. Geometry Queries
        *From `ifc_tool_utils.ifcopenshell.geometry_queries`*:
        - `get_element_dimensions(element) -> Dict[str, Optional[float]]`
          Returns dict with keys: 'width', 'height', 'length', 'depth', 'overallwidth', 'overallheight'. Values are floats or None. Returns empty dict {} if element is None.
        - `get_element_location(element) -> Dict[str, Any]`
          Returns dict with keys: 'coordinates' (list of [x, y, z]), 'direction' (list of direction ratios). Returns empty dict {} if no ObjectPlacement.
        - `get_bounding_box(element) -> Dict[str, Any]`
          Returns dict with keys: 'min_x', 'min_y', 'min_z', 'max_x', 'max_y', 'max_z'. Returns empty dict {} if geometry processing fails.
        - `calculate_area(element) -> float | None`
          Calculates area in model units. Prioritizes IfcElementQuantity AreaValue, falls back to bounding box estimation. Returns None if both fail.
        - `calculate_volume(element) -> float | None`
          Calculates volume in model units. Prioritizes IfcElementQuantity VolumeValue, falls back to bounding box estimation. Returns None if both fail.
        - `get_geometry_representation(element) -> Dict[str, Any]`
          Returns dict with key 'representations': list of dicts with metadata. Returns empty dict {} if no Representation attribute.
        - `get_placement_matrix(element) -> List[List[float]]`
          Returns 4x4 transformation matrix as nested list. Returns empty list [] if processing fails.
        - `calculate_distance_between_elements(element1, element2) -> float | None`
          Calculates 3D Euclidean distance between element placement centers. Returns None if either element lacks ObjectPlacement.

        ### 4. Relationship & Topology Queries
        *From `ifc_tool_utils.ifcopenshell.relationship_queries`*:
        - `get_spatial_container(element) -> element | None`
          Get the IfcBuildingStorey/IfcSpace that contains this element. Returns None if not found.
        - `get_contained_elements(spatial_element) -> List[element]`
          Get all elements within an IfcBuildingStorey/IfcSpace. Returns empty list if none found.
        - `get_host_element(filling_element) -> element | None`
          Get the IfcWall that an IfcDoor/IfcWindow fills. Returns None if not found.
        - `get_filling_elements(host_element) -> List[element]`
          Get all IfcDoor/IfcWindow elements inside an IfcWall. Returns empty list if none found.
        - `get_connected_elements(element, relation_type: str = None) -> List[element]`
          Get elements connected to this element. Optional relation_type filter (e.g., "IfcRelConnectsPathElements"). Returns empty list if none found.
        - `get_aggregated_elements(aggregate_element) -> List[element]`
          Get elements aggregated by this element (via IfcRelAggregates). Returns empty list if none found.
        - `get_decomposing_element(element) -> element | None`
          Get the element that decomposes/aggregates this element. Returns None if not found.
        - `find_relationship(element1, element2, relationship_type: str = None) -> relationship | None`
          Find relationship between two elements. Optional relationship_type filter. Returns None if not found.
        - `get_assigned_elements(assigning_element, assignment_type: str = None) -> List[element]`
          Get elements assigned to this element. Optional assignment_type filter. Returns empty list if none found.
        - `get_space_boundaries(ifc_file, space: element = None, boundary_type: str = None) -> List[boundary]`
          Get IfcRelSpaceBoundary relationships. Optional space filter and boundary_type filter ('INTERNAL' or 'EXTERNAL'). Returns empty list if none found.
        - `get_space_boundary_info(boundary) -> Dict[str, Any]`
          Extract structured info from IfcRelSpaceBoundary. Returns dict with keys: 'boundary_id', 'space_id', 'element_id', 'element_type', 'physical_virtual', 'internal_external'.
        - `find_adjacent_spaces_via_boundaries(ifc_file, space) -> List[element]`
          Find spaces adjacent to given space by analyzing shared INTERNAL boundary elements. Returns empty list if none found.

        ### 5. Shapely 2D Geometry Operations
        *From `ifc_tool_utils.shapely.geometry_utils`*:
        - `ifc_to_shapely_polygon(ifc_element) -> Polygon | None`
          Convert IFC element to Shapely 2D polygon using bounding box projection on XY plane. Returns Polygon with 4 corner points. Returns None if conversion fails.
        - `calculate_minimum_distance(geom1: Polygon, geom2: Polygon) -> float`
          Calculate minimum 2D surface-to-surface distance between geometries in XY plane (ignores Z-axis). Returns float in coordinate units. Returns inf if calculation fails.
        - `get_polygon_bounds(polygon: Polygon) -> Tuple[float, float, float, float]`
          Get 2D bounding box. Returns tuple of (min_x, min_y, max_x, max_y). Returns (0.0, 0.0, 0.0, 0.0) if operation fails.

        ### 6. Trimesh 3D Mesh Operations
        *From `ifc_tool_utils.trimesh.mesh_utils`*:
        - `ifc_to_trimesh(ifc_element) -> trimesh.Trimesh | None`
          Convert IFC element to Trimesh 3D box mesh using bounding box approximation. Returns Trimesh object with 8 vertices and 12 triangular faces. Returns None if conversion fails.
        - `calculate_minimum_vertical_distance(lower_mesh: trimesh.Trimesh, upper_meshes: List[trimesh.Trimesh]) -> float`
          Calculate minimum vertical clearance between lower mesh top and upper meshes bottom. Pure Z-axis distance (ignores XY position). Returns float in model units. Returns inf if upper_meshes is empty, 0.0 if negative distance.
        - `get_mesh_bounds(mesh: trimesh.Trimesh) -> Tuple[float, float, float, float, float, float]`
          Get 3D bounding box. Returns tuple of (min_x, min_y, min_z, max_x, max_y, max_z). Returns (0.0, 0.0, 0.0, 0.0, 0.0, 0.0) if operation fails.
        - `create_mesh_from_vertices_faces(vertices: np.ndarray, faces: np.ndarray) -> trimesh.Trimesh | None`
          Create Trimesh mesh from raw vertex coordinates (N, 3) and face indices (M, 3). Returns Trimesh object or None if creation fails.

        USAGE EXAMPLES:

        **Basic IFC Property Extraction:**
        ```python
        import ifcopenshell
        from ifc_tool_utils.ifcopenshell import get_element_by_id, get_all_psets

        def my_tool(ifc_file_path: str, element_id: str):
            ifc_file = ifcopenshell.open(ifc_file_path)
            element = get_element_by_id(ifc_file, element_id)
            psets = get_all_psets(element)
            return {"element_id": element_id, "psets": psets}
        ```

        **2D Distance Analysis with Shapely:**
        ```python
        import ifcopenshell
        from ifc_tool_utils.ifcopenshell import get_element_by_id, get_elements_by_type
        from ifc_tool_utils.shapely import ifc_to_shapely_polygon, calculate_minimum_distance

        def calculate_door_clearance(ifc_file_path: str, door_id: str):
            ifc_file = ifcopenshell.open(ifc_file_path)
            door = get_element_by_id(ifc_file, door_id)
            walls = get_elements_by_type(ifc_file, "IfcWall")

            door_polygon = ifc_to_shapely_polygon(door)
            min_distance = float('inf')

            for wall in walls:
                wall_polygon = ifc_to_shapely_polygon(wall)
                distance = calculate_minimum_distance(door_polygon, wall_polygon)
                min_distance = min(min_distance, distance)

            return {"door_id": door_id, "min_clearance": min_distance}
        ```

        **3D Vertical Clearance with Trimesh:**
        ```python
        import ifcopenshell
        from ifc_tool_utils.ifcopenshell import get_element_by_id, get_elements_by_type
        from ifc_tool_utils.trimesh import ifc_to_trimesh, calculate_minimum_vertical_distance

        def check_ceiling_height(ifc_file_path: str, space_id: str):
            ifc_file = ifcopenshell.open(ifc_file_path)
            space = get_element_by_id(ifc_file, space_id)
            slabs = get_elements_by_type(ifc_file, "IfcSlab")

            space_mesh = ifc_to_trimesh(space)
            slab_meshes = [ifc_to_trimesh(slab) for slab in slabs]

            clearance = calculate_minimum_vertical_distance(space_mesh, slab_meshes)
            return {"space_id": space_id, "ceiling_clearance": clearance}
        ```

        ## STRUCTURED OUTPUT REQUIREMENTS:
        You must provide a JSON object with the following keys:
        1. tool_name: The function name from the specification.
        2. code: A string containing the complete, executable Python function code.
        3. metadata: A dictionary containing detailed tool metadata:
            - ifc_tool_name: Tool name (must match the function name).
            - description: A clear, concise description of what the tool does.
            - parameters: A list of parameter objects (dictionaries), each with name, type, description, required, and default.
            - return_type: The expected Python return type.
            - category: Choose from: "attributes", "topological_and_relational", "element_selection", "aggregation", "quantification", "derived_geometric", "others".
            - tags: A list of relevant keywords for search and discovery.

        ## CODE QUALITY REQUIREMENTS:
        - Imports & Typing: Include proper imports from the specified libraries and use full type hints.
        - Style: Follow PEP 8 style guidelines.
        - Docstrings: Add comprehensive docstrings following the Google Python Style Guide, including Args, Returns, and a simple Example section.
        - Error Handling Policy:  
            * If an expected element, property, or value is not found, the function should return a sensible default (None, [], {}) rather than raising an exception. 
            * Exceptions should only be raised for critical errors like an invalid ifc_file_path. 
            * Your code must handle None return values from the utility functions.
        - Dependency Policy: Only use the Python standard library and the provided ifc_tool_utils and utils.ifc_file_manager modules. Do not import any other third-party libraries (e.g., pandas, numpy) unless explicitly instructed.
        - Preference: STRONGLY PREFER using the standard library functions listed above instead of reimplementing logic.
        """

        # Process relevant documentation
        docs_context = ""
        if relevant_docs:
            docs_context = "RELEVANT DOCUMENTATION:\n"
            for i, doc in enumerate(relevant_docs, 1):
                docs_context += f"Document {i} (relevance: {doc.relevance_score:.3f}):\n"
                docs_context += f"{doc.content}...\n\n"

        # Format parameters for prompt
        param_descriptions = []
        for param in tool_spec.parameters:
            param_descriptions.append(f"- {param['name']}: {param['type']} - {param.get('description', 'No description')}")

        prompt = f"""
        {docs_context}

        TOOL SPECIFICATION:
        Function name: {tool_spec.function_name}
        Description: {tool_spec.description}
        Primary Library: {tool_spec.library}
        Return type: {tool_spec.return_type}

        Parameters:
        {chr(10).join(param_descriptions)}

        Generate a complete tool implementation with all required metadata.
        The generated function should use {tool_spec.library} as the primary library.
        """

        try:
            tool_output = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                response_model=ToolCreatorOutput,
                max_retries=3
            )
            return tool_output

        except Exception as e:
            print(f"LLM structured tool generation failed: {e}")
            return None


    def fix_code(self, code: str, check_result: IFCToolResult, metadata: ToolMetadata) -> str:
        """Fix code errors, focusing on the code itself"""

        system_prompt = """You are an expert Python developer specializing in IFC file processing and building compliance checking.
        Your task is to fix Python code issues while maintaining the original functionality.

        CORE RESPONSIBILITIES:
        - Analyze the specific error type and context
        - Fix the root cause of the error
        - Maintain original function signature and behavior
        - Follow IFC processing best practices
        - Implement comprehensive error handling

        CODE QUALITY REQUIREMENTS:
        - Include proper imports and type hints
        - Follow PEP 8 style guidelines
        - Add comprehensive docstrings with parameter descriptions
        - Implement robust error handling with meaningful messages
        - Validate input parameters and handle edge cases
        - Use appropriate data structures for return values
        - All comments and docstrings must be in English

        OUTPUT FORMAT:
        - Return the corrected code and a brief summary of changes made
        - Focus on fixing the specific error while preserving functionality"""

        # Build error context based on exception type
        error_context = self._build_error_context(check_result)

        user_prompt = f"""Fix the Python code based on the following error information:

        ERROR DETAILS:
        - Tool Name: {check_result.ifc_tool_name}
        - Error Type: {check_result.exception_type or 'Unknown'}
        - Error Message: {check_result.error_message or 'No error message'}
        {f"- Line Number: {check_result.line_number}" if check_result.line_number else ""}

        {error_context}

        CURRENT CODE:
        {code}

        TOOL METADATA:
        - Function Name: {check_result.ifc_tool_name}
        - Description: {metadata.description}
        - Parameters: {[param.model_dump() for param in metadata.parameters]}
        - Return Type: {metadata.return_type}
        - Category: {metadata.category}

        Fix the error while maintaining the original functionality and requirements."""

        try:
            fixed_output = self.llm_client.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_model=FixedCodeOutput,
                max_retries=3
            )

            return fixed_output.code

        except Exception as e:
            print(f"LLM code fixing failed: {e}")
            # Return original code if fixing fails
            return code

    def _build_error_context(self, check_result: IFCToolResult) -> str:
        """Build error-specific context for fixing"""

        context_map = {
            # Syntax errors
            "SyntaxError": "SYNTAX ERROR: Check for missing parentheses, brackets, quotes, or incorrect indentation.",
            "IndentationError": "INDENTATION ERROR: Fix inconsistent indentation, mixing tabs and spaces.",
            "TabError": "TAB ERROR: Ensure consistent use of tabs or spaces for indentation.",

            # Import errors
            "ImportError": "IMPORT ERROR: Fix import statements, check module names, or add missing dependencies.",
            "ModuleNotFoundError": "MODULE ERROR: The required module is not installed or the import path is incorrect. Consider alternative imports or add proper imports.",

            # Runtime errors
            "NameError": "NAME ERROR: The variable or function name is not defined. Check for typos or missing imports.",
            "TypeError": "TYPE ERROR: Fix type mismatches, incorrect argument types, or missing/extra arguments.",
            "AttributeError": "ATTRIBUTE ERROR: The object doesn't have the specified attribute or method. Check object type and available methods.",
            "ValueError": "VALUE ERROR: Fix invalid argument values or data conversion issues.",
            "RuntimeError": "RUNTIME ERROR: General runtime issue, check logic flow and error conditions.",

            # Logic errors
            "KeyError": "KEY ERROR: Dictionary key doesn't exist. Add key existence checks or use .get() method.",
            "IndexError": "INDEX ERROR: List/array index is out of range. Add bounds checking.",
            "AssertionError": "ASSERTION ERROR: An assertion failed. Check the assertion condition and fix the logic.",
        }

        error_type = check_result.exception_type or "Unknown"
        context = context_map.get(error_type, f"UNKNOWN ERROR ({error_type}): Analyze the error message and fix accordingly.")

        # Add traceback context if available
        if check_result.traceback:
            context += f"\n\nTRACEBACK ANALYSIS:\n{check_result.traceback[:500]}..."

        return context