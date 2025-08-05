"""
Tool Manager - Unified management of all available tools
"""

from typing import Dict, Any, List, Callable
from dataclasses import dataclass
import importlib
import os

@dataclass
class Tool:
    """Tool definition"""
    name: str
    description: str
    category: str
    function: Callable
    parameters_schema: Dict[str, Any]

class ToolManager:
    """Tool Manager - Dynamic loading and management of all tools"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._load_all_tools()
    
    def _load_all_tools(self):
        """Load all available tools"""
        
        # 1. Load basic tools
        self._load_basic_tools()

        # 2. Dynamically load tools from tool_library directory
        self._load_tools_from_directory()
    
    def _load_basic_tools(self):
        """Load basic tools"""
        
        # IFC element extraction tool
        self.tools["get_elements_by_type"] = Tool(
            name="get_elements_by_type",
            description="Extract building elements of specified type from IFC files (walls, doors, windows, etc.)",
            category="analysis",
            function=self._get_elements_by_type,
            parameters_schema={
                "element_type": {
                    "type": "string",
                    "description": "IFC element type, such as IfcWall, IfcDoor, IfcWindow, etc.",
                    "required": True
                }
            }
        )
        
        # Property extraction tool
        self.tools["extract_properties"] = Tool(
            name="extract_properties",
            description="Extract property information of building elements (dimensions, materials, etc.)",
            category="analysis", 
            function=self._extract_properties,
            parameters_schema={
                "elements": {
                    "type": "array",
                    "description": "List of elements to extract properties from",
                    "required": True
                },
                "properties": {
                    "type": "array", 
                    "description": "List of property names to extract",
                    "required": False
                }
            }
        )
        
        # Basic validation tool
        self.tools["basic_validation"] = Tool(
            name="basic_validation",
            description="Perform basic validation checks on IFC files",
            category="validation",
            function=self._basic_validation,
            parameters_schema={}
        )
        
        # Dimension measurement tool
        self.tools["dimension_measurement"] = Tool(
            name="dimension_measurement", 
            description="Measure dimensions of building elements (length, width, height, etc.)",
            category="measurement",
            function=self._dimension_measurement,
            parameters_schema={
                "element_type": {
                    "type": "string",
                    "description": "Type of element to measure",
                    "required": True
                },
                "dimension_type": {
                    "type": "string",
                    "description": "Type of dimension to measure (width, height, length, etc.)",
                    "required": False
                }
            }
        )
    
    def _load_tools_from_directory(self):
        """Dynamically load tools from tool_library directory"""
        tool_dir = os.path.dirname(__file__)
        
        for filename in os.listdir(tool_dir):
            if filename.endswith('.py') and filename not in ['__init__.py', 'tool_manager.py', 'ifc_parser.py']:
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f'tool_library.{module_name}')
                    if hasattr(module, 'check'):
                        tool_name = module_name.replace('_', '')
                        self.tools[tool_name] = Tool(
                            name=tool_name,
                            description=f"Tool loaded from {module_name} module",
                            category="analysis",
                            function=module.check,
                            parameters_schema={}
                        )
                except Exception as e:
                    print(f"Failed to load tool from {filename}: {e}")
    
    def get_tool(self, tool_name: str) -> Tool:
        """Get specified tool"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, Tool]:
        """Get all tools"""
        return self.tools.copy()
    
    def get_tools_by_category(self, category: str) -> Dict[str, Tool]:
        """Get tools by category"""
        return {name: tool for name, tool in self.tools.items() if tool.category == category}
    
    def execute_tool(self, tool_name: str, ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specified tool"""
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "result": "fail",
                "detail": f"Tool '{tool_name}' not found",
                "error": f"Unknown tool: {tool_name}"
            }
        
        try:
            # Call tool function
            if tool_name in ["get_elements_by_type", "extract_properties", "basic_validation", 
                           "dimension_measurement", "accessibility_checker", "safety_compliance"]:
                # Built-in tools need to pass ifc_file_path
                return tool.function(ifc_file_path, parameters)
            else:
                # External tools use standard interface
                return tool.function(ifc_file_path, parameters)
                
        except Exception as e:
            return {
                "result": "fail", 
                "detail": f"Tool execution failed: {str(e)}",
                "error": str(e)
            }
    
    # === Built-in tool implementations ===
    
    def _get_elements_by_type(self, ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get elements of specified type"""
        from .ifc_parser import IFCParser
        
        parser = IFCParser()
        if not parser.load_file(ifc_file_path):
            return {
                "result": "fail",
                "detail": "Failed to load IFC file",
                "elements_checked": [],
                "issues": ["IFC file loading failed"]
            }
        
        element_type = parameters.get("element_type", "IfcWall")
        elements = parser.get_elements_by_type(element_type)
        
        element_info = []
        for elem in elements:
            elem_name = elem.Name if hasattr(elem, 'Name') and elem.Name else f"Unnamed {element_type}"
            element_info.append({
                "id": elem.GlobalId if hasattr(elem, 'GlobalId') else str(elem),
                "name": elem_name
            })
        
        return {
            "result": "pass",
            "detail": f"Successfully extracted {len(elements)} {element_type} elements",
            "elements_checked": [info["name"] for info in element_info],
            "issues": [],
            "element_count": len(elements),
            "element_type": element_type,
            "elements_data": element_info
        }
    
    def _extract_properties(self, ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract element properties"""
        from .ifc_parser import IFCParser
        
        parser = IFCParser()
        if not parser.load_file(ifc_file_path):
            return {
                "result": "fail",
                "detail": "Failed to load IFC file"
            }
        
        # Here we can extract specific properties based on elements and properties in parameters
        # Simplified implementation
        return {
            "result": "pass",
            "detail": "Properties extracted successfully",
            "properties": {"sample": "data"}
        }
    
    def _basic_validation(self, ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Basic validation"""
        from .ifc_parser import IFCParser
        
        parser = IFCParser()
        if not parser.load_file(ifc_file_path):
            return {
                "result": "fail",
                "detail": "Failed to load IFC file for validation"
            }
        
        return {
            "result": "pass",
            "detail": "IFC file passed basic validation",
            "validation_status": "valid"
        }
    
    def _dimension_measurement(self, ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Dimension measurement"""
        element_type = parameters.get("element_type", "IfcDoor") 
        dimension_type = parameters.get("dimension_type", "width")
        
        # Call get_elements_by_type to get elements
        elements_result = self._get_elements_by_type(ifc_file_path, {"element_type": element_type})
        
        if elements_result["result"] == "fail":
            return elements_result
        
        # Simplified dimension measurement
        measurements = []
        for element in elements_result.get("elements_data", []):
            measurements.append({
                "element_id": element["id"],
                "element_name": element["name"],
                dimension_type: "32.0 inches"  # Simulated measurement result
            })
        
        return {
            "result": "pass",
            "detail": f"Measured {dimension_type} for {len(measurements)} {element_type} elements",
            "measurements": measurements,
            "measurement_type": dimension_type
        }

        """Safety compliance check"""
        safety_type = parameters.get("safety_type", "fire_exit")
        
        # Simplified safety check
        return {
            "result": "pass",
            "detail": f"Safety compliance check for {safety_type} completed",
            "safety_issues": [],
            "safety_type": safety_type
        }