"""
Tool: get_elements_by_type
Category: builtin
Description: Extract building elements of specified type from IFC files
"""

from typing import Dict, Any
from utils.ifc_parser import IFCParser


def get_elements_by_type(ifc_file_path: str, element_type: str = "IfcWall") -> Dict[str, Any]:
    """Extract building elements of specified type from IFC files"""
    parser = IFCParser()
    if not parser.load_file(ifc_file_path):
        return {
            "result": "fail",
            "detail": "Failed to load IFC file",
            "elements_checked": [],
            "issues": ["IFC file loading failed"]
        }
    
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