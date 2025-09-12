
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class RegulationAnalysis(BaseModel):
    """Model for regulation analysis results"""
    summary: str = Field(..., description="Concise summary of the regulation")
    requirements: List['Requirement'] = Field(default_factory=list, description="List of extracted requirements")


class Requirement(BaseModel):
    """Model for regulation requirements"""
    id: str = Field(..., description="Unique requirement identifier")
    description: str = Field(..., description="Requirement description")
    type: Literal["structural", "safety", "accessibility", "other"] = Field(..., description="Type of requirement")
    measurable: bool = Field(..., description="Whether requirement is measurable")
    criteria: Optional[str] = Field(None, description="Specific measurement criteria if applicable")


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
    modification_count: int = Field(default=0, ge=0, description="Number of modifications")
    status: Literal["active", "modified", "completed", "failed"] = Field(default="active", description="Plan status")


class ModifiedPlan(BaseModel):
    """Model for modified plan structure"""
    plan_id: str = Field(..., description="Plan identifier (should be preserved)")
    regulation_summary: str = Field(..., description="Regulation summary")
    steps: List[StepModel] = Field(..., min_items=1, description="Modified list of plan steps")


class ReActResponse(BaseModel):
    """Structured ReAct response model for LLM output parsing"""
    thought: str = Field(..., description="Your reasoning about what needs to be done next")
    action: Optional[str] = Field(None, description="The exact tool name to use from available tools")
    action_input: Optional[Dict[str, Any]] = Field(None, description="Parameters for the selected tool")
    is_final: bool = Field(False, description="Whether this is the final response completing the task")



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


class ViolationModel(BaseModel):
    """Model for compliance violations"""
    requirement: str = Field(..., description="Which requirement was violated")
    severity: Literal["critical", "major", "minor"] = Field(..., description="Severity level of violation")
    details: str = Field(..., description="What specifically failed")


class ComplianceEvaluationModel(BaseModel):
    """Model for compliance evaluation results"""
    compliant: bool = Field(..., description="Overall compliance status")
    summary: str = Field(..., description="One-line summary of compliance status")
    violations: List[ViolationModel] = Field(default_factory=list, description="List of violations found")
    passed_checks: List[str] = Field(default_factory=list, description="List of requirements that passed")
    recommendations: List[str] = Field(default_factory=list, description="Actionable steps to achieve compliance")



class ToolRequirement(BaseModel):  
    """Tool requirement specification"""
    description: str = Field(..., description="Description of what the tool should do")
    function_name: str = Field(..., description="Name of the function to be created")
    parameters: List[Dict[str, Any]] = Field(..., description="List of function parameters")
    return_type: str = Field(..., description="Expected return type of the function")
    examples: Optional[List[str]] = Field(None, description="Optional usage examples")
    library: str = Field(default="ifcopenshell", description="Primary library used by this tool")


class RetrievedDocument(BaseModel):
    """Retrieved document from RAG system"""
    content: str = Field(..., description="Content of the retrieved document")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    relevance_score: float = Field(..., description="Relevance score for the document")

    
class ToolCreationResult(BaseModel):
    """Final result of tool creation process"""
    success: bool = Field(..., description="Whether tool creation was successful")
    generated_code: str = Field(..., description="The generated tool code")
    ifc_dependencies: Dict[str, Any] = Field(..., description="IFC-related dependencies")
    issues: List[str] = Field(default_factory=list, description="List of issues encountered")
    static_check_passes: int = Field(..., description="Number of static checks passed")


class StaticCheckResult(BaseModel):
    """Static code analysis result"""
    is_valid: bool = Field(..., description="Whether the code passes static analysis")
    errors: List[str] = Field(default_factory=list, description="List of errors found")
    warnings: List[str] = Field(default_factory=list, description="List of warnings found")
    suggestions: List[str] = Field(default_factory=list, description="List of improvement suggestions")


class TestResult(BaseModel):
    """Test execution result"""
    success: bool = Field(..., description="Whether the test was successful")
    output: str = Field(..., description="Test output message")
    error: str = Field(..., description="Error message if test failed")





