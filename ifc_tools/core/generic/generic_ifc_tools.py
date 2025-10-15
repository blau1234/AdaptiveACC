"""
Generic IFC Tools
Category: core
Description: Flexible generic tools for IFC data exploration and extraction.
             These tools provide a high-level interface for common IFC queries
             and are designed to be used by agents for exploratory data analysis.
"""

from typing import Dict, Any, Optional, List
from ifc_tool_utils.ifcopenshell import (
    get_element_by_id, get_element_guid, get_element_name,
    get_element_type_name, get_all_psets
)
from ifc_tool_utils.ifcopenshell.relationship_queries import (
    get_spatial_container, get_host_element, get_connected_elements,
    get_filling_elements, get_contained_elements, get_aggregated_elements,
    get_decomposing_element
)
from utils.ifc_file_manager import IFCFileManager


def get_element_attributes(ifc_file_path: str, element_id: str) -> Dict[str, Any]:
    """Get all direct attributes of an element (Name, GlobalId, Description, etc).

    This function retrieves the basic attributes directly stored in the IFC element,
    not property sets. Use get_element_property_sets() to discover available property sets.

    Args:
        ifc_file_path: Path to the IFC file
        element_id: Element GlobalId

    Returns:
        Dictionary with element attributes including:
        - element_id: GlobalId of the element
        - name: Element name
        - type: IFC type (e.g., "IfcDoor", "IfcWall")
        - description: Element description (if available)
        - object_type: Object type classification (if available)
        - tag: Element tag (if available)

        Returns error dict if element not found.

    Example:
        result = get_element_attributes("model.ifc", "2O2Fr$t4X7Zf8NOew3FLOH")
        # Returns: {"element_id": "2O2Fr$t4X7Zf8NOew3FLOH", "name": "Door-01",
        #           "type": "IfcDoor", "description": "Main entrance door", ...}
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            element = get_element_by_id(ifc_file, element_id)
            if not element:
                return {"element_id": element_id, "error": "Element not found"}

            return {
                "element_id": get_element_guid(element),
                "name": get_element_name(element) or "",
                "type": get_element_type_name(element),
                "description": element.Description if hasattr(element, 'Description') else None,
                "object_type": element.ObjectType if hasattr(element, 'ObjectType') else None,
                "tag": element.Tag if hasattr(element, 'Tag') else None
            }
    except Exception as e:
        return {"element_id": element_id, "error": f"Failed to get attributes: {str(e)}"}


def get_element_property_sets(ifc_file_path: str, element_id: str) -> Dict[str, Any]:
    """Get all property set names for an element.

    This function returns only the names of property sets attached to an element.
    Use get_properties_in_pset() to retrieve actual property values.

    Args:
        ifc_file_path: Path to the IFC file
        element_id: Element GlobalId

    Returns:
        Dictionary with:
        - element_id: GlobalId of the element
        - pset_names: List of property set names (e.g., ["Pset_DoorCommon", "Pset_DoorWindowGlazingType"])

        Returns error dict if element not found.

    Example:
        result = get_element_property_sets("model.ifc", "2O2Fr$t4X7Zf8NOew3FLOH")
        # Returns: {"element_id": "2O2Fr$t4X7Zf8NOew3FLOH",
        #           "pset_names": ["Pset_DoorCommon", "Pset_DoorWindowGlazingType"]}
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            element = get_element_by_id(ifc_file, element_id)
            if not element:
                return {"element_id": element_id, "error": "Element not found"}

            psets = get_all_psets(element)
            return {
                "element_id": element_id,
                "pset_names": list(psets.keys())
            }
    except Exception as e:
        return {"element_id": element_id, "error": f"Failed to get property sets: {str(e)}"}


