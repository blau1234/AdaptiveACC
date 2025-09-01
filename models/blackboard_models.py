from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ComplianceCheckBlackboard:
    
    # Session information
    session_id: str = ""
    
    # Input data
    regulation_text: str = ""
    ifc_file_path: str = ""
    
    # Plan data
    current_plan: Dict[str, Any] = field(default_factory=dict)
    plan_history: List[Dict[str, Any]] = field(default_factory=list)
    plan_modifications: List[Dict[str, Any]] = field(default_factory=list)
    
    # Execution data
    current_step_index: int = 0
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    step_execution_history: List[Dict[str, Any]] = field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool creation data
    created_tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # step_id -> tool_info
    tool_creation_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool Creator sub-agents data
    tool_creator_state: Dict[str, Any] = field(default_factory=dict)
    
    # Requirement Agent data
    requirement_analyses: List[Dict[str, Any]] = field(default_factory=list)  # step_id -> AnalysisResult
    generated_requirements: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # step_id -> ToolRequirement
    
    # Code Generator data  
    code_generation_history: List[Dict[str, Any]] = field(default_factory=list)
    generated_code_versions: Dict[str, List[str]] = field(default_factory=dict)  # step_id -> code versions
    
    # RAG Retriever data
    retrieved_documents: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # step_id -> documents
    rag_queries: List[Dict[str, Any]] = field(default_factory=list)
    
    # Static Checker data
    static_check_results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # step_id -> check results
    static_check_iterations: Dict[str, int] = field(default_factory=dict)  # step_id -> iteration count
    
    # Dynamic Tester data  
    dynamic_test_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # step_id -> test results
    test_execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Agent communication
    communication_log: List[Dict[str, Any]] = field(default_factory=list)
    feedback_rounds: int = 0
    max_feedback_rounds: int = 3
    
    # Status tracking
    current_phase: str = "initialization"  # initialization, planning, execution, checking, completed
    execution_status: str = "in_progress"  # in_progress, completed, failed, max_rounds_exceeded
    
    # Shared data between agents
    shared_context: Dict[str, Any] = field(default_factory=dict)
    
    # IFC analysis cache (shared between agents)
    ifc_elements_cache: Dict[str, List[Any]] = field(default_factory=dict)
    ifc_properties_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def add_communication(self, sender: str, recipient: str, message_type: str, payload: Dict[str, Any]):
        """Add communication message to log"""
        self.communication_log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sender": sender,
            "recipient": recipient, 
            "message_type": message_type,
            "payload": payload
        })
    
    def add_execution_result(self, result: Dict[str, Any]):
        """Add execution result"""
        self.execution_results.append(result)
    
    def add_step_history(self, step_result: Dict[str, Any]):
        """Add step execution history"""
        self.step_execution_history.append(step_result)
    
    def add_failed_step(self, step: Dict[str, Any], error: str):
        """Add failed step information"""
        self.failed_steps.append({
            "step": step,
            "error": error,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "step_index": self.current_step_index
        })
    
    def update_plan(self, new_plan: Dict[str, Any], modification_reason: str = ""):
        """Update current plan and track history"""
        if self.current_plan:
            self.plan_history.append(self.current_plan.copy())
        
        self.current_plan = new_plan
        self.plan_modifications.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": modification_reason,
            "modification_count": len(self.plan_modifications) + 1
        })
    
    def add_created_tool(self, step_id: str, tool_info: Dict[str, Any]):
        """Add information about created tool"""
        self.created_tools[step_id] = tool_info
        self.tool_creation_results.append({
            "step_id": step_id,
            "tool_info": tool_info,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    def set_phase(self, phase: str):
        """Update current phase"""
        self.current_phase = phase
        self.shared_context["phase_changed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def add_requirement_analysis(self, step_id: str, analysis_result: Dict[str, Any]):
        """Add requirement analysis result"""
        analysis_data = {
            "step_id": step_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_result": analysis_result
        }
        self.requirement_analyses.append(analysis_data)
        if step_id not in self.generated_requirements:
            self.generated_requirements[step_id] = analysis_result.get("tool_requirement", {})
    
    def add_generated_code_version(self, step_id: str, code: str, metadata: Dict[str, Any] = None):
        """Add generated code version"""
        if step_id not in self.generated_code_versions:
            self.generated_code_versions[step_id] = []
        self.generated_code_versions[step_id].append(code)
        
        # Also add to generation history with metadata
        generation_data = {
            "step_id": step_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "code_length": len(code),
            "version": len(self.generated_code_versions[step_id]),
            "metadata": metadata or {}
        }
        self.code_generation_history.append(generation_data)
    
    def add_retrieved_documents(self, step_id: str, documents: List[Dict[str, Any]], query: str = ""):
        """Add retrieved documents from RAG"""
        if step_id not in self.retrieved_documents:
            self.retrieved_documents[step_id] = []
        self.retrieved_documents[step_id].extend(documents)
        
        # Add query to history
        query_data = {
            "step_id": step_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "documents_count": len(documents)
        }
        self.rag_queries.append(query_data)
    
    def add_static_check_result(self, step_id: str, check_result: Dict[str, Any]):
        """Add static check result"""
        if step_id not in self.static_check_results:
            self.static_check_results[step_id] = []
        
        check_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": check_result,
            "iteration": len(self.static_check_results[step_id]) + 1
        }
        self.static_check_results[step_id].append(check_data)
        self.static_check_iterations[step_id] = len(self.static_check_results[step_id])
    
    def add_dynamic_test_result(self, step_id: str, test_result: Dict[str, Any]):
        """Add dynamic test result"""
        test_data = {
            "step_id": step_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": test_result
        }
        self.dynamic_test_results[step_id] = test_result
        self.test_execution_history.append(test_data)
    
    def get_tool_creation_status(self, step_id: str) -> Dict[str, Any]:
        """Get complete tool creation status for a step"""
        return {
            "step_id": step_id,
            "has_requirement": step_id in self.generated_requirements,
            "code_versions": len(self.generated_code_versions.get(step_id, [])),
            "retrieved_docs": len(self.retrieved_documents.get(step_id, [])),
            "static_checks": len(self.static_check_results.get(step_id, [])),
            "has_dynamic_test": step_id in self.dynamic_test_results,
            "is_completed": step_id in self.created_tools
        }
    
    def get_tool_creator_statistics(self) -> Dict[str, Any]:
        """Get ToolCreator system statistics"""
        return {
            "total_requirement_analyses": len(self.requirement_analyses),
            "total_code_generations": len(self.code_generation_history),
            "total_rag_queries": len(self.rag_queries),
            "total_static_checks": sum(len(checks) for checks in self.static_check_results.values()),
            "total_dynamic_tests": len(self.test_execution_history),
            "steps_with_requirements": len(self.generated_requirements),
            "steps_with_code": len(self.generated_code_versions),
            "steps_with_tests": len(self.dynamic_test_results),
            "completed_tools": len(self.created_tools)
        }
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context"""
        tool_creator_stats = self.get_tool_creator_statistics()
        return {
            "session_id": self.session_id,
            "current_phase": self.current_phase,
            "execution_status": self.execution_status,
            "current_step": f"{self.current_step_index + 1}/{len(self.current_plan.get('steps', []))}",
            "total_communications": len(self.communication_log),
            "total_execution_results": len(self.execution_results),
            "total_created_tools": len(self.created_tools),
            "feedback_rounds": self.feedback_rounds,
            "failed_steps_count": len(self.failed_steps),
            "tool_creator_stats": tool_creator_stats
        }


class BlackboardMixin:
    """
    Mixin class that provides blackboard functionality to agents
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._blackboard: Optional[ComplianceCheckBlackboard] = None
    
    def set_blackboard(self, blackboard: ComplianceCheckBlackboard):
        """Set the shared blackboard"""
        self._blackboard = blackboard
    
    @property
    def blackboard(self) -> ComplianceCheckBlackboard:
        """Get the shared blackboard"""
        if self._blackboard is None:
            raise RuntimeError("Blackboard not set. Call set_blackboard() first.")
        return self._blackboard
    
    def log_communication(self, recipient: str, message_type: str, payload: Dict[str, Any]):
        """Log communication to blackboard"""
        sender = self.__class__.__name__.lower().replace('agent', '').replace('coordinator', 'coordinator')
        self.blackboard.add_communication(sender, recipient, message_type, payload)
    
    def update_phase(self, phase: str):
        """Update current phase in blackboard"""
        self.blackboard.set_phase(phase)
    
    def get_shared_context(self, key: str, default=None):
        """Get value from shared context"""
        return self.blackboard.shared_context.get(key, default)
    
    def set_shared_context(self, key: str, value: Any):
        """Set value in shared context"""
        self.blackboard.shared_context[key] = value
    
    def get_current_plan(self) -> Dict[str, Any]:
        """Get current plan from blackboard"""
        return self.blackboard.current_plan
    
    def get_execution_results(self) -> List[Dict[str, Any]]:
        """Get all execution results from blackboard"""
        return self.blackboard.execution_results
    
    def get_ifc_file_path(self) -> str:
        """Get IFC file path from blackboard"""
        return self.blackboard.ifc_file_path
    
    def get_regulation_text(self) -> str:
        """Get regulation text from blackboard"""
        return self.blackboard.regulation_text
    
    # Tool Creator convenience methods
    def log_requirement_analysis(self, step_id: str, analysis_result: Dict[str, Any]):
        """Log requirement analysis result to blackboard"""
        self.blackboard.add_requirement_analysis(step_id, analysis_result)
        self.log_communication("requirement_agent", "analysis_completed", {
            "step_id": step_id,
            "function_name": analysis_result.get("tool_requirement", {}).get("function_name", "unknown")
        })
    
    def log_code_generation(self, step_id: str, code: str, metadata: Dict[str, Any] = None):
        """Log code generation to blackboard"""
        self.blackboard.add_generated_code_version(step_id, code, metadata)
        self.log_communication("code_generator", "code_generated", {
            "step_id": step_id,
            "code_length": len(code),
            "version": len(self.blackboard.generated_code_versions.get(step_id, [])),
            "metadata": metadata or {}
        })
    
    def log_rag_retrieval(self, step_id: str, query: str, documents: List[Dict[str, Any]]):
        """Log RAG document retrieval to blackboard"""
        self.blackboard.add_retrieved_documents(step_id, documents, query)
        self.log_communication("rag_retriever", "documents_retrieved", {
            "step_id": step_id,
            "query": query[:100] + "..." if len(query) > 100 else query,
            "documents_count": len(documents),
            "total_relevance": sum(doc.get("relevance_score", 0) for doc in documents)
        })
    
    def log_static_check(self, step_id: str, check_result: Dict[str, Any]):
        """Log static check result to blackboard"""
        self.blackboard.add_static_check_result(step_id, check_result)
        self.log_communication("static_checker", "check_completed", {
            "step_id": step_id,
            "is_valid": check_result.get("is_valid", False),
            "errors_count": len(check_result.get("errors", [])),
            "warnings_count": len(check_result.get("warnings", [])),
            "iteration": len(self.blackboard.static_check_results.get(step_id, []))
        })
    
    def log_dynamic_test(self, step_id: str, test_result: Dict[str, Any]):
        """Log dynamic test result to blackboard"""
        self.blackboard.add_dynamic_test_result(step_id, test_result)
        self.log_communication("dynamic_tester", "test_completed", {
            "step_id": step_id,
            "success": test_result.get("success", False),
            "data_availability": test_result.get("data_availability", False),
            "tool_execution": test_result.get("tool_execution", False)
        })
    
    def get_tool_creation_status(self, step_id: str) -> Dict[str, Any]:
        """Get tool creation status for a step"""
        return self.blackboard.get_tool_creation_status(step_id)
    
    def get_tool_creator_statistics(self) -> Dict[str, Any]:
        """Get ToolCreator statistics"""
        return self.blackboard.get_tool_creator_statistics()