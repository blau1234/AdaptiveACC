"""
Extract Building Elements Tool
从IFC文件中提取所有建筑元素（墙、门、窗、板等）
"""

from typing import Dict, Any
from .ifc_parser import IFCParser


def check(ifc_file_path: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    从IFC文件中提取所有建筑元素
    
    Args:
        ifc_file_path: IFC文件路径
        parameters: 可选参数 (目前未使用)
        
    Returns:
        Dict: 提取结果
    """
    parser = IFCParser()
    
    if not parser.load_file(ifc_file_path):
        return {
            "result": "fail",
            "detail": "Failed to load IFC file",
            "elements_checked": [],
            "issues": ["IFC file loading failed"]
        }
    
    # 使用get_elements_by_type方法提取建筑元素
    element_types = ["IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcColumn", "IfcBeam", "IfcSpace"]
    elements = {}
    
    for element_type in element_types:
        elements[element_type.lower().replace("ifc", "")] = parser.get_elements_by_type(element_type)
    
    element_counts = {key: len(value) for key, value in elements.items()}
    
    return {
        "result": "pass",
        "detail": f"Successfully extracted building elements: {element_counts}",
        "elements_checked": list(elements.keys()),
        "issues": [],
        "building_elements": elements,
        "element_counts": element_counts
    }