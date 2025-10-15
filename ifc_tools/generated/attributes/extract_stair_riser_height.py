"""
Tool: extract_stair_riser_height
Category: attributes
Description: Extract riser height from IfcStair property sets in an IFC file
"""

import ifcopenshell
from typing import Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property


def extract_stair_riser_height(ifc_file_path: str, stair_id: str) -> Optional[float]:
    """Extract riser height from IfcStair property sets in an IFC file.
    
    This function extracts the riser height value from an IfcStair element by checking
    common property sets where stair geometry parameters are typically stored.
    
    Args:
        ifc_file_path (str): Path to the IFC file containing the stair elements
        stair_id (str): Unique identifier (GlobalId) of the IfcStair element
        
    Returns:
        Optional[float]: Riser height value in model units, or None if not found
        
    Example:
        >>> riser_height = extract_stair_riser_height("model.ifc", "2XQ7X9v9H1h8K$z4HqW3DD")
        >>> print(f"Riser height: {riser_height}")
        Riser height: 0.175
    """
    try:
        # Open the IFC file
        ifc_file = ifcopenshell.open(ifc_file_path)
        
        # Get the stair element by its GlobalId
        stair_element = get_element_by_id(ifc_file, stair_id)
        
        if stair_element is None:
            print(f"Warning: Stair element with ID '{stair_id}' not found")
            return None
        
        # Check if the element is actually an IfcStair
        element_type = getattr(stair_element, 'is_a', lambda: '')()
        if element_type != 'IfcStair':
            print(f"Warning: Element with ID '{stair_id}' is not an IfcStair (found: {element_type})")
            return None
        
        # Try to extract riser height from common property sets
        # Common property set names for stair geometry
        pset_names_to_check = [
            'Pset_StairCommon',
            'Pset_Stair', 
            'PSet_StairCommon',
            'PSet_Stair',
            'StairCommon',
            'Stair',
            'BaseQuantities'
        ]
        
        # Common property names for riser height
        property_names_to_check = [
            'RiserHeight',
            'Riser_Height',
            'RiserHeightValue',
            'Riser',
            'RiserHeightNominal',
            'NominalRiserHeight'
        ]
        
        # Search through property sets and property names
        for pset_name in pset_names_to_check:
            for prop_name in property_names_to_check:
                riser_height = get_pset_property(stair_element, pset_name, prop_name)
                if riser_height is not None:
                    # Ensure the value is numeric
                    try:
                        return float(riser_height)
                    except (ValueError, TypeError):
                        print(f"Warning: Riser height value '{riser_height}' is not numeric")
                        continue
        
        # If not found in property sets, try basic properties
        basic_property_names = ['RiserHeight', 'Riser_Height', 'Riser']
        for prop_name in basic_property_names:
            riser_height = getattr(stair_element, prop_name, None)
            if riser_height is not None:
                try:
                    return float(riser_height)
                except (ValueError, TypeError):
                    continue
        
        print(f"Warning: Riser height not found for stair element '{stair_id}'")
        return None
        
    except FileNotFoundError:
        print(f"Error: IFC file not found at path '{ifc_file_path}'")
        return None
    except Exception as e:
        print(f"Error processing IFC file: {str(e)}")
        return None