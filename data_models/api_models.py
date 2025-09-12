"""
Pydantic models for API requests and responses
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from .shared_models import PlanModel, ExecutionResultModel


class ComplianceCheckRequest(BaseModel):
    """Model for compliance check API request"""
    regulation: str = Field(..., min_length=10, description="Building code regulation text")
    
    @validator('regulation')
    def validate_regulation_content(cls, v):
        if not v.strip():
            raise ValueError('Regulation text cannot be empty or whitespace only')
        return v.strip()


class CoordinationInfoModel(BaseModel):
    """Model for coordination information"""
    execution_status: str = Field(..., description="Overall execution status")
    feedback_rounds_used: int = Field(..., ge=0, description="Number of feedback rounds used")
    steps_completed: int = Field(..., ge=0, description="Number of steps completed")
    total_steps: int = Field(..., ge=0, description="Total number of steps")
    communication_summary: Dict[str, Any] = Field(default_factory=dict, description="Communication summary")
    
    @validator('steps_completed')
    def validate_steps_completed(cls, v, values):
        if 'total_steps' in values and v > values['total_steps']:
            raise ValueError('Steps completed cannot exceed total steps')
        return v


class ComplianceCheckResponse(BaseModel):
    """Model for compliance check API response"""
    report: Dict[str, Any] = Field(..., description="Compliance report")


class HealthCheckResponse(BaseModel):
    """Model for health check response"""
    status: str = Field(..., description="System health status")
    system: str = Field(..., description="System name")
    version: str = Field(..., description="System version")
    components: Dict[str, str] = Field(..., description="Component status")


class ErrorResponse(BaseModel):
    """Model for error responses"""
    detail: str = Field(..., description="Error detail message")
    error_code: Optional[str] = Field(None, description="Error code if applicable")
    timestamp: Optional[str] = Field(None, description="Error timestamp")