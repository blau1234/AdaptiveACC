
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from utils.base_classes import Singleton
from models.common_models import AgentToolResult, IFCToolResult, ComplianceEvaluationModel

class SharedContext(Singleton, BaseModel):
    """Singleton shared context for multi-agent collaboration (ReAct architecture)"""

    # Core session information (immutable during execution)
    session_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Core session information: session_id, regulation_text, ifc_file_path, regulation_interpretation, etc."
    )

    subgoals: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Current subgoals being worked on"
    )

    # ReAct iteration history (includes thoughts, actions, results, and active_subgoal_id)
    agent_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Complete ReAct iteration history from ComplianceAgent"
    )

    # Web search summaries (supports multiple searches without overwriting)
    search_summaries: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of web search summaries with query, result, and timestamp"
    )

    # Compliance evaluation result (final assessment)
    compliance_result: Optional[ComplianceEvaluationModel] = Field(
        None,
        description="Final compliance evaluation result from Checker"
    )


    def _initialize(self):
        """Initialize SharedContext singleton instance"""
        # Initialize Pydantic BaseModel with default values
        super(BaseModel, self).__init__()
        BaseModel.__init__(self)
        print("SharedContext: Singleton instance initialized")

    def initialize_session(self, session_id: str, regulation_text: str, ifc_file_path: str) -> None:
        """Initialize session information and reset state for new session"""
        self.session_info = {
            "session_id": session_id,
            "regulation_text": regulation_text,
            "ifc_file_path": ifc_file_path,
        }
        # Reset session state
        self.subgoals = []
        self.agent_history = []
        self.search_summaries = []
        self.compliance_result = None

    # === Web search summary methods ===

    def add_search_summary(self, query: str, summary: str) -> None:
        """Add a web search summary to the list.

        Args:
            query: The search query used
            summary: The summarized search result (max ~500 chars)
        """
        self.search_summaries.append({
            "query": query,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })
        print(f"SharedContext: Added search summary for query '{query}' (total: {len(self.search_summaries)})")

    def get_all_summaries(self) -> str:
        """Get all search summaries as formatted text for LLM consumption.

        Returns:
            Formatted string with all search summaries, or empty string if none exist
        """
        if not self.search_summaries:
            return ""

        formatted_summaries = []
        for i, entry in enumerate(self.search_summaries, 1):
            formatted_summaries.append(
                f"Search {i}: {entry['query']}\n"
                f"Result: {entry['summary']}"
            )

        return "\n\n".join(formatted_summaries)

    # === agent_history filtering and query methods ===

    def get_successful_ifc_tool_executions(self) -> List[Dict[str, Any]]:
        """Get all successful IFC tool execution entries from agent_history."""
        return [
            entry for entry in self.agent_history
            if (entry.get('action') == 'execute_ifc_tool' and
                entry.get('action_result', {}).get('success'))
        ]

    def get_entries_by_subgoal(self, subgoal_id: int) -> List[Dict[str, Any]]:
        """Get all agent_history entries related to a specific subgoal ID."""
        return [
            entry for entry in self.agent_history
            if entry.get('active_subgoal_id') == subgoal_id
        ]

    def get_tool_by_name(self, tool_name: str) -> Any:
        """Get the most recent successful tool creation or fix result by tool name.

        Args:
            tool_name: Name of the IFC tool to find

        Returns:
            ToolCreatorOutput object if found, None otherwise
        """
        # Traverse agent_history in reverse (most recent first)
        for entry in reversed(self.agent_history):
            action = entry.get('action')
            action_result = entry.get('action_result', {})

            # Check if this is a successful create_ifc_tool or fix_ifc_tool action
            if (action in ['create_ifc_tool', 'fix_ifc_tool'] and
                action_result.get('success')):

                result = action_result.get('result')
                if result and result.get('ifc_tool_name') == tool_name:
                    return result

        return None

    def get_error_info_from_context(self, tool_name: str = "") -> Optional[IFCToolResult]:
        """Get error information from agent_history for failed IFC tool executions.

        Args:
            tool_name: Name of the IFC tool to find error for (optional)

        Returns:
            IFCToolResult with error information if found, None otherwise
        """
        try:
            # Traverse agent_history in reverse (most recent first)
            for entry in reversed(self.agent_history):
                action = entry.get('action')
                action_result = entry.get('action_result', {})

                # Check if this is a failed execute_ifc_tool action
                if (action == 'execute_ifc_tool' and
                    not action_result.get('success')):

                    result = action_result.get('result', {})

                    # Match tool name if specified
                    if not tool_name or result.get('ifc_tool_name') == tool_name:
                        return result

            # No matching failure found
            msg = f"No failed execution found for tool '{tool_name}'" if tool_name \
                else "No failed tool executions found"
            print(msg)
            return None

        except Exception as e:
            print(f"Error getting error info from context: {e}")
            return None

    # === Formatting methods for LLM consumption ===

    def format_successful_executions_summary(self, max_per_subgoal: int = 2) -> str:
        """Format successful IFC tool executions grouped by subgoal.

        Args:
            max_per_subgoal: Maximum number of executions to show per subgoal

        Returns:
            Formatted string suitable for LLM consumption
        """
        successful_executions = self.get_successful_ifc_tool_executions()

        if not successful_executions:
            return "## Data Collected: None yet"

        # Group by subgoal
        evidence_by_subgoal = {}
        for entry in successful_executions:
            subgoal_id = entry.get('active_subgoal_id', 'unassigned')
            if subgoal_id not in evidence_by_subgoal:
                evidence_by_subgoal[subgoal_id] = []
            evidence_by_subgoal[subgoal_id].append(entry)

        # Format output
        lines = ["## Data Collected by Subgoal"]
        for subgoal_id, entries in evidence_by_subgoal.items():
            lines.append(f"\nSubgoal {subgoal_id}: {len(entries)} successful executions")
            for entry in entries[:max_per_subgoal]:
                result = entry['action_result'].get('result', {})
                tool_name = result.get('ifc_tool_name', 'unknown')
                iter_num = entry.get('iteration')
                lines.append(f"  - Iter {iter_num}: {tool_name}")

            if len(entries) > max_per_subgoal:
                lines.append(f"  ... and {len(entries) - max_per_subgoal} more")

        return "\n".join(lines)

    def format_subgoal_history(self, subgoal_id: int) -> str:
        """Format all history entries for a specific subgoal.

        Args:
            subgoal_id: The subgoal ID to get history for

        Returns:
            Formatted string with all actions attempted for this subgoal
        """
        entries = self.get_entries_by_subgoal(subgoal_id)

        if not entries:
            return f"## Subgoal {subgoal_id}: No actions yet"

        lines = [f"## Subgoal {subgoal_id} - Detailed History ({len(entries)} actions)"]

        for entry in entries:
            action = entry.get('action')
            iter_num = entry.get('iteration')
            result = entry.get('action_result', {})

            status_icon = "✓" if result.get('success') else "✗"

            # Basic info
            line = f"  {status_icon} Iter {iter_num}: {action}"

            # Add brief result info
            if result.get('success'):
                if action == 'execute_ifc_tool':
                    tool_name = result.get('result', {}).get('ifc_tool_name', '')
                    line += f" ({tool_name})"
            else:
                error = result.get('error', '')[:50]
                line += f" - Error: {error}..."

            lines.append(line)

        return "\n".join(lines)

    def format_planning_history(self) -> str:
        """Format planning-related actions from agent_history.

        Returns:
            Formatted string with all planning actions
        """
        planning_actions = [
            'search_and_summarize',
            'generate_interpretation',
            'generate_subgoals',
            'review_and_update_subgoals'
        ]

        planning_entries = [
            entry for entry in self.agent_history
            if entry.get('action') in planning_actions
        ]

        if not planning_entries:
            return "## Planning History: No planning actions yet"

        lines = ["## Planning History"]
        for entry in planning_entries:
            action = entry['action']
            iter_num = entry['iteration']
            result = entry['action_result']

            status_icon = "✓" if result.get('success') else "✗"

            if result.get('success'):
                lines.append(f"  {status_icon} Iter {iter_num}: {action}")
            else:
                error = result.get('error', '')[:50]
                lines.append(f"  {status_icon} Iter {iter_num}: {action} - Error: {error}...")

        return "\n".join(lines)

    def format_last_action(self) -> str:
        """Format the last action result from agent_history.

        Returns:
            Formatted string with last action name and result, or empty string if no history
        """
        if not self.agent_history:
            return ""

        # If last action is auto_generate_report, get the one before it
        if len(self.agent_history) >= 2 and self.agent_history[-1].get('action') == 'auto_generate_report':
            last_iteration = self.agent_history[-2]
        elif len(self.agent_history) >= 1:
            last_iteration = self.agent_history[-1]
        else:
            return ""

        last_action_result = last_iteration.get('action_result', {})

        if last_action_result.get('success'):
            result_info = f"succeeded with result: {last_action_result.get('result')}"
        else:
            result_info = f"failed with error: {last_action_result.get('error')}"

        last_action_text = f"""## Last Action Result
        Action: {last_iteration.get('action')}
        Result: {result_info}"""

        return last_action_text

    def format_complete_history(self) -> str:
        """Format complete agent_history without filtering or truncation.

        Returns:
            Formatted string with all iteration history including full thoughts, actions, and results
        """
        if not self.agent_history:
            return "## Complete History: No actions yet"

        lines = ["## Complete Agent History"]

        for entry in self.agent_history:
            iter_num = entry.get('iteration')
            thought = entry.get('thought', '')
            action = entry.get('action', '')
            action_input = entry.get('action_input')
            action_result = entry.get('action_result', {})
            active_subgoal_id = entry.get('active_subgoal_id')

            status_icon = "✓" if action_result.get('success') else "✗"

            # Build iteration header
            subgoal_info = f" [Subgoal {active_subgoal_id}]" if active_subgoal_id is not None else ""
            lines.append(f"\n### Iteration {iter_num}{subgoal_info}")

            # Add full thought if present
            if thought:
                lines.append(f"Thought: {thought}")

            # Add action and status
            lines.append(f"{status_icon} Action: {action}")

            # Add full action input
            if action_input:
                lines.append(f"  Input: {str(action_input)}")

            # Add full result
            if action_result.get('success'):
                result = action_result.get('result')
                if isinstance(result, dict):
                    if 'ifc_tool_name' in result:
                        # This is an IFCToolResult - show both tool name and actual result data
                        tool_name = result.get('ifc_tool_name')
                        actual_result = result.get('result')  # The actual data returned by the tool
                        lines.append(f"  Result: Tool '{tool_name}' executed successfully")
                        if actual_result is not None:
                            # Truncate very long results to keep context manageable
                            result_str = str(actual_result)
                            lines.append(f"  Data: {result_str}")
                    elif 'subgoals' in result:
                        # Subgoals result - reference the dedicated Subgoals section
                        subgoals_list = result.get('subgoals', [])
                        lines.append(f"  Result: Updated {len(subgoals_list)} subgoals (see Subgoals section above for current status)")
                    else:
                        lines.append(f"  Result: {str(result)}")
                else:
                    lines.append(f"  Result: {str(result)}")
            else:
                error = action_result.get('error', '')
                lines.append(f"  Error: {error}")

        return "\n".join(lines)