def get_properties_in_pset(ifc_file_path: str, element_id: str, pset_name: str) -> Dict[str, Any]:
    """Get all properties and values in a specific property set.

    This function retrieves all property names and values from a specified property set.
    Use get_element_property_sets() first to discover available property set names.

    Args:
        ifc_file_path: Path to the IFC file
        element_id: Element GlobalId
        pset_name: Property set name (e.g., "Pset_DoorCommon")

    Returns:
        Dictionary with:
        - element_id: GlobalId of the element
        - pset_name: Name of the property set
        - properties: Dict mapping property names to values

        Returns error dict if element or property set not found.

    Example:
        result = get_properties_in_pset("model.ifc", "2O2Fr$t4X7Zf8NOew3FLOH", "Pset_DoorCommon")
        # Returns: {"element_id": "2O2Fr$t4X7Zf8NOew3FLOH",
        #           "pset_name": "Pset_DoorCommon",
        #           "properties": {"FireRating": "FD30", "IsExternal": True, "GlazingAreaFraction": 0.7}}
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            element = get_element_by_id(ifc_file, element_id)
            if not element:
                return {"element_id": element_id, "error": "Element not found"}

            psets = get_all_psets(element)
            if pset_name not in psets:
                return {
                    "element_id": element_id,
                    "pset_name": pset_name,
                    "error": f"Property set '{pset_name}' not found. Available: {list(psets.keys())}"
                }

            return {
                "element_id": element_id,
                "pset_name": pset_name,
                "properties": psets[pset_name]
            }
    except Exception as e:
        return {"element_id": element_id, "pset_name": pset_name,
                "error": f"Failed to get properties: {str(e)}"}


def get_elements_by_type(ifc_file_path: str, element_type: str) -> Dict[str, Any]:
    """Get all elements of a specified IFC type.

    This function retrieves all elements matching the specified IFC type.
    This is typically the first step in exploratory analysis: "get all doors",
    "get all walls", etc. The returned element IDs can then be used with
    other generic tools to explore properties and relationships.

    Args:
        ifc_file_path: Path to the IFC file
        element_type: IFC type string (e.g., "IfcDoor", "IfcWall", "IfcSpace")

    Returns:
        Dictionary with:
        - element_type: The requested IFC type
        - element_ids: List of GlobalId strings for all matching elements
        - count: Total number of elements found

        Returns error dict if operation fails.

    Example:
        result = get_elements_by_type("model.ifc", "IfcDoor")
        # Returns: {"element_type": "IfcDoor",
        #           "element_ids": ["2O2Fr$t4X7Zf8NOew3FLOH", "3O2Fr$t4X7Zf8NOew3FLOI", ...],
        #           "count": 42}

    Note:
        Use this as the starting point for type-specific analysis. Once you have
        the element IDs, use get_element_attributes(), get_properties_in_pset(),
        or get_related_elements() to explore further.
    """
    try:
        from ifc_tool_utils.ifcopenshell import get_elements_by_type as get_elems

        with IFCFileManager(ifc_file_path) as ifc_file:
            elements = get_elems(ifc_file, element_type)
            element_ids = [get_element_guid(elem) for elem in elements]

            return {
                "element_type": element_type,
                "element_ids": element_ids,
                "count": len(element_ids)
            }
    except Exception as e:
        return {"element_type": element_type, "error": f"Failed to get elements: {str(e)}"}


def get_related_elements(ifc_file_path: str, element_id: str,
                        relationship_type: Optional[str] = None) -> Dict[str, Any]:
    """Get elements related through IFC relationships.

    This function discovers various types of relationships between elements:
    - Spatial containment (which space/storey contains this element)
    - Host relationships (which wall hosts this door)
    - Connectivity (which elements are connected)
    - Aggregation (part-whole relationships)

    Args:
        ifc_file_path: Path to the IFC file
        element_id: Element GlobalId
        relationship_type: Optional filter for specific relationship types:
                          - "container" - Get spatial container (space, storey, building)
                          - "host" - Get host element (wall for door/window)
                          - "contained" - Get elements contained in this spatial element
                          - "connected" - Get connected elements
                          - "aggregated" - Get parts of this element
                          - "parent" - Get parent in aggregation hierarchy
                          - None - Get all relationships

    Returns:
        Dictionary with:
        - element_id: GlobalId of the element
        - relationships: List of relationship dictionaries, each containing:
          - type: Relationship type description
          - related_elements: List of related element IDs

        Returns error dict if element not found.

    Example:
        result = get_related_elements("model.ifc", "2O2Fr$t4X7Zf8NOew3FLOH", "host")
        # Returns: {"element_id": "2O2Fr$t4X7Zf8NOew3FLOH",
        #           "relationships": [{"type": "host",
        #                             "related_elements": ["3O2Fr$t4X7Zf8NOew3FLOI"]}]}
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            element = get_element_by_id(ifc_file, element_id)
            if not element:
                return {"element_id": element_id, "error": "Element not found"}

            relationships = []

            # Helper to add relationship if elements found
            def add_relationship(rel_type: str, elements: List):
                if elements:
                    element_ids = [get_element_guid(e) for e in elements if e]
                    if element_ids:
                        relationships.append({
                            "type": rel_type,
                            "related_elements": element_ids
                        })

            # Spatial container
            if relationship_type is None or relationship_type == "container":
                container = get_spatial_container(element)
                if container:
                    add_relationship("container", [container])

            # Host element (for doors, windows)
            if relationship_type is None or relationship_type == "host":
                host = get_host_element(element)
                if host:
                    add_relationship("host", [host])

            # Contained elements (for spatial elements)
            if relationship_type is None or relationship_type == "contained":
                contained = get_contained_elements(element)
                if contained:
                    add_relationship("contained", contained)

            # Connected elements
            if relationship_type is None or relationship_type == "connected":
                connected = get_connected_elements(element)
                if connected:
                    add_relationship("connected", connected)

            # Aggregated elements (parts)
            if relationship_type is None or relationship_type == "aggregated":
                aggregated = get_aggregated_elements(element)
                if aggregated:
                    add_relationship("aggregated", aggregated)

            # Parent element (in aggregation)
            if relationship_type is None or relationship_type == "parent":
                parent = get_decomposing_element(element)
                if parent:
                    add_relationship("parent", [parent])

            # Filling elements (for walls - get doors/windows)
            if relationship_type is None or relationship_type == "filling":
                fillings = get_filling_elements(element)
                if fillings:
                    add_relationship("filling", fillings)

            return {
                "element_id": element_id,
                "relationships": relationships
            }
    except Exception as e:
        return {"element_id": element_id, "error": f"Failed to get relationships: {str(e)}"}
