"""
Tool: Data Grouping Operations
Category: aggregation
Description: Functions for grouping and organizing data by different criteria
"""

from typing import List, Dict, Any
from collections import defaultdict


def group_by_property(data: List[Dict[str, Any]], property_name: str) -> Dict[Any, List[Dict[str, Any]]]:
    """Group elements by a specific property value.

    Args:
        data: List of dictionaries containing element data
        property_name: Name of the property to group by

    Returns:
        Dictionary mapping property values to lists of elements

    Example:
        doors = [
            {"element_id": "D1", "floor": "Level 1", "width": 900},
            {"element_id": "D2", "floor": "Level 2", "width": 800},
            {"element_id": "D3", "floor": "Level 1", "width": 900}
        ]
        grouped = group_by_property(doors, "floor")
        # Returns: {
        #     "Level 1": [{"element_id": "D1", ...}, {"element_id": "D3", ...}],
        #     "Level 2": [{"element_id": "D2", ...}]
        # }
    """
    grouped = defaultdict(list)
    for item in data:
        key = item.get(property_name)
        if key is not None:
            grouped[key].append(item)
    return dict(grouped)


def group_by_multiple_properties(data: List[Dict[str, Any]], property_names: List[str]) -> Dict[tuple, List[Dict[str, Any]]]:
    """Group elements by multiple property values.

    Args:
        data: List of dictionaries containing element data
        property_names: List of property names to group by

    Returns:
        Dictionary mapping tuples of property values to lists of elements

    Example:
        doors = [
            {"element_id": "D1", "floor": "Level 1", "type": "Fire", "width": 900},
            {"element_id": "D2", "floor": "Level 1", "type": "Normal", "width": 800},
            {"element_id": "D3", "floor": "Level 2", "type": "Fire", "width": 900}
        ]
        grouped = group_by_multiple_properties(doors, ["floor", "type"])
        # Returns: {
        #     ("Level 1", "Fire"): [{"element_id": "D1", ...}],
        #     ("Level 1", "Normal"): [{"element_id": "D2", ...}],
        #     ("Level 2", "Fire"): [{"element_id": "D3", ...}]
        # }
    """
    grouped = defaultdict(list)
    for item in data:
        key = tuple(item.get(prop) for prop in property_names)
        if all(k is not None for k in key):
            grouped[key].append(item)
    return dict(grouped)


def group_by_range(data: List[Dict[str, Any]], field_name: str, ranges: List[tuple]) -> Dict[str, List[Dict[str, Any]]]:
    """Group elements into ranges based on a numeric field.

    Args:
        data: List of dictionaries containing element data
        field_name: Name of the numeric field to group by
        ranges: List of (min, max, label) tuples defining ranges

    Returns:
        Dictionary mapping range labels to lists of elements

    Example:
        doors = [
            {"element_id": "D1", "width": 700},
            {"element_id": "D2", "width": 850},
            {"element_id": "D3", "width": 950}
        ]
        ranges = [(0, 800, "narrow"), (800, 1000, "standard"), (1000, float('inf'), "wide")]
        grouped = group_by_range(doors, "width", ranges)
        # Returns: {
        #     "narrow": [{"element_id": "D1", ...}],
        #     "standard": [{"element_id": "D2", ...}, {"element_id": "D3", ...}],
        #     "wide": []
        # }
    """
    grouped = {label: [] for _, _, label in ranges}

    for item in data:
        value = item.get(field_name)
        if value is not None and isinstance(value, (int, float)):
            for min_val, max_val, label in ranges:
                if min_val <= value < max_val:
                    grouped[label].append(item)
                    break

    return grouped
