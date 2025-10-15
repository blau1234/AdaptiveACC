"""
Tool: extract_stair_flights
Category: element_selection
Description: Extract all stair flight elements from an IFC file by filtering for IfcStairFlight entities
"""

import ifcopenshell
from typing import List, Dict, Any


def extract_stair_flights(ifc_file_path: str) -> List[Dict[str, Any]]:
    """Extract all stair flight elements from an IFC file.
    
    This function reads an IFC file and extracts all IfcStairFlight entities,
    returning a list of dictionaries containing key information about each stair flight.
    
    Args:
        ifc_file_path (str): Path to the IFC file to process
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - 'global_id': The GlobalId of the stair flight
            - 'name': The name of the stair flight (empty string if not available)
            - 'description': The description of the stair flight (empty string if not available)
            - 'element_type': The IFC type (always 'IfcStairFlight')
            - 'step_data': Dictionary with 'number_of_risers' and 'number_of_treads' if available
            - 'properties': Dictionary of all property sets and their values
            
    Example:
        >>> stair_flights = extract_stair_flights('model.ifc')
        >>> for flight in stair_flights:
        ...     print(f"Stair flight: {flight['name']}, ID: {flight['global_id']}")
    """
    try:
        # Open the IFC file
        ifc_file = ifcopenshell.open(ifc_file_path)
        
        # Get all IfcStairFlight elements
        stair_flights = ifc_file.by_type('IfcStairFlight')
        
        result = []
        
        for stair_flight in stair_flights:
            # Extract basic element information
            flight_info = {
                'global_id': getattr(stair_flight, 'GlobalId', ''),
                'name': getattr(stair_flight, 'Name', ''),
                'description': getattr(stair_flight, 'Description', ''),
                'element_type': 'IfcStairFlight'
            }
            
            # Extract step data if available
            step_data = {}
            if hasattr(stair_flight, 'NumberOfRisers'):
                step_data['number_of_risers'] = stair_flight.NumberOfRisers
            if hasattr(stair_flight, 'NumberOfTreads'):
                step_data['number_of_treads'] = stair_flight.NumberOfTreads
            flight_info['step_data'] = step_data
            
            # Extract property sets using ifcopenshell.util.element
            try:
                import ifcopenshell.util.element
                properties = ifcopenshell.util.element.get_psets(stair_flight)
                flight_info['properties'] = properties
            except (ImportError, AttributeError):
                # Fallback if ifcopenshell.util.element is not available
                flight_info['properties'] = {}
            
            result.append(flight_info)
        
        return result
        
    except FileNotFoundError:
        raise FileNotFoundError(f"IFC file not found: {ifc_file_path}")
    except Exception as e:
        # Return empty list for other errors to maintain robustness
        print(f"Error processing IFC file: {e}")
        return []