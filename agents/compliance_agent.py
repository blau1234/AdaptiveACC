
import json
import uuid
from typing import Dict, List, Any, Optional
from utils.llm_client import LLMClient
from agent_tools.agent_tool_registry import AgentToolRegistry
from agent_tools.ifc_tool_selection import ToolSelection
from agent_tools.ifc_tool_execution import ToolExecution
from agent_tools.ifc_tool_storage import ToolStorage
from agent_tools.ifc_tool_creation_and_fix.ifc_tool_fix import ToolFix
from agent_tools.ifc_tool_creation_and_fix.ifc_tool_creation import ToolCreation
from agent_tools.subgoal_management import SubgoalManagement
from agent_tools.compliance_report import ComplianceReport
from agent_tools.web_search import WebSearch
from models.common_models import (
    AgentResult,
    AgentToolResult,
    SubgoalModel,
    SubgoalSetModel,
    ComplianceEvaluationModel
)
from models.shared_context import SharedContext
from telemetry.tracing import trace_method


class ComplianceAgent:
    """Main agent for compliance checking using ReAct framework"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()
        self.agent_tool_registry = AgentToolRegistry.get_instance()

        # Register agent tools
        self._register_required_tools()
        print(f"ComplianceAgent: Initialized with {len(self.agent_tool_registry.get_available_tools())} agent tools")

    def _register_required_tools(self):
        """Register all 8 agent tools for compliance checking workflow"""
        subgoal_management = SubgoalManagement()
        web_search = WebSearch()

        tools_to_register = [
            # Research tool (1 tool)
            web_search.search_and_summarize,
            # Core 5 agent tools for IFC tool lifecycle
            ToolSelection().select_ifc_tool,
            ToolCreation().create_ifc_tool,
            ToolExecution().execute_ifc_tool,
            ToolStorage().store_ifc_tool,
            ToolFix().fix_ifc_tool,
            # Subgoal management (2 tools)
            subgoal_management.generate_subgoals,
            subgoal_management.review_and_update_subgoals,
        ]

        for tool_func in tools_to_register:
            try:
                self.agent_tool_registry.register(tool_func)
            except Exception as e:
                print(f"Failed to register agent tool {tool_func.__name__}: {e}")


    # === Main Interface ===

    @trace_method("compliance_check")
    def execute_compliance_check(self, regulation_text: str, ifc_file_path: str, max_iterations: int = 10) -> AgentResult:
        """Execute complete compliance checking using ReAct framework

        Args:
            regulation_text: Building regulation to check
            ifc_file_path: Path to IFC file
            max_iterations: Maximum ReAct iterations 

        Returns:
            AgentResult with compliance report
        """

        # 1. Initialize session (also resets subgoals and agent_history)
        session_id = str(uuid.uuid4())[:8]
        print(f"\nComplianceAgent: Session {session_id} initialized")
        self.shared_context.initialize_session(session_id, regulation_text, ifc_file_path)

        # 2. Run ReAct loop (state managed in SharedContext)
        print(f"\nStarting ReAct loop (max {max_iterations} iterations)...")
        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"ReAct Iteration {iteration + 1}/{max_iterations}")
            print(f"{'='*60}")

            result = self._run_react_iteration(iteration)
            if result:  # Task completed or failed
                return result

        # 3. Handle timeout
        print(f"\n[WARNING] Exceeded maximum iterations ({max_iterations})")
        return AgentResult(
            status="timeout",
            iterations_used=max_iterations,
            agent_history=self.shared_context.agent_history,
            error=f"Exceeded maximum iterations ({max_iterations})"
        )


    # === Core ReAct Logic ===

    def _run_react_iteration(self, iteration: int) -> Optional[AgentResult]:
        """Run a single ReAct iteration"""

        # Get LLM's thought and function calls
        llm_response = self._get_react_response()
        thought_content = llm_response.get("content", "").strip()
        tool_calls = llm_response.get("tool_calls", [])

        # Determine if task is complete (no function calls = data collection finished)
        if not tool_calls or len(tool_calls) == 0:
            print("\n[OK] Agent finished data collection - automatically generating compliance report")

            # Record final thought
            iteration_entry = {
                "iteration": iteration + 1,
                "thought": thought_content,
                "action": "auto_generate_report",
                "action_input": None
            }
            self.shared_context.agent_history.append(iteration_entry)

            # Automatically trigger compliance report generation
            compliance_report = ComplianceReport()
            report_result = compliance_report.generate_report()

            if report_result.success:
                print(f"[OK] Compliance report generated - {report_result.result.overall_status}")
                return AgentResult(
                    status="success",
                    iterations_used=iteration + 1,
                    agent_history=self.shared_context.agent_history,
                    compliance_result=report_result.result
                )
            else:
                print(f"[ERROR] Compliance report generation failed: {report_result.error}")
                return AgentResult(
                    status="failed",
                    iterations_used=iteration + 1,
                    agent_history=self.shared_context.agent_history,
                    error=f"Compliance report generation failed: {report_result.error}"
                )

        # Extract first tool call (execute one at a time)
        tool_call = tool_calls[0]
        action_name = tool_call.function.name

        # Parse function arguments
        try:
            action_input = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse tool arguments: {e}")
            action_input = {}

        # Execute action
        action_result = self._execute_action(
            action_name,
            action_input,
        )

        # Get current active subgoal ID from SharedContext
        active_subgoal_id = None
        if self.shared_context.subgoals:
            for sg_dict in self.shared_context.subgoals:
                if sg_dict.get('status') == "in_progress":
                    active_subgoal_id = sg_dict.get('id')
                    break

        # Record complete iteration entry to history
        iteration_entry = {
            "iteration": iteration + 1,
            "active_subgoal_id": active_subgoal_id,
            "thought": thought_content,
            "action": action_name,
            "action_input": action_input,
            "action_result": action_result.model_dump()
        }
        self.shared_context.agent_history.append(iteration_entry)

        print(iteration_entry)

        # Special handling for subgoal management tools
        if action_result.success and action_name in ["generate_subgoals", "review_and_update_subgoals"]:
            # Update SharedContext with new subgoals
            updated_subgoals = action_result.result
            if isinstance(updated_subgoals, SubgoalSetModel):
                # Store as list of dicts for easy access by agent tools
                self.shared_context.subgoals = [sg.model_dump() for sg in updated_subgoals.subgoals]

                print(f"[SUBGOALS UPDATED] {len(updated_subgoals.subgoals)} subgoals")
                for sg in updated_subgoals.subgoals:
                    print(f"  {sg.id}. [{sg.status}] {sg.description}")

        return None  # Continue iterations


    def _get_react_response(self) -> Dict:
        """Get LLM's ReAct response for current iteration"""

        # Get regulation context (always needed)
        regulation_text = self.shared_context.session_info.get("regulation_text", "")
        ifc_file_path = self.shared_context.session_info.get("ifc_file_path", "")

        # Get regulation interpretation if available (generated during generate_subgoals)
        regulation_interpretation = self.shared_context.session_info.get("regulation_interpretation")

        # Format interpretation if available
        interpretation_section = ""
        if regulation_interpretation:
            term_clarifications_text = "\n".join([
                f"  - {tc['term']}: {tc['meaning']}" + (f" (IFC: {tc['ifc_mapping']})" if tc.get('ifc_mapping') else "")
                for tc in regulation_interpretation.get('term_clarifications', [])
            ])
            misunderstandings_text = "\n".join([
                f"  - {m}" for m in regulation_interpretation.get('common_misunderstandings', [])
            ])

            interpretation_section = f"""
        ## Regulation Interpretation:
        Plain Language:
        {regulation_interpretation.get('plain_language', '')}

        Key Terms:
        {term_clarifications_text if term_clarifications_text else "  (none)"}

        Common Misunderstandings to Avoid:
        {misunderstandings_text if misunderstandings_text else "  (none)"}
        """

        # Get current subgoals for display
        current_subgoals = self.shared_context.subgoals

        # Format subgoals section if available
        subgoals_section = ""
        if current_subgoals:
            subgoal_lines = []
            for sg in current_subgoals:
                subgoal_lines.append(f"  {sg['id']}. [{sg['status']}] {sg['description']}")

            subgoals_section = f"""
        ## Current Subgoals:
        {chr(10).join(subgoal_lines)}
        """

        # Using complete unfiltered history
        complete_history = self.shared_context.format_complete_history()

        system_prompt = f"""
        You are an intelligent building compliance checker using the ReAct (Reasoning and Acting) framework.
        Your task is to verify that a building design (IFC file) complies with given building regulations.

        ## ReAct Framework Process
        For each iteration, you output:
        1. **Thought**: Analyze the current situation based on:
            - The regulation requirements
            - The subgoals (dynamic guidance that you can update)
            - Last action result and recent history
            - Current progress and what information is still needed

        2. **Action**: Choose which agent tool to use (see Available Agent Tools below)
        3. **Action Input**: Specify tool parameters

        The system then executes your action and provides the result in the next iteration.

        ## Three-Phase Workflow Strategy

        ### Phase 1: Planning
        **First Step**: Use **generate_subgoals** to create an initial high-level plan. 
        If you need external knowledge about the regulation, use **search_and_summarize** before generating subgoals.

        ### Phase 2: Execution
        **Goal**: Systematically collect all data needed for compliance evaluation.

        **The Core Workflow for New Tools: Create → Execute → Store (if successful) → Review**

        When you create a new tool with **`create_ifc_tool`**:
        1. **Execute it first** with `execute_ifc_tool` (in sandbox mode) to validate it works correctly
        2. **If execution succeeds**, your immediate next action **MUST** be to call **`store_ifc_tool`** to save it to the registry for future use
        3. **Then** call **`review_and_update_subgoals`** to assess the collected data and update your plan

        **If execution fails**, use `fix_ifc_tool` to repair the tool, then repeat step 1.

        **Why store tools?** Successfully executed tools become reusable assets. Storing them enriches the tool library for future checks and other users.

        **Error Handling & Tool Adjustment Protocol**
        - Your primary role is to diagnose the root cause of any problem before acting. Follow these scenarios strictly.

        **- Scenario 1: Newly Created Tool Fails (Code Error)**
        - **Symptom**: The tool you just created with `create_ifc_tool` crashes during execution (e.g., `SyntaxError`, `TypeError`).
        - **Your Thought**: "My new code is buggy and needs debugging."
        - **Action**: Use **fix_ifc_tool**. This is the only valid use case for this tool.

        **- Scenario 2: Existing Library Tool Fails (Code Error)**
        - **Symptom**: A tool retrieved using `select_ifc_tool` crashes during execution.
        - **Your Thought**: "The library tool is broken. I cannot modify it directly. I need to create a working replacement."
        - **Action**: **DO NOT use `fix_ifc_tool`**. Instead, use **create_ifc_tool** to build a new, correct tool from scratch.

        **- Scenario 3: Tool Works But is Functionally Wrong (Design Flaw)**
        - **Symptom**: A tool (new or existing) runs successfully, but its result is not useful for your current subgoal.
        - **Your Thought**: "This tool works as designed, but the design itself is wrong for my goal. I need a different kind of tool."
        - **Action**: **DO NOT use `fix_ifc_tool`**. Use **create_ifc_tool** with a new, more precise description to build a better tool.

        **- Scenario 4: Direct Information Retrieval Fails (Investigation Protocol Required)**
        - **Symptom**: A tool runs successfully but returns a result indicating it could not find the required information through standard means.
        - **Your Thought**: "Direct retrieval failed. This does not mean the information is absent. Possible reasons are numerous: a non-standard storage location, different property naming conventions or language, or data that requires special parsing. I must initiate the investigation protocol instead of giving up immediately."
        - **Action (The Investigation Protocol)**:
            1. **Broaden the Search**: Obtain a more generic 'explorer' tool by following the standard IFC tool workflow (`select_ifc_tool` first, then `create_ifc_tool` if necessary). e.g. retrieve all available data associated with the target element or type.
            2. **Analyze Raw Data**: Carefully examine the complete raw data returned by the explorer tool. Look for clues like similar but different names, data embedded in text strings, or information in unexpected locations.
            3. **Formulate & Test Hypothesis**: If you find a promising new location or name, obtain another, more precise tool to specifically target and validate your hypothesis.
            4. **Conclude**: Only after executing this investigation protocol and attempting reasonable exploratory paths should you conclude that the data is missing. Mark the subgoal as "unverifiable due to missing data" and document your investigation steps.

        ### Phase 3: Completion
        Stop calling tools when you have sufficient data to answer all regulation requirements. The system will automatically generate the final report.

        ## Available Agent Tools
        (Detailed schemas provided separately via function calling)

        ### Research Tool (Optional)
        - **search_and_summarize**: For external knowledge research.

        ### Planning & Management Tools
        - **generate_subgoals**: Call ONCE at the beginning for the initial plan. This automatically includes regulation interpretation.
        - **review_and_update_subgoals**: Call after milestones or discoveries to update the plan.

        ### IFC Tool Workflow (Data Collection)
        - **select_ifc_tool**: Find existing IFC tools via semantic search. **Always use this before creating a new tool.**
        - **create_ifc_tool (The Engineer)**: Generate new IFC tools when no suitable one exists or when an existing tool has a design flaw.
          **CRITICAL - Task Description Guidelines**:
          - Keep it SIMPLE and FOCUSED on ONE approach
          - ✓ Good: "Extract riser height from IfcStair property sets"
          - ✗ Bad: "Extract riser height from property sets, geometric data, or any other relevant sources..."
          - If first approach fails, create a DIFFERENT tool with a different approach
          - Priority order: property sets > geometry > relationships
        - **execute_ifc_tool**: Execute IFC tools to gather data from the IFC file.
        - **fix_ifc_tool (The Mechanic)**:
            - CRITICAL RULE: This tool can ONLY be used to fix a tool that was just created by `create_ifc_tool` in the current session.
            - Its purpose is for immediate, in-memory debugging of new code.
            - Never use it on a tool retrieved from the library via `select_ifc_tool`.
        - **store_ifc_tool**: Save a validated, new tool to the registry for future use.

        ## Core Principles & Autonomy
        **Reasoning**: Always explain your thinking in the Thought step.
        **Efficiency**: Avoid redundant actions by checking your history.
        **Guardrails, Not a Cage**: 
        - The scenarios described above are best-practice guidelines for common situations. You should follow them strictly in most cases. However, if you encounter a truly unique situation that does not fit any scenario, you are empowered to use your own reasoning. 
        - In such a case, you must explicitly state in your **Thought** why the existing scenarios are insufficient and propose a logical alternative action. Your ultimate goal is to complete the compliance check; these rules are designed to help you, not to hinder you.
        """

        # Build final prompt based on phase
        prompt = f"""
        ## Regulation to Check:
        "{regulation_text}"
        {interpretation_section}

        ## IFC File Being Analyzed:
        {ifc_file_path}

        ## Subgoals:
        {subgoals_section}

        ## Agent history:
        {complete_history}

        Based on the current situation, what should be your next action?
        Think step by step about what information is still needed and how to obtain it.

        Remember:
        - You can use any available agent tools
        - Keep your thoughts concise and focused.
        - When data collection is complete, simply stop calling tools
        """

        try:
            response = self.llm_client.generate_response_with_tools(
                prompt=prompt,
                system_prompt=system_prompt,
                tools=self.agent_tool_registry.get_tools_json()
            )
            return response
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            raise RuntimeError(f"ReAct LLM call failed: {e}") from e


    def _execute_action(self, action_name: str, action_input: Dict[str, Any]) -> AgentToolResult:
        """Execute the selected agent tool"""

        try:
            # Get the callable tool function
            tool_func = self.agent_tool_registry.get_callable(action_name)

            if tool_func is None:
                return AgentToolResult(
                    success=False,
                    agent_tool_name=action_name,
                    error=f"Agent tool '{action_name}' not found in registry"
                )

            # Execute tool with provided parameters
            result = tool_func(**action_input)

            # All agent tools should return AgentToolResult
            if not isinstance(result, AgentToolResult):
                return AgentToolResult(
                    success=False,
                    agent_tool_name=action_name,
                    error=f"Agent tool '{action_name}' returned unexpected type: {type(result)}"
                )

            return result

        except Exception as e:
            return AgentToolResult(
                success=False,
                agent_tool_name=action_name,
                error=f"Agent tool execution failed: {str(e)}"
            )


    def _determine_phase(self) -> str:
        """Determine current phase: 'planning' or 'execution'"""
        if not self.shared_context.subgoals:
            return "planning"

        # Check if there's an active subgoal
        has_active_subgoal = any(
            sg.get('status') == 'in_progress'
            for sg in self.shared_context.subgoals
        )

        if has_active_subgoal:
            return "execution"

        # All subgoals are pending or completed
        all_completed = all(
            sg.get('status') == 'completed'
            for sg in self.shared_context.subgoals
        )

        if all_completed:
            return "execution"  # Will trigger report generation soon
        else:
            return "execution"  # Pending subgoals to work on
