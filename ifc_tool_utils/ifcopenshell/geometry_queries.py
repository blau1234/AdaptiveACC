"""
Geometry Queries - Atomic functions for IFC geometric data operations

These functions provide geometric query operations that return native Python types
for geometric analysis and calculations.
"""

import ifcopenshell
import ifcopenshell.geom
from typing import Dict, List, Tuple, Optional, Any


def get_element_dimensions(element: ifcopenshell.entity_instance) -> Dict[str, Optional[float]]:
    """Get basic dimensions from element's direct properties (not geometry calculation).

    Args:
        element: IFC element instance

    Returns:
        Dict with keys: 'width', 'height', 'length', 'depth', 'overallwidth', 'overallheight'.
        Values are floats in model units or None if property not available.
        Returns empty dict {} if element is None.
    """
    dimensions = {}

    # Common dimension properties
    dimension_props = ['Width', 'Height', 'Length', 'Depth', 'OverallWidth', 'OverallHeight']

    for prop in dimension_props:
        if hasattr(element, prop):
            value = getattr(element, prop)
            if value is not None:
                try:
                    dimensions[prop.lower()] = float(value)
                except (ValueError, TypeError):
                    dimensions[prop.lower()] = None
            else:
                dimensions[prop.lower()] = None

    return dimensions


def get_element_location(element: ifcopenshell.entity_instance) -> Dict[str, Any]:
    """Get element's placement location and orientation from ObjectPlacement.

    Args:
        element: IFC element instance

    Returns:
        Dict with keys: 'coordinates' (list of [x, y, z] floats), 'direction' (list of direction ratios).
        Returns empty dict {} if element has no ObjectPlacement or is not IfcLocalPlacement.
    """
    location_data = {}

    if not element or not hasattr(element, 'ObjectPlacement'):
        return location_data

    placement = element.ObjectPlacement
    if placement and placement.is_a('IfcLocalPlacement'):
        if hasattr(placement, 'RelativePlacement') and placement.RelativePlacement:
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'Location') and rel_placement.Location:
                coords = rel_placement.Location.Coordinates
                location_data['coordinates'] = list(coords) if coords else []

            if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                direction = rel_placement.RefDirection.DirectionRatios
                location_data['direction'] = list(direction) if direction else []

    return location_data


def get_bounding_box(element: ifcopenshell.entity_instance) -> Dict[str, Any]:
    """Get element's 3D axis-aligned bounding box from processed geometry.

    Args:
        element: IFC element instance

    Returns:
        Dict with keys: 'min_x', 'min_y', 'min_z', 'max_x', 'max_y', 'max_z' (all float values in model units).
        Returns empty dict {} if element has no geometry or geometry processing fails.
    """
    bbox_data = {}

    try:
        # Create geometry settings
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        # Get shape
        shape = ifcopenshell.geom.create_shape(settings, element)
        if shape:
            # Get bounding box - handle different geometry types
            if hasattr(shape.geometry, 'bounding_box'):
                bbox = shape.geometry.bounding_box
            elif hasattr(shape.geometry, 'verts'):
                # For Triangulation objects in ifcopenshell 0.8.3+, use 'verts' attribute
                vertices = shape.geometry.verts
                if len(vertices) >= 3:  # Need at least one vertex (x,y,z)
                    # Convert flat vertex array to coordinate tuples
                    coords = [(vertices[i], vertices[i+1], vertices[i+2])
                             for i in range(0, len(vertices), 3)]

                    if coords:
                        xs, ys, zs = zip(*coords)
                        bbox = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
                    else:
                        bbox = None
                else:
                    bbox = None
            elif hasattr(shape.geometry, 'vertices'):
                # Fallback for older versions or other geometry types
                vertices = shape.geometry.vertices
                if len(vertices) >= 3:  # Need at least one vertex (x,y,z)
                    # Convert flat vertex array to coordinate tuples
                    coords = [(vertices[i], vertices[i+1], vertices[i+2])
                             for i in range(0, len(vertices), 3)]

                    if coords:
                        xs, ys, zs = zip(*coords)
                        bbox = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
                    else:
                        bbox = None
                else:
                    bbox = None
            else:
                bbox = None

            if bbox and len(bbox) >= 6:
                bbox_data = {
                    'min_x': bbox[0],
                    'min_y': bbox[1],
                    'min_z': bbox[2],
                    'max_x': bbox[3],
                    'max_y': bbox[4],
                    'max_z': bbox[5]
                }
    except Exception:
        # Return empty dict if geometry processing fails
        pass

    return bbox_data


