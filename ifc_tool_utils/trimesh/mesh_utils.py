"""
Trimesh Mesh Utilities - Atomic functions for 3D geometry operations

This module provides atomic functions for working with Trimesh geometries.
These functions handle IFC-to-Trimesh conversion and basic 3D geometric operations.
"""

import ifcopenshell
import trimesh
import numpy as np
from typing import List, Tuple, Optional, Union
from ifc_tool_utils.ifcopenshell import get_bounding_box, get_element_location


def ifc_to_trimesh(ifc_element) -> Optional[trimesh.Trimesh]:
    """Convert IFC element to Trimesh 3D box mesh using bounding box approximation.

    Step Type: utility

    Args:
        ifc_element: IFC element object

    Returns:
        Trimesh object with 8 vertices and 12 triangular faces representing the bounding box.
        Returns None if element has no bounding box or conversion fails.
    """
    try:
        # Get bounding box and create a simple box mesh representation
        bbox = get_bounding_box(ifc_element)
        if not bbox:
            return None

        # bbox format: dict with keys 'min_x', 'min_y', 'min_z', 'max_x', 'max_y', 'max_z'
        # Create box vertices
        vertices = np.array([
            [bbox['min_x'], bbox['min_y'], bbox['min_z']],  # min corner
            [bbox['max_x'], bbox['min_y'], bbox['min_z']],  # +x
            [bbox['max_x'], bbox['max_y'], bbox['min_z']],  # +x+y
            [bbox['min_x'], bbox['max_y'], bbox['min_z']],  # +y
            [bbox['min_x'], bbox['min_y'], bbox['max_z']],  # +z
            [bbox['max_x'], bbox['min_y'], bbox['max_z']],  # +x+z
            [bbox['max_x'], bbox['max_y'], bbox['max_z']],  # +x+y+z
            [bbox['min_x'], bbox['max_y'], bbox['max_z']]   # +y+z
        ])

        # Create box faces (triangles)
        faces = np.array([
            # Bottom face (z=min)
            [0, 1, 2], [0, 2, 3],
            # Top face (z=max)
            [4, 6, 5], [4, 7, 6],
            # Front face (y=min)
            [0, 5, 1], [0, 4, 5],
            # Back face (y=max)
            [2, 6, 7], [2, 7, 3],
            # Left face (x=min)
            [0, 3, 7], [0, 7, 4],
            # Right face (x=max)
            [1, 5, 6], [1, 6, 2]
        ])

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        return mesh
    except Exception as e:
        return None


def calculate_minimum_vertical_distance(lower_mesh: trimesh.Trimesh, upper_meshes: List[trimesh.Trimesh]) -> float:
    """Calculate minimum vertical clearance between lower mesh top and upper meshes bottom.

    Measurement Type: Pure Z-axis distance (ignores XY position).
    Calculates: min(upper_mesh.min_z) - lower_mesh.max_z for all upper meshes.

    Args:
        lower_mesh: Lower reference mesh (e.g., floor)
        upper_meshes: List of upper obstacle meshes (e.g., ceilings, beams)

    Returns:
        Minimum vertical distance as float in model units. Returns inf if upper_meshes is empty,
        returns 0.0 if calculation fails or distance is negative.
    """
    try:
        if not upper_meshes:
            return float('inf')

        # Get the highest points of the lower mesh
        lower_top_z = np.max(lower_mesh.vertices[:, 2])

        min_distance = float('inf')

        for upper_mesh in upper_meshes:
            # Get the lowest points of the upper mesh
            upper_bottom_z = np.min(upper_mesh.vertices[:, 2])

            # Calculate vertical distance
            distance = upper_bottom_z - lower_top_z
            min_distance = min(min_distance, distance)

        return float(max(0.0, min_distance))  # Ensure non-negative distance
    except Exception as e:
        return 0.0


def get_mesh_bounds(mesh: trimesh.Trimesh) -> Tuple[float, float, float, float, float, float]:
    """Get 3D axis-aligned bounding box of a mesh.

    Args:
        mesh: Trimesh mesh object

    Returns:
        Tuple of (min_x, min_y, min_z, max_x, max_y, max_z) as floats in model units.
        Returns (0.0, 0.0, 0.0, 0.0, 0.0, 0.0) if operation fails.
    """
    try:
        bounds = mesh.bounds
        return (bounds[0, 0], bounds[0, 1], bounds[0, 2],
                bounds[1, 0], bounds[1, 1], bounds[1, 2])
    except Exception as e:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def create_mesh_from_vertices_faces(vertices: np.ndarray, faces: np.ndarray) -> Optional[trimesh.Trimesh]:
    """Create Trimesh mesh from raw vertex coordinates and face indices.

    Args:
        vertices: Numpy array of shape (N, 3) with vertex [x, y, z] coordinates
        faces: Numpy array of shape (M, 3) with triangular face vertex indices

    Returns:
        Trimesh mesh object, or None if creation fails (invalid input format or dimensions).
    """
    try:
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        return mesh
    except Exception as e:
        return None