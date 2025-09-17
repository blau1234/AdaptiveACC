
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
    steps: List[StepModel] = Field(..., min_items=1, description="List of plan steps")



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

class CheckedComponent(BaseModel):
    """Model for individual IFC component compliance check result"""
    component_id: str = Field(..., description="IFC GUID or unique component identifier")
    component_type: str = Field(..., description="IFC class or category, e.g., IfcDoor, IfcWall")
    checked_rule: str = Field(..., description="The rule/check being applied")
    data_used: Dict[str, str] = Field(..., description="Key-value data used for compliance checking")
    compliance_status: str = Field(..., description="one of: compliant, non_compliant, uncertain")
    violation_reason: Optional[str] = Field(None, description="Reason for non-compliance if applicable")
    suggested_fix: Optional[str] = Field(None, description="Optional suggestion to fix non-compliance")


class RelationshipCheck(BaseModel):
    """Model for relationship-based compliance checks between IFC components"""
    relation_type: str = Field(..., description="Type of relationship being checked (e.g., geometry / topology / semantic)")
    relation_name: str = Field(..., description="Name of the relationship being checked")
    involved_components: List[str] = Field(..., description="List of components involved in the relationship")
    compliance_status: str = Field(..., description="Compliance status of the relationship")
    analysis_evidence: Optional[Dict[str, str]] = Field(None, description="Evidence supporting the compliance analysis")
    violation_reason: Optional[str] = Field(None, description="Reason for non-compliance if applicable")
    suggested_fix: Optional[str] = Field(None, description="Optional suggestion to fix non-compliance")


class ComplianceEvaluationModel(BaseModel):
    """Model for compliance evaluation results"""
    overall_status: str = Field(..., description="Aggregate status: compliant / non_compliant / partial / uncertain / not_applicable")
    compliant_components: List[CheckedComponent] = Field(..., description="List of compliant components")
    non_compliant_components: List[CheckedComponent] = Field(..., description="List of non-compliant components")
    uncertain_components: List[CheckedComponent] = Field(..., description="List of components with uncertain compliance")
    relationship_checks: Optional[List[RelationshipCheck]] = Field(None, description="List of relationship checks performed")


# === Meta Tools ===

class MetaToolResult(BaseModel):
    """Standardized result model for meta tool execution"""
    success: bool = Field(..., description="Whether the execution was successful")
    meta_tool_name: str = Field(..., description="Name of the meta tool executed")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


# === Tool Creation ===

class ToolSpec(BaseModel):
    """Tool requirement specification"""
    description: str = Field(..., description="Description of what the tool should do")
    function_name: str = Field(..., description="Name of the function to be created")
    parameters: List[Dict[str, Any]] = Field(..., description="List of function parameters")
    return_type: str = Field(..., description="Expected return type of the function")
    library: str = Field(default="ifcopenshell", description="Primary library used by this tool")


class RetrievedDocument(BaseModel):
    """Retrieved document from RAG system"""
    content: str = Field(..., description="Content of the retrieved document")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    relevance_score: float = Field(..., description="Relevance score for the document")


class ToolParam(BaseModel):
    """Function parameter definition"""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type, e.g., 'str', 'int', 'float', 'dict'")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(..., description="Is this parameter required?")
    default: Optional[str] = Field(None, description="Default value for the parameter (as a string)")


class ToolMetadata(BaseModel):
    """Metadata for the created tool"""
    description: str = Field(..., description="Short description of the tool")
    parameters: List[ToolParam] = Field(..., description="Function parameters")
    return_type: Optional[str] = Field(None, description="Function return type")
    category: str = Field(default="IfcOpenShell", description="Tool category for organization")
    tags: List[str] = Field(default_factory=list, description="Keywords for retrieval")


class ToolCreatorOutput(BaseModel):
    """Output model for tool creation"""
    tool_name: str = Field(..., description="Tool name, unique identifier")
    code: str = Field(..., description="Python function code as a string")
    metadata: ToolMetadata = Field(..., description="Tool metadata")


# === Tool Execution and Fixing ===

class DomainToolResult(BaseModel):
    """Result model for domain tool execution (syntax and runtime)"""
    success: bool = Field(..., description="Whether the code passed the check")
    domain_tool_name: str = Field(..., description="Tool name")
    result: Optional[Any] = Field(None, description="Result of code execution if successful")
    parameters_used: Dict[str, Any] = Field(default_factory=dict, description="Parameters used")

    # Error-related fields (only present when success=False)
    error_message: Optional[str] = Field(None, description="Error message")
    exception_type: Optional[str] = Field(None, description="Exception type, e.g., SyntaxError, RuntimeError")
    traceback: Optional[str] = Field(None, description="Complete stack trace")
    line_number: Optional[int] = Field(None, description="Line number where the error occurred")


class FixedCodeOutput(BaseModel):
    """Output model for fixed code"""
    code: str = Field(..., description="Fixed Python code")


# === Sandbox Executor ===

class TestResult(BaseModel):
    """Test execution result"""
    success: bool = Field(..., description="Whether the test was successful")
    output: str = Field(..., description="Test output message")
    error: str = Field(..., description="Error message if test failed")




