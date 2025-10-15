"""
Tool: 3D Volumetric Analysis Tools
Category: trimesh
Description: Functions for 3D volumetric analysis including heights, clearances, and volume calculations using Trimesh
"""

import ifcopenshell
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell import (
    get_elements_by_type, get_elements_by_ids, get_element_guid, get_element_name,
    get_spatial_container
)
from ifc_tool_utils.trimesh import (
    ifc_to_trimesh, calculate_minimum_vertical_distance, get_mesh_bounds
)
from utils.ifc_file_manager import IFCFileManager


def get_space_net_heights(ifc_file_path: str, space_ids: List[str]) -> List[Dict[str, Any]]:
    """Extract net heights for spaces by calculating distance from floor to ceiling obstacles.


    Args:
        ifc_file_path: Path to the IFC file
        space_ids: List of space GlobalIds

    Returns:
        List of dictionaries containing space net height data
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            spaces = get_elements_by_ids(ifc_file, space_ids)

            # Get potential ceiling obstacles
            ceiling_types = ["IfcSlab", "IfcBeam", "IfcCovering", "IfcDistributionElement"]
            ceiling_elements = []
            for ceiling_type in ceiling_types:
                elements = get_elements_by_type(ifc_file, ceiling_type)
                ceiling_elements.extend(elements)

            height_data = []
            for space in spaces:
                space_mesh = ifc_to_trimesh(space)
                if not space_mesh:
                    continue

                # Find ceiling elements above this space
                space_bounds = get_mesh_bounds(space_mesh)
                space_max_z = space_bounds[5]  # top of space

                relevant_ceiling_meshes = []
                for ceiling_element in ceiling_elements:
                    ceiling_mesh = ifc_to_trimesh(ceiling_element)
                    if not ceiling_mesh:
                        continue

                    ceiling_bounds = get_mesh_bounds(ceiling_mesh)
                    ceiling_min_z = ceiling_bounds[2]  # bottom of ceiling element

                    # Check if ceiling element is above the space
                    if ceiling_min_z > space_max_z:
                        # Check for horizontal overlap (simplified)
                        if (ceiling_bounds[0] < space_bounds[3] and ceiling_bounds[3] > space_bounds[0] and
                            ceiling_bounds[1] < space_bounds[4] and ceiling_bounds[4] > space_bounds[1]):
                            relevant_ceiling_meshes.append(ceiling_mesh)

                # Calculate ceiling height
                if relevant_ceiling_meshes:
                    ceiling_height = calculate_minimum_vertical_distance(space_mesh, relevant_ceiling_meshes)
                else:
                    # No ceiling obstacles found, use space height
                    ceiling_height = space_bounds[5] - space_bounds[2]  # space height

                height_info = {
                    "space_id": get_element_guid(space),
                    "space_name": get_element_name(space),
                    "net_height": round(ceiling_height, 3),
                    "ceiling_obstacles_count": len(relevant_ceiling_meshes)
                }
                height_data.append(height_info)

            return height_data
    except Exception as e:
        return []


def get_door_opening_heights(ifc_file_path: str, door_ids: List[str]) -> List[Dict[str, Any]]:
    """Extract door opening clear heights for human passage.


    Args:
        ifc_file_path: Path to the IFC file
        door_ids: List of door GlobalIds

    Returns:
        List of dictionaries containing door opening height data
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            doors = get_elements_by_ids(ifc_file, door_ids)

            opening_data = []
            for door in doors:
                door_mesh = ifc_to_trimesh(door)
                if not door_mesh:
                    continue

                # Calculate door opening clear height
                # Note: This is a simplified implementation using bounding box
                # In a real implementation, this would extract the actual door opening geometry
                door_bounds = get_mesh_bounds(door_mesh)

                # Calculate opening height as the vertical dimension of the door element
                # This assumes the door mesh represents the opening space
                opening_clear_height = door_bounds[5] - door_bounds[2]  # top - bottom

                opening_info = {
                    "door_id": get_element_guid(door),
                    "door_name": get_element_name(door),
                    "opening_clear_height": round(opening_clear_height, 3)
                }
                opening_data.append(opening_info)

            return opening_data
    except Exception as e:
        return []


def get_stair_headroom(ifc_file_path: str, stair_ids: List[str]) -> List[Dict[str, Any]]:
    """Extract stair headroom clearances.


    Args:
        ifc_file_path: Path to the IFC file
        stair_ids: List of stair GlobalIds

    Returns:
        List of dictionaries containing stair headroom data
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            stairs = get_elements_by_ids(ifc_file, stair_ids)

            # Get potential overhead obstacles
            overhead_types = ["IfcSlab", "IfcStair", "IfcBeam"]
            overhead_elements = []
            for overhead_type in overhead_types:
                elements = get_elements_by_type(ifc_file, overhead_type)
                overhead_elements.extend(elements)

            headroom_data = []
            for stair in stairs:
                stair_mesh = ifc_to_trimesh(stair)
                if not stair_mesh:
                    continue

                stair_bounds = get_mesh_bounds(stair_mesh)

                # Find overhead obstacles above stair
                relevant_obstacle_meshes = []
                for obstacle in overhead_elements:
                    # Skip self
                    if get_element_guid(obstacle) == get_element_guid(stair):
                        continue

                    obstacle_mesh = ifc_to_trimesh(obstacle)
                    if not obstacle_mesh:
                        continue

                    obstacle_bounds = get_mesh_bounds(obstacle_mesh)

                    # Check if obstacle is above stair and overlaps
                    if (obstacle_bounds[2] > stair_bounds[5] and
                        obstacle_bounds[0] < stair_bounds[3] and obstacle_bounds[3] > stair_bounds[0] and
                        obstacle_bounds[1] < stair_bounds[4] and obstacle_bounds[4] > stair_bounds[1]):
                        relevant_obstacle_meshes.append(obstacle_mesh)

                # Calculate headroom
                if relevant_obstacle_meshes:
                    headroom = calculate_minimum_vertical_distance(stair_mesh, relevant_obstacle_meshes)
                else:
                    headroom = 3.0  # Default reasonable headroom

                headroom_info = {
                    "stair_id": get_element_guid(stair),
                    "stair_name": get_element_name(stair),
                    "headroom": round(headroom, 3),
                    "overhead_obstacles_count": len(relevant_obstacle_meshes)
                }
                headroom_data.append(headroom_info)

            return headroom_data
    except Exception as e:
        return []


