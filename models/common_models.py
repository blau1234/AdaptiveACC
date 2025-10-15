
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# === Regulation Interpretation ===

class TermClarification(BaseModel):
    """Clarification for a specific technical term in a regulation"""

    term: str = Field(..., description="The term to clarify")
    meaning: str = Field(..., description="What this term means in the regulation context")
    ifc_mapping: Optional[str] = Field(None, description="How this term maps to IFC entities/properties (e.g., 'exit → IfcDoor with IsExternal=True')")
    examples: List[str] = Field(default_factory=list, description="Examples to illustrate the concept")


class RegulationInterpretation(BaseModel):
    """Human-readable interpretation of a regulation with disambiguated semantics"""
    plain_language: str = Field(..., description="Simple explanation of the regulation in everyday language (2-3 sentences)")
    term_clarifications: List[TermClarification] = Field(default_factory=list, description="Clarifications for technical terms and concepts that may be ambiguous")
    common_misunderstandings: List[str] = Field(default_factory=list, description="Common mistakes or misinterpretations to avoid when implementing this check")


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


# === Agent Tools ===

class AgentToolResult(BaseModel):
    """Standardized result model for agent tool execution"""
    success: bool = Field(..., description="Whether the execution was successful")
    agent_tool_name: str = Field(..., description="Name of the agent tool executed")
    result: Optional[Any] = Field(None, description="Result data if successful")
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
    ifc_tool_name: str = Field(..., description="Tool name, unique identifier")
    description: str = Field(..., description="Short description of the tool")
    parameters: List[ToolParam] = Field(..., description="Function parameters")
    return_type: Optional[str] = Field(None, description="Function return type")
    category: str = Field(default="IfcOpenShell", description="Tool category for organization")
    tags: List[str] = Field(default_factory=list, description="Keywords for retrieval")


class ToolCreatorOutput(BaseModel):
    """Output model for tool creation"""
    ifc_tool_name: str = Field(..., description="Tool name, unique identifier")
    code: str = Field(..., description="Python function code as a string")
    metadata: ToolMetadata = Field(..., description="Tool metadata")


# === IFC Tool Execution and Fixing ===

class IFCToolResult(BaseModel):
    """Result model for IFC tool execution (syntax and runtime)"""
    success: bool = Field(..., description="Whether the code passed the check")
    ifc_tool_name: str = Field(..., description="IFC tool name")
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


# === ComplianceAgent ===

class SubgoalModel(BaseModel):
    """Subgoal model - replaces StepModel"""
    id: int = Field(..., description="Subgoal ID")
    description: str = Field(..., min_length=1, description="Goal description (WHAT to achieve, not HOW)")
    status: Literal["pending", "in_progress", "completed"] = Field(default="pending", description="Subgoal status")
    rationale: Optional[str] = Field(None, description="Why this subgoal is needed")


class SubgoalSetModel(BaseModel):
    """Subgoal collection - replaces PlanModel
    Note: subgoals can be empty initially in ReAct architecture, as the agent may generate them dynamically during execution.
    """
    subgoals: List[SubgoalModel] = Field(default_factory=list, description="List of subgoals (can be empty initially)")
    regulation_summary: str = Field(default="", description="Brief summary of the regulation")


class AgentResult(BaseModel):
    """ReAct agent execution result"""
    status: Literal["success", "timeout", "failed"] = Field(..., description="Execution status")
    iterations_used: int = Field(..., description="Number of ReAct iterations used")
    agent_history: List[Dict[str, Any]] = Field(default_factory=list, description="Complete ReAct history")
    compliance_result: Optional[ComplianceEvaluationModel] = Field(None, description="Final compliance evaluation result")
    error: Optional[str] = Field(None, description="Error message if failed")


