"""
Tool: Ratio and Percentage Calculations
Category: quantification
Description: Pure mathematical functions for ratio and percentage calculations
"""

from typing import List, Dict, Any, Optional


def calculate_ratio(numerator: int, denominator: int) -> float:
    """Calculate ratio of two numbers (numerator / denominator).

    Args:
        numerator: Numerator value
        denominator: Denominator value

    Returns:
        Ratio as float (numerator/denominator). Returns 0.0 if denominator is 0.

    Example:
        ratio = calculate_ratio(5, 20)  # Returns: 0.25
        ratio = calculate_ratio(10, 0)  # Returns: 0.0 (safe division)
    """
    return numerator / denominator if denominator > 0 else 0.0


def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage of part relative to total.

    Args:
        part: Part value (numerator)
        total: Total value (denominator)

    Returns:
        Percentage as float (0-100 range). Returns 0.0 if total is 0.

    Example:
        percentage = calculate_percentage(5, 20)  # Returns: 25.0 (means 25%)
        percentage = calculate_percentage(3, 10)  # Returns: 30.0 (means 30%)
    """
    return (part / total * 100) if total > 0 else 0.0


def calculate_ratio_from_elements(elements: List[Dict],
                                  numerator_property: str,
                                  numerator_value: Any,
                                  denominator_property: Optional[str] = None,
                                  denominator_value: Optional[Any] = None) -> float:
    """Calculate ratio by counting elements matching property conditions.

    Args:
        elements: List of element dictionaries
        numerator_property: Property name for numerator condition
        numerator_value: Property value to match for numerator
        denominator_property: Property name for denominator (None = use all elements)
        denominator_value: Property value to match for denominator

    Returns:
        Ratio as float (numerator_count / denominator_count). Returns 0.0 if denominator is 0.

    Example:
        doors = [{'fire_rating': 'FD30'}, {'fire_rating': None}, {'fire_rating': 'FD30'}]
        ratio = calculate_ratio_from_elements(doors, 'fire_rating', 'FD30', None, None)
        # Returns: 0.67 (2 out of 3)
    """
    # Count numerator elements
    numerator_count = sum(1 for e in elements
                         if e.get(numerator_property) == numerator_value)

    # Count denominator elements
    if denominator_property is None:
        # Use all elements as denominator
        denominator_count = len(elements)
    else:
        # Count elements matching denominator condition
        denominator_count = sum(1 for e in elements
                               if e.get(denominator_property) == denominator_value)

    return numerator_count / denominator_count if denominator_count > 0 else 0.0