def calculate_area(element: ifcopenshell.entity_instance) -> Optional[float]:
    """Calculate element area, prioritizing BIM quantity data over geometric estimation.

    Args:
        element: IFC element instance

    Returns:
        Area in model units (typically m²). First checks IfcElementQuantity AreaValue,
        falls back to bounding box width*height estimation if unavailable.
        Returns None if both methods fail.
    """
    # Try to get from quantity sets first
    if hasattr(element, 'IsDefinedBy'):
        for rel in element.IsDefinedBy:
            if rel.is_a('IfcRelDefinesByProperties'):
                qset = rel.RelatingPropertyDefinition
                if qset.is_a('IfcElementQuantity'):
                    for quantity in qset.Quantities:
                        if hasattr(quantity, 'AreaValue'):
                            return float(quantity.AreaValue)

    # Try geometric calculation
    try:
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, element)
        if shape:
            # For surfaces/areas, use appropriate calculation
            # This is a simplified approach
            bbox = shape.geometry.bounding_box
            if len(bbox) >= 6:
                # Estimate area from bounding box (simplified)
                width = bbox[3] - bbox[0]
                height = bbox[4] - bbox[1]
                return width * height
    except Exception:
        pass

    return None


def calculate_volume(element: ifcopenshell.entity_instance) -> Optional[float]:
    """Calculate element volume, prioritizing BIM quantity data over geometric estimation.

    Args:
        element: IFC element instance

    Returns:
        Volume in model units (typically m³). First checks IfcElementQuantity VolumeValue,
        falls back to bounding box width*height*depth estimation if unavailable.
        Returns None if both methods fail.
    """
    # Try to get from quantity sets first
    if hasattr(element, 'IsDefinedBy'):
        for rel in element.IsDefinedBy:
            if rel.is_a('IfcRelDefinesByProperties'):
                qset = rel.RelatingPropertyDefinition
                if qset.is_a('IfcElementQuantity'):
                    for quantity in qset.Quantities:
                        if hasattr(quantity, 'VolumeValue'):
                            return float(quantity.VolumeValue)

    # Try geometric calculation
    try:
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, element)
        if shape:
            # Get volume from shape geometry
            # This requires proper geometric analysis
            bbox = shape.geometry.bounding_box
            if len(bbox) >= 6:
                # Estimate volume from bounding box (simplified)
                width = bbox[3] - bbox[0]
                height = bbox[4] - bbox[1]
                depth = bbox[5] - bbox[2]
                return width * height * depth
    except Exception:
        pass

    return None


def get_geometry_representation(element: ifcopenshell.entity_instance) -> Dict[str, Any]:
    """Get metadata about element's geometry representations (not the actual geometry).

    Args:
        element: IFC element instance

    Returns:
        Dict with key 'representations': list of dicts, each containing 'context', 'identifier',
        'type', 'items_count' for each representation.
        Returns empty dict {} if element has no Representation attribute.
    """
    geom_data = {}

    if not element or not hasattr(element, 'Representation'):
        return geom_data

    representation = element.Representation
    if representation:
        representations = []
        for rep in representation.Representations:
            rep_data = {
                'context': rep.ContextOfItems.ContextType if hasattr(rep.ContextOfItems, 'ContextType') else None,
                'identifier': rep.RepresentationIdentifier if hasattr(rep, 'RepresentationIdentifier') else None,
                'type': rep.RepresentationType if hasattr(rep, 'RepresentationType') else None,
                'items_count': len(rep.Items) if hasattr(rep, 'Items') else 0
            }
            representations.append(rep_data)
        geom_data['representations'] = representations

    return geom_data


def get_placement_matrix(element: ifcopenshell.entity_instance) -> List[List[float]]:
    """Get 4x4 transformation matrix from element's placement in world coordinates.

    Args:
        element: IFC element instance

    Returns:
        4x4 transformation matrix as nested list of floats [[row1], [row2], [row3], [row4]].
        Returns empty list [] if geometry processing fails or element has no placement.
    """
    try:
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, element)
        if shape and hasattr(shape, 'transformation'):
            # Convert transformation matrix to nested list format
            matrix = shape.transformation.matrix
            return [[matrix[i*4+j] for j in range(4)] for i in range(4)]
    except Exception:
        pass

    return []


def calculate_distance_between_elements(element1: ifcopenshell.entity_instance,
                                      element2: ifcopenshell.entity_instance) -> Optional[float]:
    """Calculate 3D Euclidean distance between element placement centers.

    Measurement Type: Center-to-center distance (not surface-to-surface).
    Uses ObjectPlacement coordinates, not geometry boundaries.

    Args:
        element1: First IFC element
        element2: Second IFC element

    Returns:
        3D distance in model units as float, or None if either element lacks ObjectPlacement coordinates.
    """
    try:
        loc1 = get_element_location(element1)
        loc2 = get_element_location(element2)

        if 'coordinates' in loc1 and 'coordinates' in loc2:
            coords1 = loc1['coordinates']
            coords2 = loc2['coordinates']

            if len(coords1) >= 3 and len(coords2) >= 3:
                # Calculate Euclidean distance
                dx = coords1[0] - coords2[0]
                dy = coords1[1] - coords2[1]
                dz = coords1[2] - coords2[2]
                return (dx**2 + dy**2 + dz**2)**0.5
    except Exception:
        pass

    return None