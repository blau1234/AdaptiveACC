"""
Pydantic models for agent communication messages
"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field
from .shared_models import PlanModel, StepModel, ExecutionResultModel, StepExecutionResultModel, ComplianceReportModel


class BaseMessage(BaseModel):
    """Base model for all agent communication messages"""
    message_type: str = Field(..., description="Type of message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    sender: str = Field(..., description="Sender agent name")
    recipient: str = Field(..., description="Recipient agent name")


class PlanRequestMessage(BaseMessage):
    """Model for plan request messages"""
    message_type: Literal["plan_request"] = "plan_request"
    payload: Dict[str, Any] = Field(..., description="Request payload")
    
    class Payload(BaseModel):
        regulation_text: str = Field(..., min_length=1, description="Building regulation text")
        request_type: Literal["initial_plan"] = "initial_plan"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class PlanResponseMessage(BaseMessage):
    """Model for plan response messages"""
    message_type: Literal["plan_response"] = "plan_response"
    payload: Dict[str, Any] = Field(..., description="Response payload")
    
    class Payload(BaseModel):
        plan: PlanModel = Field(..., description="Generated plan")
        status: Literal["success", "failed"] = Field(..., description="Request status")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class StepExecutionRequestMessage(BaseMessage):
    """Model for step execution request messages"""
    message_type: Literal["step_execution_request"] = "step_execution_request"
    payload: Dict[str, Any] = Field(..., description="Request payload")
    
    class Payload(BaseModel):
        step: StepModel = Field(..., description="Step to execute")
        ifc_file_path: str = Field(..., description="Path to IFC file")
        step_index: int = Field(..., ge=0, description="Step index")
        request_type: Literal["execute_single_step"] = "execute_single_step"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class StepExecutionResponseMessage(BaseMessage):
    """Model for step execution response messages"""
    message_type: Literal["step_execution_response"] = "step_execution_response"
    payload: Dict[str, Any] = Field(..., description="Response payload")
    
    class Payload(BaseModel):
        step_result: StepExecutionResultModel = Field(..., description="Step execution result")
        step_index: int = Field(..., ge=0, description="Step index")
        status: Literal["success", "failed"] = Field(..., description="Execution status")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class ModificationRequestMessage(BaseMessage):
    """Model for plan modification request messages"""
    message_type: Literal["modification_request"] = "modification_request"
    payload: Dict[str, Any] = Field(..., description="Request payload")
    
    class Payload(BaseModel):
        current_plan: PlanModel = Field(..., description="Current plan to modify")
        feedback: Dict[str, Any] = Field(..., description="Feedback for modification")
        request_type: Literal["modify_plan"] = "modify_plan"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class ModificationResponseMessage(BaseMessage):
    """Model for plan modification response messages"""
    message_type: Literal["modification_response"] = "modification_response"
    payload: Dict[str, Any] = Field(..., description="Response payload")
    
    class Payload(BaseModel):
        modified_plan: PlanModel = Field(..., description="Modified plan")
        status: Literal["success", "failed"] = Field(..., description="Modification status")
        modification_count: int = Field(..., ge=0, description="Number of modifications")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class ComplianceCheckRequestMessage(BaseMessage):
    """Model for compliance check request messages"""
    message_type: Literal["compliance_check_request"] = "compliance_check_request"
    payload: Dict[str, Any] = Field(..., description="Request payload")
    
    class Payload(BaseModel):
        execution_results: List[ExecutionResultModel] = Field(..., description="Execution results")
        regulation_text: str = Field(..., min_length=1, description="Regulation text")
        plan: PlanModel = Field(..., description="Execution plan")
        request_type: Literal["check_compliance"] = "check_compliance"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)


class ComplianceCheckResponseMessage(BaseMessage):
    """Model for compliance check response messages"""
    message_type: Literal["compliance_check_response"] = "compliance_check_response"
    payload: Dict[str, Any] = Field(..., description="Response payload")
    
    class Payload(BaseModel):
        compliance_report: ComplianceReportModel = Field(..., description="Compliance report")
        status: Literal["success", "failed"] = Field(..., description="Check status")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate payload structure
        self.Payload(**self.payload)