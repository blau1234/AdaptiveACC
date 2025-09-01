"""
Shared Pydantic models used across the system
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator


class StepModel(BaseModel):
    """Model for individual plan steps"""
    step_id: str = Field(..., description="Unique step identifier")
    description: str = Field(..., min_length=1, description="Step description")
    task_type: str = Field(..., description="Type of task (measurement, validation, etc.)")
    required_tools: List[str] = Field(default_factory=list, description="Tools needed for this step")
    expected_output: str = Field(..., description="Expected output description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Step-specific parameters")


class PlanModel(BaseModel):
    """Model for structured plans"""
    plan_id: str = Field(..., description="Unique plan identifier")
    regulation_id: str = Field(..., description="Associated regulation identifier")
    steps: List[StepModel] = Field(..., min_items=1, description="List of plan steps")
    creation_timestamp: datetime = Field(default_factory=datetime.now, description="Plan creation time")
    modification_count: int = Field(default=0, ge=0, description="Number of modifications")
    status: Literal["active", "modified", "completed", "failed"] = Field(default="active", description="Plan status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional plan metadata")


class ExecutionResultModel(BaseModel):
    """Model for execution results"""
    result: Literal["pass", "fail"] = Field(..., description="Execution result status")
    detail: str = Field(..., description="Detailed result description")
    elements_checked: List[str] = Field(default_factory=list, description="List of checked elements")
    issues: List[str] = Field(default_factory=list, description="List of issues found")


class StepExecutionResultModel(BaseModel):
    """Model for single step execution results"""
    step_status: Literal["success", "failed"] = Field(..., description="Step execution status")
    step_result: ExecutionResultModel = Field(..., description="Detailed step result")
    failure_reason: Optional[str] = Field(None, description="Reason for failure if applicable")
    error_message: Optional[str] = Field(None, description="Error message if any")
    execution_details: Dict[str, Any] = Field(default_factory=dict, description="Additional execution details")


