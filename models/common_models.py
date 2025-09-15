
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# === Planner ===

class RegulationAnalysis(BaseModel):
    """Enhanced model for building regulation analysis results with comprehensive compliance checking information"""

    # Core regulation information
    original_text: str = Field(..., description="Original regulation text for reference")
    summary: str = Field(..., description="Concise summary of the regulation's main requirements")

    # Regulation scope and applicability
    scope: str = Field(..., description="Scope of applicability (e.g., means of egress, doors, stairs, accessibility)")
    applicability: Optional[Dict[str, Any]] = Field(default=None, description="Applicability conditions such as building type, door type, occupancy class")

    # IFC-specific information for compliance checking
    target_elements: List[str] = Field(..., description="IFC entities to be checked (e.g., IfcDoor, IfcStair, IfcWall, IfcSpace)")
    required_attributes: List[str] = Field(..., description="IFC attributes required for checking (e.g., Height, Width, Material)")

    # Compliance checking logic
    check_type: str = Field(..., description="Type of check required: existence, comparison, range, relation, geometry, or aggregation")
    check_conditions: List[str] = Field(..., description="Logical conditions extracted from regulation (e.g., 'width >= 800mm', 'height <= 2100mm')")

    # Additional regulation context
    dependencies: Optional[List[str]] = Field(default=None, description="References to other regulations or standards that this regulation depends on")
    exceptions: Optional[List[str]] = Field(default=None, description="Exceptions or exemptions specified in the regulation")


class StepModel(BaseModel):
    """Model for individual plan steps"""
    description: str = Field(..., min_length=1, description="Step description")
    task_type: str = Field(..., description="Type of task (e.g., measurement, validation, parsing)")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Step-specific inputs or parameters")
    expected_output: str = Field(..., description="Expected output description")


class PlanModel(BaseModel):
    """Model for structured plans"""
    plan_id: str = Field(..., description="Unique plan identifier")
    steps: List[StepModel] = Field(..., min_items=1, description="List of plan steps")


# === Meta Tools ===

class MetaToolResult(BaseModel):
    """Standardized result model for meta tool execution"""
    success: bool = Field(..., description="Whether the execution was successful")
    tool_name: str = Field(..., description="Name of the tool executed")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


# === Executor ===

class ReActResponse(BaseModel):
    """Structured ReAct response model for LLM output parsing"""
    thought: str = Field(..., description="Your reasoning about what needs to be done next")
    action: Optional[str] = Field(None, description="The exact tool name to use from available tools")
    action_input: Optional[Dict[str, Any]] = Field(None, description="Parameters for the selected tool")
    observation: Optional[str] = Field(None, description="Your interpretation of the previous action result, analyzing what was accomplished and its significance for the task")
    is_final: bool = Field(False, description="Whether this is the final response completing the task")


class StepExecutionResult(BaseModel):
    """Result model for Executor step execution"""

    # Core fields
    step_index: int = Field(..., description="Step position in plan.steps array")
    status: Literal["success", "timeout", "failed"] = Field(..., description="Execution status")

    # ReAct related
    execution_history: List[Dict[str, Any]] = Field(default_factory=list, description="ReAct iteration history")
    iterations_used: Optional[int] = Field(None, description="Number of iterations used")

    # Result related
    tool_results: List[Any] = Field(default_factory=list, description="Tool execution results")
    error: Optional[str] = Field(None, description="Error message if failed")


class ExecutionState(BaseModel):
    """Local state management for single step execution in Executor"""

    step_index: int = Field(..., description="Step position in plan.steps array")
    step: Dict[str, Any] = Field(..., description="Current step being executed")
 
    # ReAct iteration tracking
    history: List[Dict[str, Any]] = Field(default_factory=list, description="ReAct iteration history")
    tool_results: List[Any] = Field(default_factory=list, description="Successful tool execution results")
    last_observation: str = Field(..., description="Previous observation from last iteration (provides context for next iteration)")

    def add_iteration(self, iteration: int, thought: str, action: str):
        """Record a ReAct iteration"""
        self.history.append({
            "iteration": iteration,
            "thought": thought,
            "action": action
        })
        
    def add_tool_result(self, result: Any):
        """Add successful tool execution result"""
        if result:
            self.tool_results.append(result)

    def update_observation(self, observation: str):
        """Update last observation state for next iteration context"""
        self.last_observation = observation


# === Checker ===

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


# === Tool Creation ===

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
    issues: List[str] = Field(default_factory=list, description="List of issues encountered")
    static_check_passes: int = Field(..., description="Number of static checks passed")


class StaticCheckResult(BaseModel):
    """Static code analysis result"""
    is_valid: bool = Field(..., description="Whether the code passes static analysis")
    errors: List[str] = Field(default_factory=list, description="List of errors found")
    warnings: List[str] = Field(default_factory=list, description="List of warnings found")
    suggestions: List[str] = Field(default_factory=list, description="List of improvement suggestions")


# === Sandbox Executor ===

class TestResult(BaseModel):
    """Test execution result"""
    success: bool = Field(..., description="Whether the test was successful")
    output: str = Field(..., description="Test output message")
    error: str = Field(..., description="Error message if test failed")






