"""
Tool: Counting and Statistical Operations
Category: quantification
Description: Pure counting functions for element quantification and threshold-based counting
"""

from typing import List, Dict, Any


def count_elements(elements: List[Dict]) -> int:
    """Count total number of elements in a list.

    Args:
        elements: List of element dictionaries

    Returns:
        Total count of elements as integer

    Example:
        doors = [{'element_id': '1', 'name': 'Door 1'}, {'element_id': '2', 'name': 'Door 2'}]
        count = count_elements(doors)  # Returns: 2
    """
    return len(elements)


def count_by_property_value(elements: List[Dict],
                            property_name: str,
                            property_value: Any) -> int:
    """Count elements that have a specific property value.

    Args:
        elements: List of element dictionaries
        property_name: Name of the property to check
        property_value: Target value to match (exact match)

    Returns:
        Count of elements with matching property value as integer

    Example:
        doors = [
            {'element_id': '1', 'fire_rating': 'FD30'},
            {'element_id': '2', 'fire_rating': 'FD60'},
            {'element_id': '3', 'fire_rating': 'FD30'}
        ]
        count = count_by_property_value(doors, 'fire_rating', 'FD30')  # Returns: 2
    """
    return sum(1 for e in elements if e.get(property_name) == property_value)


def count_above_threshold(elements: List[Dict],
                         field_name: str,
                         threshold: float) -> int:
    """Count elements where a numeric field value is above a threshold.

    Args:
        elements: List of element dictionaries
        field_name: Name of the numeric field to check
        threshold: Threshold value (exclusive, elements > threshold are counted)

    Returns:
        Count of elements above threshold as integer. Non-numeric values are ignored.

    Example:
        doors = [
            {'element_id': '1', 'width': 900},
            {'element_id': '2', 'width': 750},
            {'element_id': '3', 'width': 1000}
        ]
        count = count_above_threshold(doors, 'width', 800)  # Returns: 2
    """
    return sum(1 for e in elements
               if isinstance(e.get(field_name), (int, float))
               and e[field_name] > threshold)


def count_below_threshold(elements: List[Dict],
                         field_name: str,
                         threshold: float) -> int:
    """Count elements where a numeric field value is below a threshold.

    Args:
        elements: List of element dictionaries
        field_name: Name of the numeric field to check
        threshold: Threshold value (exclusive, elements < threshold are counted)

    Returns:
        Count of elements below threshold as integer. Non-numeric values are ignored.

    Example:
        spaces = [
            {'element_id': '1', 'area': 25.5},
            {'element_id': '2', 'area': 15.0},
            {'element_id': '3', 'area': 30.0}
        ]
        count = count_below_threshold(spaces, 'area', 20.0)  # Returns: 1
    """
    return sum(1 for e in elements
               if isinstance(e.get(field_name), (int, float))
               and e[field_name] < threshold)


def count_in_range(elements: List[Dict],
                  field_name: str,
                  min_value: float,
                  max_value: float) -> int:
    """Count elements where a numeric field value is within a specified range.

    Args:
        elements: List of element dictionaries
        field_name: Name of the numeric field to check
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)

    Returns:
        Count of elements within range [min_value, max_value] as integer.
        Non-numeric values are ignored.

    Example:
        doors = [
            {'element_id': '1', 'height': 2000},
            {'element_id': '2', 'height': 2100},
            {'element_id': '3', 'height': 2400}
        ]
        count = count_in_range(doors, 'height', 2000, 2200)  # Returns: 2
    """
    return sum(1 for e in elements
               if isinstance(e.get(field_name), (int, float))
               and min_value <= e[field_name] <= max_value)
