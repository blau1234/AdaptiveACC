"""
Tool: Numerical Comparison Operations
Category: quantification
Description: Pure comparison functions for finding min/max values and threshold comparisons
"""

from typing import List, Dict, Any


def find_min_value(elements: List[Dict], field_name: str) -> float:
    """Find the minimum value of a numeric field across all elements.

    Args:
        elements: List of element dictionaries
        field_name: Name of the numeric field to analyze

    Returns:
        Minimum value as float. Returns float('inf') if no valid numeric values found.

    Example:
        spaces = [
            {'element_id': '1', 'area': 25.5},
            {'element_id': '2', 'area': 15.0},
            {'element_id': '3', 'area': 30.0}
        ]
        min_area = find_min_value(spaces, 'area')  # Returns: 15.0
    """
    values = [e[field_name] for e in elements
              if field_name in e and isinstance(e[field_name], (int, float))]
    return min(values) if values else float('inf')


def find_max_value(elements: List[Dict], field_name: str) -> float:
    """Find the maximum value of a numeric field across all elements.

    Args:
        elements: List of element dictionaries
        field_name: Name of the numeric field to analyze

    Returns:
        Maximum value as float. Returns float('-inf') if no valid numeric values found.

    Example:
        doors = [
            {'element_id': '1', 'width': 900},
            {'element_id': '2', 'width': 750},
            {'element_id': '3', 'width': 1000}
        ]
        max_width = find_max_value(doors, 'width')  # Returns: 1000
    """
    values = [e[field_name] for e in elements
              if field_name in e and isinstance(e[field_name], (int, float))]
    return max(values) if values else float('-inf')


def compare_counts(count_a: int, count_b: int) -> Dict[str, Any]:
    """Compare two count values and return detailed comparison results.

    Args:
        count_a: First count value
        count_b: Second count value

    Returns:
        Dictionary with comparison details:
        - 'count_a': First count
        - 'count_b': Second count
        - 'difference': count_a - count_b (positive if a>b, negative if a<b)
        - 'larger': 'a' if count_a > count_b, 'b' if count_b > count_a, 'equal' if same

    Example:
        result = compare_counts(10, 15)
        # Returns: {
        #     'count_a': 10,
        #     'count_b': 15,
        #     'difference': -5,
        #     'larger': 'b'
        # }
    """
    return {
        'count_a': count_a,
        'count_b': count_b,
        'difference': count_a - count_b,
        'larger': 'a' if count_a > count_b else ('b' if count_b > count_a else 'equal')
    }


def compare_to_threshold(value: float, threshold: float, operator: str) -> Dict[str, Any]:
    """Compare a numeric value to a threshold using specified operator.

    Args:
        value: Numeric value to compare
        threshold: Threshold value
        operator: Comparison operator as string: '>', '<', '>=', '<=', '==', '!='

    Returns:
        Dict with comparison string and boolean result

    Example:
        result = compare_to_threshold(1000, 914.4, '>=')
        # Returns: {"comparison": "1000 >= 914.4", "meets_threshold": True}

        result = compare_to_threshold(800, 914.4, '>=')
        # Returns: {"comparison": "800 >= 914.4", "meets_threshold": False}
    """
    operators = {
        '>': lambda v, t: v > t,
        '<': lambda v, t: v < t,
        '>=': lambda v, t: v >= t,
        '<=': lambda v, t: v <= t,
        '==': lambda v, t: v == t,
        '!=': lambda v, t: v != t
    }

    meets_threshold = operators.get(operator, lambda v, t: False)(value, threshold)
    comparison = f"{value} {operator} {threshold}"

    return {
        "comparison": comparison,
        "meets_threshold": meets_threshold
    }


def compare_elements_to_threshold(
    elements: List[Dict],
    field_name: str,
    threshold: float,
    operator: str,
    unit: str = ""
) -> List[Dict[str, Any]]:
    """Compare multiple elements' field values to a threshold, returning detailed results for each.

    Args:
        elements: List of element dictionaries containing the field to compare
        field_name: Name of the numeric field to compare in each element
        threshold: Threshold value for comparison
        operator: Comparison operator as string: '>', '<', '>=', '<=', '==', '!='
        unit: Optional unit string to append to values (e.g., 'mm', 'm', 'inches')

    Returns:
        List of dicts, each containing:
        - element_id: Element identifier from input
        - comparison: Human-readable comparison string (e.g., "1000mm >= 914mm")
        - meets_threshold: Boolean result of the comparison

    Example:
        stairs = [
            {'element_id': 'stair_A', 'width': 1000},
            {'element_id': 'stair_B', 'width': 800}
        ]
        result = compare_elements_to_threshold(stairs, 'width', 914, '>=', 'mm')
        # Returns: [
        #   {'element_id': 'stair_A', 'comparison': '1000mm >= 914mm', 'meets_threshold': True},
        #   {'element_id': 'stair_B', 'comparison': '800mm >= 914mm', 'meets_threshold': False}
        # ]
    """
    results = []

    for elem in elements:
        if field_name not in elem:
            continue

        value = elem[field_name]

        # Use the single-value comparison function
        comparison_result = compare_to_threshold(value, threshold, operator)

        # Format comparison string with units if provided
        value_str = f"{value}{unit}" if unit else str(value)
        threshold_str = f"{threshold}{unit}" if unit else str(threshold)

        results.append({
            "element_id": elem.get("element_id", "unknown"),
            "comparison": f"{value_str} {operator} {threshold_str}",
            "meets_threshold": comparison_result["meets_threshold"]
        })

    return results
