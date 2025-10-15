"""
Relationship Queries - Atomic functions for IFC relationship operations

These functions provide relationship query operations that return native
ifcopenshell objects for relationship and connection analysis.
"""

import ifcopenshell
from typing import List, Optional, Union, Dict, Any


def get_spatial_container(element: ifcopenshell.entity_instance) -> Optional[ifcopenshell.entity_instance]:
    """Get the spatial container (space, storey, building) that contains this element.

    Args:
        element: IFC element instance

    Returns:
        Spatial container element or None if not found
    """
    if not element or not hasattr(element, 'ContainedInStructure'):
        return None

    for rel in element.ContainedInStructure:
        if rel.is_a('IfcRelContainedInSpatialStructure'):
            return rel.RelatingStructure
    return None


def get_contained_elements(spatial_element: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Get all elements contained in a spatial structure.

    Args:
        spatial_element: IFC spatial element (IfcSpace, IfcBuildingStorey, etc.)

    Returns:
        List of contained elements
    """
    elements = []
    if not spatial_element or not hasattr(spatial_element, 'ContainsElements'):
        return elements

    for rel in spatial_element.ContainsElements:
        if rel.is_a('IfcRelContainedInSpatialStructure'):
            elements.extend(rel.RelatedElements)
    return elements


def get_connected_elements(element: ifcopenshell.entity_instance, relation_type: str = None) -> List[ifcopenshell.entity_instance]:
    """Get elements connected to this element.

    Args:
        element: IFC element instance
        relation_type: Specific relationship type filter (optional)

    Returns:
        List of connected elements
    """
    connected = []
    if not element:
        return connected

    # Check ConnectedTo relationships
    if hasattr(element, 'ConnectedTo'):
        for rel in element.ConnectedTo:
            if relation_type is None or rel.is_a(relation_type):
                connected.append(rel.RelatedElement)

    # Check ConnectedFrom relationships
    if hasattr(element, 'ConnectedFrom'):
        for rel in element.ConnectedFrom:
            if relation_type is None or rel.is_a(relation_type):
                connected.append(rel.RelatingElement)

    return connected


def get_filling_elements(host_element: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Get elements that fill openings in the host element (e.g., doors/windows in walls).

    Args:
        host_element: Host element (typically IfcWall)

    Returns:
        List of filling elements (doors, windows, etc.)
    """
    filling_elements = []
    if not host_element or not hasattr(host_element, 'HasOpenings'):
        return filling_elements

    for rel_voids in host_element.HasOpenings:
        if rel_voids.is_a('IfcRelVoidsElement'):
            opening = rel_voids.RelatedOpeningElement
            if hasattr(opening, 'HasFillings'):
                for rel_fills in opening.HasFillings:
                    if rel_fills.is_a('IfcRelFillsElement'):
                        filling_elements.append(rel_fills.RelatedBuildingElement)
    return filling_elements


def get_host_element(filling_element: ifcopenshell.entity_instance) -> Optional[ifcopenshell.entity_instance]:
    """Get the host element that contains this filling element.

    Args:
        filling_element: Filling element (door, window, etc.)

    Returns:
        Host element or None if not found
    """
    if not filling_element or not hasattr(filling_element, 'FillsVoids'):
        return None

    for rel_fills in filling_element.FillsVoids:
        if rel_fills.is_a('IfcRelFillsElement'):
            opening = rel_fills.RelatingOpeningElement
            if hasattr(opening, 'VoidsElements'):
                for rel_voids in opening.VoidsElements:
                    if rel_voids.is_a('IfcRelVoidsElement'):
                        return rel_voids.RelatingBuildingElement
    return None


def find_relationship(element1: ifcopenshell.entity_instance,
                     element2: ifcopenshell.entity_instance,
                     relationship_type: str = None) -> Optional[ifcopenshell.entity_instance]:
    """Find relationship between two elements.

    Args:
        element1: First element
        element2: Second element
        relationship_type: Specific relationship type to look for (optional)

    Returns:
        Relationship instance or None if not found
    """
    if not element1 or not element2:
        return None

    # Check all relationships from element1
    for attr_name in dir(element1):
        if attr_name.startswith('_'):
            continue
        attr_value = getattr(element1, attr_name)
        if hasattr(attr_value, '__iter__') and not isinstance(attr_value, str):
            for rel in attr_value:
                if hasattr(rel, 'is_a') and rel.is_a().startswith('IfcRel'):
                    if relationship_type and not rel.is_a(relationship_type):
                        continue

                    # Check if element2 is in this relationship
                    for rel_attr_name in dir(rel):
                        if rel_attr_name.startswith('_'):
                            continue
                        rel_attr_value = getattr(rel, rel_attr_name)

                        if rel_attr_value == element2:
                            return rel
                        elif hasattr(rel_attr_value, '__iter__') and not isinstance(rel_attr_value, str):
                            if element2 in rel_attr_value:
                                return rel
    return None


def get_aggregated_elements(aggregate_element: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Get elements that are aggregated by this element.

    Args:
        aggregate_element: Element that aggregates others

    Returns:
        List of aggregated elements
    """
    aggregated = []
    if not aggregate_element or not hasattr(aggregate_element, 'IsDecomposedBy'):
        return aggregated

    for rel in aggregate_element.IsDecomposedBy:
        if rel.is_a('IfcRelAggregates'):
            aggregated.extend(rel.RelatedObjects)
    return aggregated


def get_decomposing_element(element: ifcopenshell.entity_instance) -> Optional[ifcopenshell.entity_instance]:
    """Get the element that decomposes/aggregates this element.

    Args:
        element: Element that is part of an aggregation

    Returns:
        Decomposing element or None if not found
    """
    if not element or not hasattr(element, 'Decomposes'):
        return None

    for rel in element.Decomposes:
        if rel.is_a('IfcRelAggregates'):
            return rel.RelatingObject
    return None


def get_assigned_elements(assigning_element: ifcopenshell.entity_instance,
                         assignment_type: str = None) -> List[ifcopenshell.entity_instance]:
    """Get elements assigned to this element.

    Args:
        assigning_element: Element that assigns others
        assignment_type: Specific assignment type filter (optional)

    Returns:
        List of assigned elements
    """
    assigned = []
    if not assigning_element or not hasattr(assigning_element, 'HasAssignments'):
        return assigned

    for rel in assigning_element.HasAssignments:
        if assignment_type is None or rel.is_a(assignment_type):
            if hasattr(rel, 'RelatedObjects'):
                assigned.extend(rel.RelatedObjects)
    return assigned


def get_space_boundaries(ifc_file: ifcopenshell.entity_instance,
                        space: Optional[ifcopenshell.entity_instance] = None,
                        boundary_type: Optional[str] = None) -> List[ifcopenshell.entity_instance]:
    """Get space boundary relationships from IFC file with optional filtering.

    Args:
        ifc_file: IFC file instance
        space: Specific space to get boundaries for (optional, None = all spaces)
        boundary_type: Filter by boundary type: 'INTERNAL' or 'EXTERNAL' (optional, None = both)

    Returns:
        List of IfcRelSpaceBoundary instances matching filters.
        Returns empty list [] if no boundaries found or file has no IfcRelSpaceBoundary.
    """
    boundaries = ifc_file.by_type('IfcRelSpaceBoundary')

    filtered_boundaries = []
    for boundary in boundaries:
        # Filter by space if specified
        if space and boundary.RelatingSpace != space:
            continue

        # Filter by boundary type if specified
        if boundary_type and hasattr(boundary, 'InternalOrExternalBoundary'):
            if str(boundary.InternalOrExternalBoundary) != boundary_type:
                continue

        filtered_boundaries.append(boundary)

    return filtered_boundaries


def get_space_boundary_info(boundary: ifcopenshell.entity_instance) -> Dict[str, Any]:
    """Extract structured information from a space boundary relationship.

    Args:
        boundary: IfcRelSpaceBoundary instance

    Returns:
        Dict with keys: 'boundary_id', 'space_id', 'element_id', 'element_type',
        'physical_virtual', 'internal_external', 'level', 'description'.
        Values are GlobalId strings or property values. Missing attributes are omitted from dict.
    """
    info = {}

    try:
        info['boundary_id'] = boundary.GlobalId if hasattr(boundary, 'GlobalId') else str(boundary)
        info['space_id'] = boundary.RelatingSpace.GlobalId if boundary.RelatingSpace else None
        info['element_id'] = boundary.RelatedBuildingElement.GlobalId if boundary.RelatedBuildingElement else None
        info['element_type'] = boundary.RelatedBuildingElement.is_a() if boundary.RelatedBuildingElement else None

        if hasattr(boundary, 'PhysicalOrVirtualBoundary'):
            info['physical_virtual'] = str(boundary.PhysicalOrVirtualBoundary)

        if hasattr(boundary, 'InternalOrExternalBoundary'):
            info['internal_external'] = str(boundary.InternalOrExternalBoundary)

        if hasattr(boundary, 'Name'):
            info['level'] = boundary.Name

        if hasattr(boundary, 'Description'):
            info['description'] = boundary.Description

    except Exception as e:
        # Return partial info if some attributes are missing
        pass

    return info


def find_adjacent_spaces_via_boundaries(ifc_file: ifcopenshell.entity_instance,
                                       space: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Find spaces adjacent to given space by analyzing shared INTERNAL boundary elements.

    Args:
        ifc_file: IFC file instance
        space: Space to find adjacencies for

    Returns:
        List of unique adjacent space instances that share building elements with the input space.
        Returns empty list [] if space has no INTERNAL boundaries or no adjacent spaces found.
    """
    adjacent_spaces = []

    # Get all boundaries for this space (only internal boundaries indicate adjacency)
    space_boundaries = get_space_boundaries(ifc_file, space, 'INTERNAL')

    # Get all building elements that bound this space
    bounding_elements = []
    for boundary in space_boundaries:
        if boundary.RelatedBuildingElement:
            bounding_elements.append(boundary.RelatedBuildingElement)

    # Find other spaces that share these building elements
    all_boundaries = get_space_boundaries(ifc_file, boundary_type='INTERNAL')

    for boundary in all_boundaries:
        # Skip boundaries from the same space
        if boundary.RelatingSpace == space:
            continue

        # Check if this boundary shares a building element with our space
        if boundary.RelatedBuildingElement in bounding_elements:
            other_space = boundary.RelatingSpace
            if other_space and other_space not in adjacent_spaces:
                adjacent_spaces.append(other_space)

    return adjacent_spaces
