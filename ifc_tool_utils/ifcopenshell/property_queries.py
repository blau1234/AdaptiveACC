"""
Property Queries - Atomic functions for IFC property and property set operations

These functions provide property query operations that return native Python types
or ifcopenshell objects for property data extraction.
"""

import ifcopenshell
from typing import Dict, Any, Optional, List, Union


def get_basic_property(element: ifcopenshell.entity_instance, property_name: str) -> Any:
    """Get basic property value from element attributes.

    Args:
        element: IFC element instance
        property_name: Property name (e.g., "Width", "Height")

    Returns:
        Property value or None if not found
    """
    if not element or not hasattr(element, property_name):
        return None

    value = getattr(element, property_name)
    return value


def get_pset_property(element: ifcopenshell.entity_instance, pset_name: str, property_name: str) -> Any:
    """Get property value from property set.

    Args:
        element: IFC element instance
        pset_name: Property set name (e.g., "Pset_DoorCommon")
        property_name: Property name within the set

    Returns:
        Property value or None if not found
    """
    if not element or not hasattr(element, 'IsDefinedBy'):
        return None

    for rel in element.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a('IfcPropertySet') and pset.Name == pset_name:
                for prop in pset.HasProperties:
                    if prop.Name == property_name:
                        if hasattr(prop, 'NominalValue') and prop.NominalValue:
                            return prop.NominalValue.wrappedValue
    return None


def get_all_psets(element: ifcopenshell.entity_instance) -> Dict[str, Dict[str, Any]]:
    """Get all property sets (IfcPropertySet) for an element.

    Args:
        element: IFC element instance

    Returns:
        Dict mapping property set names to nested dicts of {property_name: value}.
        Values are unwrapped from NominalValue. Returns empty dict {} if element has no property sets.
        Example: {'Pset_WallCommon': {'FireRating': 'REI90', 'LoadBearing': True}}
    """
    psets = {}
    if not element or not hasattr(element, 'IsDefinedBy'):
        return psets

    for rel in element.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a('IfcPropertySet'):
                pset_props = {}
                for prop in pset.HasProperties:
                    if hasattr(prop, 'NominalValue') and prop.NominalValue:
                        pset_props[prop.Name] = prop.NominalValue.wrappedValue
                    else:
                        pset_props[prop.Name] = None
                psets[pset.Name] = pset_props
    return psets


def get_quantity_value(element: ifcopenshell.entity_instance, quantity_name: str) -> Optional[float]:
    """Get quantity value from element's quantity sets (IfcElementQuantity).

    Args:
        element: IFC element instance
        quantity_name: Quantity name (e.g., "GrossArea", "NetVolume", "Length", "Count")

    Returns:
        Quantity value as float, extracted from AreaValue/VolumeValue/LengthValue/CountValue.
        Returns None if quantity not found or element has no quantity sets.
    """
    if not element or not hasattr(element, 'IsDefinedBy'):
        return None

    for rel in element.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            qset = rel.RelatingPropertyDefinition
            if qset.is_a('IfcElementQuantity'):
                for quantity in qset.Quantities:
                    if quantity.Name == quantity_name:
                        if hasattr(quantity, 'AreaValue'):
                            return float(quantity.AreaValue)
                        elif hasattr(quantity, 'VolumeValue'):
                            return float(quantity.VolumeValue)
                        elif hasattr(quantity, 'LengthValue'):
                            return float(quantity.LengthValue)
                        elif hasattr(quantity, 'CountValue'):
                            return float(quantity.CountValue)
    return None