"""
Tool: 2D Geometric Analysis Tools
Category: shapely
Description: Functions for 2D geometry analysis and spatial relationships using Shapely
"""

import ifcopenshell
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell import (
    get_elements_by_type, get_elements_by_ids, get_element_by_id,
    get_element_guid, get_element_name
)
from ifc_tool_utils.shapely import (
    ifc_to_shapely_polygon, calculate_minimum_distance, get_polygon_bounds
)
from utils.ifc_file_manager import IFCFileManager


def get_minimum_distances(ifc_file_path: str, element_pairs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Extract minimum 2D distances between element pairs.

    Args:
        ifc_file_path: Path to the IFC file
        element_pairs: List of dicts with 'element1_id' and 'element2_id'

    Returns:
        List of dictionaries containing distance data
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            distance_data = []
            for pair in element_pairs:
                element1_id = pair.get("element1_id")
                element2_id = pair.get("element2_id")

                if not element1_id or not element2_id:
                    continue

                element1 = get_element_by_id(ifc_file, element1_id)
                element2 = get_element_by_id(ifc_file, element2_id)

                if not element1 or not element2:
                    continue

                # Convert to Shapely geometries
                geom1 = ifc_to_shapely_polygon(element1)
                geom2 = ifc_to_shapely_polygon(element2)

                if not geom1 or not geom2:
                    continue

                # Calculate minimum distance
                min_distance = calculate_minimum_distance(geom1, geom2)

                distance_info = {
                    "element1_id": element1_id,
                    "element1_name": get_element_name(element1),
                    "element2_id": element2_id,
                    "element2_name": get_element_name(element2),
                    "minimum_distance": round(min_distance, 3)
                }
                distance_data.append(distance_info)

            return distance_data
    except Exception as e:
        return []


def get_corridor_widths(ifc_file_path: str, corridor_ids: List[str]) -> List[Dict[str, Any]]:
    """Extract corridor width measurements.

    Args:
        ifc_file_path: Path to the IFC file
        corridor_ids: List of corridor space GlobalIds

    Returns:
        List of dictionaries containing corridor width data
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            corridors = get_elements_by_ids(ifc_file, corridor_ids)

            width_data = []
            for corridor in corridors:
                corridor_polygon = ifc_to_shapely_polygon(corridor)
                if not corridor_polygon:
                    continue

                # Get bounding box to estimate dimensions
                bounds = get_polygon_bounds(corridor_polygon)
                width = bounds[2] - bounds[0]  # max_x - min_x
                length = bounds[3] - bounds[1]  # max_y - min_y

                # Assume width is the smaller dimension
                corridor_width = min(width, length)

                corridor_info = {
                    "corridor_id": get_element_guid(corridor),
                    "corridor_name": get_element_name(corridor),
                    "width": round(corridor_width, 2)
                }
                width_data.append(corridor_info)

            return width_data
    except Exception as e:
        return []


def get_room_dimensions(ifc_file_path: str, space_ids: List[str]) -> List[Dict[str, Any]]:
    """Extract 2D room dimensions and shape properties.

    Args:
        ifc_file_path: Path to the IFC file
        space_ids: List of space GlobalIds

    Returns:
        List of dictionaries containing room dimension data
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            spaces = get_elements_by_ids(ifc_file, space_ids)

            dimension_data = []
            for space in spaces:
                space_polygon = ifc_to_shapely_polygon(space)
                if not space_polygon:
                    continue

                # Get bounding box dimensions
                bounds = get_polygon_bounds(space_polygon)
                width = bounds[2] - bounds[0]  # max_x - min_x
                length = bounds[3] - bounds[1]  # max_y - min_y

                dimension_info = {
                    "space_id": get_element_guid(space),
                    "space_name": get_element_name(space),
                    "width": round(width, 2),
                    "length": round(length, 2)
                }
                dimension_data.append(dimension_info)

            return dimension_data
    except Exception as e:
        return []