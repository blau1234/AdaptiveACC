"""
Tool: extract_stairflight_riser_height
Category: attributes
Description: Extract riser height from IfcStairFlight property sets in IFC files
"""

import ifcopenshell
from typing import Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property


def extract_stairflight_riser_height(ifc_file_path: str, stairflight_id: str) -> Optional[float]:
    """Extract riser height from IfcStairFlight property sets in IFC files.
    
    This function extracts the riser height (vertical height of each step) from 
    an IfcStairFlight element by checking common property sets and properties 
    where riser height information is typically stored.
    
    Args:
        ifc_file_path: Path to the IFC file containing the stair flight elements
        stairflight_id: Unique identifier (GlobalId) of the IfcStairFlight element
        
    Returns:
        float: The riser height value in model units, or None if not found
        
    Example:
        >>> height = extract_stairflight_riser_height("model.ifc", "2XQ7X9vz90IugbB3Np3p4L")
        >>> print(f"Riser height: {height}")
        Riser height: 0.18
    """
    try:
        # Open the IFC file
        ifc_file = ifcopenshell.open(ifc_file_path)
        
        # Get the stair flight element by ID
        stairflight = get_element_by_id(ifc_file, stairflight_id)
        
        if stairflight is None:
            print(f"Warning: Stair flight with ID '{stairflight_id}' not found")
            return None
        
        # Check if element is actually an IfcStairFlight
        element_type = getattr(stairflight, 'is_a', lambda: '')()
        if element_type != 'IfcStairFlight':
            print(f"Warning: Element with ID '{stairflight_id}' is not an IfcStairFlight (found: {element_type})")
            return None
        
        # Try to extract riser height from common property sets
        # Common property sets for stair flights
        property_sets_to_check = [
            'Pset_StairFlightCommon',
            'Pset_StairCommon', 
            'Pset_StairFlight',
            'BaseQuantities',
            'Qto_StairFlightBaseQuantities'
        ]
        
        # Common property names for riser height
        riser_height_property_names = [
            'RiserHeight',
            'Riser',
            'RiserHeightValue',
            'NominalRiserHeight',
            'RiserHeightNominal',
            'RiserHeightActual'
        ]
        
        # Check each property set and property name combination
        for pset_name in property_sets_to_check:
            for prop_name in riser_height_property_names:
                riser_height = get_pset_property(stairflight, pset_name, prop_name)
                if riser_height is not None:
                    # Ensure we return a float value
                    try:
                        return float(riser_height)
                    except (ValueError, TypeError):
                        print(f"Warning: Riser height value '{riser_height}' cannot be converted to float")
                        continue
        
        # If no riser height found in property sets, try to calculate from geometry
        # Get overall height and number of risers if available
        overall_height = get_pset_property(stairflight, 'BaseQuantities', 'Height')
        number_of_risers = get_pset_property(stairflight, 'Pset_StairFlightCommon', 'NumberOfRisers')
        
        if overall_height is not None and number_of_risers is not None:
            try:
                overall_height_float = float(overall_height)
                number_of_risers_int = int(number_of_risers)
                if number_of_risers_int > 0:
                    calculated_riser_height = overall_height_float / number_of_risers_int
                    print(f"Info: Calculated riser height from overall height and number of risers: {calculated_riser_height}")
                    return calculated_riser_height
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        print(f"Warning: Riser height not found for stair flight '{stairflight_id}'")
        return None
        
    except FileNotFoundError:
        print(f"Error: IFC file not found at path '{ifc_file_path}'")
        return None
    except Exception as e:
        print(f"Error processing IFC file: {str(e)}")
        return None