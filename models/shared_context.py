
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from utils.base_classes import Singleton


class SharedContext(Singleton, BaseModel):
    """Singleton shared context for multi-agent collaboration"""
    
    # Core session information (immutable during execution)
    session_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Core session information: session_id, regulation_text, ifc_file_path"
    )

    # Process trace (history of executed steps and results)
    process_trace: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="""Process history with standardized structure. Expected format:
        {
            'agent': 'planner'|'executor'|'checker',
            'phase': 'initial_plan'|'plan_modification'|'step_execution'|'compliance_check',
            'status': 'success'|'failed'|'in_progress',
            'summary': str (brief description),
            'key_data': dict (phase-specific data)
        }"""
    )

    # Current task (the active step from the plan)
    current_task: Dict[str, Any] = Field(
        default_factory=dict,
        description="active step, agent, stage, step_index"
    )

    # Meta tool execution trace (detailed technical information)
    meta_tool_trace: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="""Meta tool execution results."""
    )


    def _initialize(self):
        """Initialize SharedContext singleton instance"""
        # Initialize Pydantic BaseModel with default values
        super(BaseModel, self).__init__()
        BaseModel.__init__(self)
        print("SharedContext: Singleton instance initialized")

    def initialize_session(self, session_id: str, regulation_text: str, ifc_file_path: str) -> None:
        """Initialize session information"""
        self.session_info = {
            "session_id": session_id,
            "regulation_text": regulation_text,
            "ifc_file_path": ifc_file_path,
        }
        self.current_task = {
            "active_agent": None,
            "stage": None,
            "step_index": 0,
        }
    
    def get_full_context(self) -> Dict[str, Any]:
        """Get all context information"""
        return {
            "session_info": self.session_info,
            "process_trace": self.process_trace,
            "current_task": self.current_task,
        }

    def prepare_final_trace(self) -> None:
        """Prepare final trace by keeping only the latest plan and subsequent records"""
        latest_plan_index = self._get_latest_plan_index()

        if latest_plan_index is not None:
            # Keep latest plan and everything after it
            self.process_trace = self.process_trace[latest_plan_index:]
            print(f"SharedContext: Prepared final trace with {len(self.process_trace)} records")
        else:
            print("SharedContext: No plan found in process trace, keeping all records")

    def _get_latest_plan_index(self) -> int | None:
        """Find the index of the latest plan in process_trace"""
        for i in reversed(range(len(self.process_trace))):
            entry = self.process_trace[i]
            if entry.get("phase") in ["initial_plan", "plan_modification"]:
                return i
        return None


    def get_tool_by_name(self, tool_name: str) -> Any:
        """Get the most recent successful tool creation or fix result by tool name"""
        for trace in reversed(self.meta_tool_trace):
            if (trace.success == True and
                trace.result and
                trace.meta_tool_name in ['tool_creation', 'tool_fix']):

                # Check if result has tool_name attribute and matches
                if hasattr(trace.result, 'tool_name') and trace.result.tool_name == tool_name:
                    return trace.result
        return None
     
    