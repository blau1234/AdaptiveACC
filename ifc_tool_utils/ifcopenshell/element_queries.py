"""
Element Queries - Atomic functions for basic IFC element operations

These functions provide fundamental element query operations that return
native ifcopenshell objects or basic Python types.
"""

import ifcopenshell
from typing import List, Optional, Union


def get_elements_by_type(ifc_file: ifcopenshell.file, element_type: str) -> List[ifcopenshell.entity_instance]:
    """Get all elements of specified IFC type.

    Args:
        ifc_file: Open IFC file instance
        element_type: IFC type string (e.g., "IfcWall", "IfcDoor")

    Returns:
        List of IFC element instances
    """
    if not ifc_file:
        return []
    return ifc_file.by_type(element_type)


def get_element_by_id(ifc_file: ifcopenshell.file, global_id: str) -> Optional[ifcopenshell.entity_instance]:
    """Get element by GlobalId.

    Args:
        ifc_file: Open IFC file instance
        global_id: Element's GlobalId

    Returns:
        IFC element instance or None if not found
    """
    if not ifc_file:
        return None
    try:
        return ifc_file.by_guid(global_id)
    except RuntimeError:
        return None


def get_element_guid(element: ifcopenshell.entity_instance) -> str:
    """Get element's GlobalId.

    Args:
        element: IFC element instance

    Returns:
        GlobalId string
    """
    if not element or not hasattr(element, 'GlobalId'):
        return ""
    return element.GlobalId


def get_element_name(element: ifcopenshell.entity_instance) -> str:
    """Get element's name.

    Args:
        element: IFC element instance

    Returns:
        Element name or empty string if not available
    """
    if not element:
        return ""
    if hasattr(element, 'Name') and element.Name:
        return element.Name
    return ""


def get_element_type_name(element: ifcopenshell.entity_instance) -> str:
    """Get element's IFC type name.

    Args:
        element: IFC element instance

    Returns:
        IFC type string (e.g., "IfcWall")
    """
    if not element:
        return ""
    return element.is_a()


def get_element_description(element: ifcopenshell.entity_instance) -> str:
    """Get element's description.

    Args:
        element: IFC element instance

    Returns:
        Element description or empty string if not available
    """
    if not element:
        return ""
    if hasattr(element, 'Description') and element.Description:
        return element.Description
    return ""


def get_elements_by_ids(ifc_file: ifcopenshell.file, global_ids: List[str]) -> List[ifcopenshell.entity_instance]:
    """Get multiple elements by their GlobalIds.

    Args:
        ifc_file: Open IFC file instance
        global_ids: List of GlobalId strings

    Returns:
        List of found IFC element instances (excludes not found elements)
    """
    elements = []
    for global_id in global_ids:
        element = get_element_by_id(ifc_file, global_id)
        if element:
            elements.append(element)
    return elements


