"""
Shapely Geometry Utilities - Atomic functions for 2D geometry operations

This module provides atomic functions for working with Shapely geometries.
These functions handle IFC-to-Shapely conversion and basic 2D geometric operations.
"""

import ifcopenshell
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from typing import List, Tuple, Union, Optional
from ifc_tool_utils.ifcopenshell import get_element_location, get_bounding_box


def ifc_to_shapely_polygon(ifc_element) -> Optional[Polygon]:
    """Convert IFC element to Shapely 2D polygon using bounding box projection on XY plane.

    Step Type: utility

    Args:
        ifc_element: IFC element object

    Returns:
        Shapely Polygon with 4 corner points (min_x/min_y to max_x/max_y), ignoring Z-axis.
        Returns None if element has no bounding box or conversion fails.
    """
    try:
        # Get bounding box as fallback for polygon creation
        bbox = get_bounding_box(ifc_element)
        if not bbox:
            return None

        # Create polygon from bounding box coordinates
        # bbox format: dict with keys 'min_x', 'min_y', 'min_z', 'max_x', 'max_y', 'max_z'
        coords = [
            (bbox['min_x'], bbox['min_y']),  # min_x, min_y
            (bbox['max_x'], bbox['min_y']),  # max_x, min_y
            (bbox['max_x'], bbox['max_y']),  # max_x, max_y
            (bbox['min_x'], bbox['max_y'])   # min_x, max_y
        ]

        return Polygon(coords)
    except Exception as e:
        return None


def calculate_minimum_distance(geom1: Union[Point, LineString, Polygon],
                             geom2: Union[Point, LineString, Polygon]) -> float:
    """Calculate minimum 2D distance between geometry edges/surfaces (not centers).

    Step Type: utility

    Measurement Type: Surface-to-surface distance in XY plane only (ignores Z-axis).
    Uses Shapely's precise distance calculation between closest points on boundaries.

    Args:
        geom1: First Shapely geometry (Point, LineString, Polygon)
        geom2: Second Shapely geometry

    Returns:
        Minimum distance as float in coordinate units. Returns inf if calculation fails.
    """
    try:
        return geom1.distance(geom2)
    except Exception as e:
        return float('inf')


def get_polygon_bounds(polygon: Polygon) -> Tuple[float, float, float, float]:
    """Get 2D axis-aligned bounding box of a polygon.

    Args:
        polygon: Shapely Polygon object

    Returns:
        Tuple of (min_x, min_y, max_x, max_y) as floats in coordinate units.
        Returns (0.0, 0.0, 0.0, 0.0) if operation fails.
    """
    try:
        return polygon.bounds
    except Exception as e:
        return (0.0, 0.0, 0.0, 0.0)




