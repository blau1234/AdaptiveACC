

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SharedContext(BaseModel):
    """Shared context for multi-agent collaboration"""
    
    # Core session information (immutable during execution)
    session_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Core session information: session_id, regulation_text, ifc_file_path"
    )
    
    # Current working state (mutable)
    current_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current working state: active agent, current step, temporary results"
    )
    
    # Compressed execution history
    execution_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Intelligently compressed execution history with key results"
    )
    
    def initialize_session(self, session_id: str, regulation_text: str, ifc_file_path: str) -> None:
        """Initialize session information"""
        self.session_info = {
            "session_id": session_id,
            "regulation_text": regulation_text,
            "ifc_file_path": ifc_file_path,
            "created_at": datetime.now().isoformat()
        }
        self.current_state = {
            "active_agent": None,
            "current_step": None,
            "step_index": 0,
            "temp_results": {}
        }
    
    def update_current_state(self, **kwargs) -> None:
        """Update current working state"""
        self.current_state.update(kwargs)
    
    def add_execution_result(self, result: Dict[str, Any], compress: bool = True) -> None:
        """Add execution result to summary"""
        if compress:
            compressed_result = self._compress_result(result)
            self.execution_summary.append(compressed_result)
        else:
            self.execution_summary.append(result)
    
    def _compress_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Compress execution result keeping only key information"""
        # Keep essential fields, compress detailed process
        compressed = {
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "agent": result.get("agent"),
            "step_id": result.get("step_id"),
            "status": result.get("status"),
            "key_findings": result.get("key_findings", []),
            "compliance_status": result.get("compliance_status"),
            "errors": result.get("errors", []),
            "violations": result.get("violations", [])
        }
        
        # Add specific handling for different result types
        if "tool_results" in result:
            # Compress tool execution results
            compressed["tool_summary"] = self._compress_tool_results(result["tool_results"])
        
        if "step_result" in result:
            # Keep important step result information
            step_result = result["step_result"]
            if isinstance(step_result, dict):
                compressed["elements_checked"] = step_result.get("elements_checked", [])
                compressed["measurements"] = step_result.get("measurements", {})
        
        if "plan_modifications" in result:
            # Track plan modifications
            compressed["modification_reason"] = result.get("modification_reason")
            compressed["steps_modified"] = result.get("steps_modified", 0)
        
        # Remove None values and empty lists/dicts
        return {k: v for k, v in compressed.items() 
                if v is not None and v != [] and v != {}}
    
    def _compress_tool_results(self, tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress tool execution results to essential information"""
        compressed_tools = []
        
        for tool_result in tool_results:
            compressed_tool = {
                "tool_name": tool_result.get("tool_name"),
                "success": tool_result.get("success", False),
                "key_outputs": tool_result.get("key_outputs", []),
                "error_message": tool_result.get("error_message")
            }
            
            # Remove None values
            compressed_tool = {k: v for k, v in compressed_tool.items() if v is not None}
            if compressed_tool:
                compressed_tools.append(compressed_tool)
        
        return compressed_tools
    
    def get_context_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get relevant context information for a specific agent"""
        return {
            "session_info": self.session_info,
            "current_state": self.current_state,
            "relevant_history": self._get_relevant_history(agent_name)
        }
    
    def _get_relevant_history(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get relevant execution history for agent"""
        # Return last N results, with priority for errors and key findings
        relevant = []
        
        # First add any results with errors or violations
        for result in reversed(self.execution_summary):
            if result.get("errors") or result.get("violations"):
                relevant.append(result)
                
        # Then add other recent results up to limit
        for result in reversed(self.execution_summary):
            if result not in relevant and len(relevant) < limit:
                relevant.append(result)
        
        return relevant[:limit]
    
    def cleanup_old_results(self, max_results: int = 50) -> None:
        """Clean up old execution results to keep memory manageable"""
        if len(self.execution_summary) <= max_results:
            return
            
        # Keep critical results (errors, violations) and recent results
        critical_results = []
        recent_results = []
        
        for result in self.execution_summary:
            if result.get("errors") or result.get("violations") or result.get("status") == "failed":
                critical_results.append(result)
            else:
                recent_results.append(result)
        
        # Keep all critical results and most recent normal results
        normal_limit = max_results - len(critical_results)
        if normal_limit > 0:
            kept_results = critical_results + recent_results[-normal_limit:]
        else:
            # If too many critical results, keep most recent ones
            kept_results = critical_results[-max_results:]
        
        self.execution_summary = kept_results
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the entire session"""
        if not self.execution_summary:
            return {
                "session_id": self.session_info.get("session_id"),
                "status": "no_execution",
                "total_steps": 0,
                "compliance_status": "unknown"
            }
        
        # Analyze all results for summary
        total_steps = len(self.execution_summary)
        failed_steps = sum(1 for r in self.execution_summary if r.get("status") == "failed")
        total_violations = sum(len(r.get("violations", [])) for r in self.execution_summary)
        total_errors = sum(len(r.get("errors", [])) for r in self.execution_summary)
        
        # Get final compliance status
        final_compliance = "unknown"
        for result in reversed(self.execution_summary):
            if result.get("compliance_status"):
                final_compliance = result["compliance_status"]
                break
        
        return {
            "session_id": self.session_info.get("session_id"),
            "regulation_summary": self.session_info.get("regulation_text", "")[:100] + "...",
            "total_steps": total_steps,
            "failed_steps": failed_steps,
            "total_violations": total_violations,
            "total_errors": total_errors,
            "final_compliance_status": final_compliance,
            "session_duration": self._calculate_session_duration()
        }
    
    def _calculate_session_duration(self) -> str:
        """Calculate session duration from first to last result"""
        if not self.execution_summary:
            return "0 seconds"
        
        try:
            start_time = datetime.fromisoformat(self.session_info.get("created_at", ""))
            end_time = datetime.fromisoformat(self.execution_summary[-1].get("timestamp", ""))
            duration = end_time - start_time
            return f"{duration.total_seconds():.1f} seconds"
        except:
            return "unknown"