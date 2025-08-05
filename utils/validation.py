"""
Validation utilities using Pydantic models
"""

from typing import Dict, Any, List
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


def validate_regulation_text(regulation: str) -> str:
    """
    Validate regulation text input
    
    Args:
        regulation: Raw regulation text
        
    Returns:
        str: Cleaned and validated regulation text
        
    Raises:
        ValueError: If regulation text is invalid
    """
    if not regulation or not regulation.strip():
        raise ValueError("Regulation text cannot be empty")
    
    cleaned = regulation.strip()
    if len(cleaned) < 10:
        raise ValueError("Regulation text must be at least 10 characters long")
    
    return cleaned


def validate_execution_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate execution result structure
    
    Args:
        result: Raw execution result
        
    Returns:
        Dict[str, Any]: Validated execution result
        
    Raises:
        ValueError: If result structure is invalid
    """
    required_fields = ["result", "detail"]
    
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required field: {field}")
    
    if result["result"] not in ["pass", "fail"]:
        raise ValueError("Result must be 'pass' or 'fail'")
    
    # Ensure optional fields have default values
    result.setdefault("elements_checked", [])
    result.setdefault("issues", [])
    
    return result


def validate_step_structure(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate step structure
    
    Args:
        step: Raw step data
        
    Returns:
        Dict[str, Any]: Validated step
        
    Raises:
        ValueError: If step structure is invalid
    """
    required_fields = ["step_id", "description", "task_type", "expected_output"]
    
    for field in required_fields:
        if field not in step:
            raise ValueError(f"Missing required field in step: {field}")
    
    # Ensure optional fields have default values
    step.setdefault("required_tools", [])
    step.setdefault("parameters", {})
    
    return step


def validate_plan_structure(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate plan structure
    
    Args:
        plan: Raw plan data
        
    Returns:
        Dict[str, Any]: Validated plan
        
    Raises:
        ValueError: If plan structure is invalid
    """
    required_fields = ["plan_id", "steps"]
    
    for field in required_fields:
        if field not in plan:
            raise ValueError(f"Missing required field in plan: {field}")
    
    if not isinstance(plan["steps"], list) or len(plan["steps"]) == 0:
        raise ValueError("Plan must have at least one step")
    
    # Validate each step
    validated_steps = []
    for i, step in enumerate(plan["steps"]):
        try:
            validated_steps.append(validate_step_structure(step))
        except ValueError as e:
            raise ValueError(f"Invalid step {i}: {e}")
    
    plan["steps"] = validated_steps
    
    # Ensure optional fields have default values
    plan.setdefault("regulation_id", "unknown")
    plan.setdefault("modification_count", 0)
    plan.setdefault("status", "active")
    plan.setdefault("metadata", {})
    
    return plan


def safe_validate(validator_func, data, default_value=None, log_errors=True):
    """
    Safely validate data with error handling
    
    Args:
        validator_func: Validation function to call
        data: Data to validate
        default_value: Value to return if validation fails
        log_errors: Whether to log validation errors
        
    Returns:
        Validated data or default_value if validation fails
    """
    try:
        return validator_func(data)
    except (ValueError, ValidationError) as e:
        if log_errors:
            logger.warning(f"Validation failed: {e}")
        return default_value or data