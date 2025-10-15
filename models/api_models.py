"""
Pydantic models for API requests and responses
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class ComplianceCheckRequest(BaseModel):
    """Model for compliance check API request"""
    regulation: str = Field(..., min_length=10, description="Building code regulation text")
    
    @field_validator('regulation')
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

    @field_validator('steps_completed')
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


# Admin API Models

class ToolInfo(BaseModel):
    """Model for tool information"""
    name: str = Field(..., description="Tool name")
    category: str = Field(..., description="Tool category")
    description: str = Field(..., description="Tool description")
    created_at: str = Field(..., description="Creation timestamp")
    file_path: str = Field(..., description="File path")


class ToolListResponse(BaseModel):
    """Model for tool list response"""
    tools: List[ToolInfo] = Field(..., description="List of tools")
    total_count: int = Field(..., description="Total number of tools")
    category_filter: Optional[str] = Field(None, description="Applied category filter")


class ToolDeletionResponse(BaseModel):
    """Model for tool deletion response"""
    success: bool = Field(..., description="Deletion success status")
    message: str = Field(..., description="Deletion result message")
    tool_name: str = Field(..., description="Name of the deleted tool")
    filesystem_deleted: Optional[bool] = Field(None, description="Filesystem deletion status")
    vector_deleted: Optional[bool] = Field(None, description="Vector DB deletion status")


class ToolStorageStats(BaseModel):
    """Model for tool storage statistics"""
    total_tools: int = Field(..., description="Total number of stored tools")
    categories: Dict[str, int] = Field(..., description="Tools count by category")
    vector_db_available: bool = Field(..., description="Vector database availability")
    storage_directory: str = Field(..., description="Storage directory path")
    vector_db_stats: Optional[Dict[str, Any]] = Field(None, description="Vector database statistics")
    error: Optional[str] = Field(None, description="Error message if any")