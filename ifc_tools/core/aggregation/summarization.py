"""
Tool: Data Summarization Operations
Category: aggregation
Description: Functions for calculating aggregated statistics and summaries
"""

from typing import List, Dict, Any, Callable


def sum_by_group(grouped_data: Dict[Any, List[Dict[str, Any]]], field_name: str) -> Dict[Any, float]:
    """Calculate sum of a numeric field for each group.


    Args:
        grouped_data: Dictionary of grouped elements (output from grouping functions)
        field_name: Name of the numeric field to sum

    Returns:
        Dictionary mapping group keys to sum values

    Example:
        grouped = {
            "Level 1": [{"area": 25.5}, {"area": 30.0}],
            "Level 2": [{"area": 20.0}]
        }
        sums = sum_by_group(grouped, "area")
        # Returns: {"Level 1": 55.5, "Level 2": 20.0}
    """
    result = {}
    for key, items in grouped_data.items():
        total = sum(item.get(field_name, 0) for item in items if isinstance(item.get(field_name), (int, float)))
        result[key] = total
    return result


def count_by_group(grouped_data: Dict[Any, List[Dict[str, Any]]]) -> Dict[Any, int]:
    """Count number of elements in each group.


    Args:
        grouped_data: Dictionary of grouped elements

    Returns:
        Dictionary mapping group keys to counts

    Example:
        grouped = {
            "Level 1": [{"id": "D1"}, {"id": "D2"}],
            "Level 2": [{"id": "D3"}]
        }
        counts = count_by_group(grouped)
        # Returns: {"Level 1": 2, "Level 2": 1}
    """
    return {key: len(items) for key, items in grouped_data.items()}


def average_by_group(grouped_data: Dict[Any, List[Dict[str, Any]]], field_name: str) -> Dict[Any, float]:
    """Calculate average of a numeric field for each group.


    Args:
        grouped_data: Dictionary of grouped elements
        field_name: Name of the numeric field to average

    Returns:
        Dictionary mapping group keys to average values

    Example:
        grouped = {
            "Level 1": [{"width": 900}, {"width": 800}],
            "Level 2": [{"width": 1000}]
        }
        averages = average_by_group(grouped, "width")
        # Returns: {"Level 1": 850.0, "Level 2": 1000.0}
    """
    result = {}
    for key, items in grouped_data.items():
        values = [item.get(field_name) for item in items if isinstance(item.get(field_name), (int, float))]
        if values:
            result[key] = sum(values) / len(values)
        else:
            result[key] = 0.0
    return result


def min_by_group(grouped_data: Dict[Any, List[Dict[str, Any]]], field_name: str) -> Dict[Any, float]:
    """Find minimum value of a numeric field for each group.


    Args:
        grouped_data: Dictionary of grouped elements
        field_name: Name of the numeric field

    Returns:
        Dictionary mapping group keys to minimum values

    Example:
        grouped = {
            "Level 1": [{"width": 900}, {"width": 800}],
            "Level 2": [{"width": 1000}]
        }
        minimums = min_by_group(grouped, "width")
        # Returns: {"Level 1": 800, "Level 2": 1000}
    """
    result = {}
    for key, items in grouped_data.items():
        values = [item.get(field_name) for item in items if isinstance(item.get(field_name), (int, float))]
        if values:
            result[key] = min(values)
        else:
            result[key] = None
    return result


def max_by_group(grouped_data: Dict[Any, List[Dict[str, Any]]], field_name: str) -> Dict[Any, float]:
    """Find maximum value of a numeric field for each group.


    Args:
        grouped_data: Dictionary of grouped elements
        field_name: Name of the numeric field

    Returns:
        Dictionary mapping group keys to maximum values

    Example:
        grouped = {
            "Level 1": [{"width": 900}, {"width": 800}],
            "Level 2": [{"width": 1000}]
        }
        maximums = max_by_group(grouped, "width")
        # Returns: {"Level 1": 900, "Level 2": 1000}
    """
    result = {}
    for key, items in grouped_data.items():
        values = [item.get(field_name) for item in items if isinstance(item.get(field_name), (int, float))]
        if values:
            result[key] = max(values)
        else:
            result[key] = None
    return result


# Removed: aggregate_with_custom_function - cannot generate JsonSchema for Callable parameter
# This function is not compatible with function calling APIs that require JSON schema generation
