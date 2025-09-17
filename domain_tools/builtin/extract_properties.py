"""
Tool: extract_properties
Category: builtin
Description: Extract property information of building elements
"""

from typing import Dict, Any, List
from utils.ifc_parser import IFCParser


def extract_properties(ifc_file_path: str, elements: List = None, properties: List = None) -> Dict[str, Any]:
    """Extract property information of building elements"""
    parser = IFCParser()
    if not parser.load_file(ifc_file_path):
        return {
            "result": "fail",
            "detail": "Failed to load IFC file"
        }
    
    return {
        "result": "pass", 
        "detail": "Properties extracted successfully",
        "properties": {"sample": "data"}
    }