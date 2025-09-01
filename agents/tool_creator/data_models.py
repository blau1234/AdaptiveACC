
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ToolRequirement:
    """Tool requirement specification"""
    description: str
    function_name: str
    parameters: List[Dict[str, Any]]
    return_type: str
    examples: Optional[List[str]] = None


@dataclass
class AnalysisResult:
    """Result from SpecGenerator"""
    tool_requirement: ToolRequirement
    ifc_dependencies: Dict[str, Any]
    test_parameters: Dict[str, Any]  # Function parameters for testing
    reasoning: str


@dataclass
class RetrievedDocument:
    """Retrieved document from RAG system"""
    content: str
    metadata: Dict[str, Any]
    relevance_score: float

    
@dataclass
class ToolCreationResult:
    """Final result of tool creation process"""
    success: bool
    generated_code: str
    ifc_dependencies: Dict[str, Any]  
    issues: List[str]
    static_check_passes: int
    dynamic_test_passes: int


@dataclass
class StaticCheckResult:
    """Static code analysis result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


@dataclass
class TestResult:
    """Test execution result"""
    success: bool
    output: str
    error: str


@dataclass
class DynamicTestResult:
    """Dynamic testing result"""
    success: bool
    issues: List[str]
    data_availability: bool
    tool_execution: bool
    execution_details: Dict[str, Any]
    missing_elements: List[str]
    missing_properties: List[str]







