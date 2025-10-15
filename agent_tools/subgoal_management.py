
import json
from typing import Dict, List, Any
from utils.llm_client import LLMClient
from models.common_models import SubgoalSetModel, AgentToolResult
from models.shared_context import SharedContext
from telemetry.tracing import trace_method
from agent_tools.regulation_interpretation import RegulationInterpretationTool

class SubgoalManagement:

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()

    @trace_method("subgoal_generation")
    def generate_subgoals(self) -> AgentToolResult:
        """Generate initial subgoals for compliance checking workflow.

        This method should ONLY be called once at the beginning of the workflow
        to create the initial set of subgoals. For all subsequent modifications
        (including major re-planning), use review_and_update_subgoals instead.

        Automatically generates regulation interpretation before creating subgoals.

        Returns:
            AgentToolResult with SubgoalSetModel in result field
        """
        try:
            regulation_text = self.shared_context.session_info.get("regulation_text")

            # generate interpretation
            print("\n[SubgoalManagement] Generating regulation interpretation...")
            
            interpretation_tool = RegulationInterpretationTool()
            interp_result = interpretation_tool.generate_interpretation()

            if interp_result.success:
                interpretation = interp_result.result
                print(f"[SubgoalManagement] Interpretation generated with {len(interpretation.term_clarifications)} term clarifications")

                # Store interpretation in SharedContext for persistent access
                self.shared_context.session_info['regulation_interpretation'] = interpretation.model_dump()
            else:
                raise RuntimeError(f"Interpretation generation failed: {interp_result.error}")

            # Build system prompt
            system_prompt = """
            You are a building compliance planning expert. Your task is to generate high-level subgoals for a compliance checking process.

            ## Your Task
            Generate subgoals that guide the compliance checking process. Each subgoal must describe **WHAT** needs to be achieved, not **HOW** it should be achieved.

            ## Subgoal Generation Guidelines

            ### Core Principle: One Subgoal, One Atomic Action
            This is the most important rule. Each subgoal must correspond to **a single, indivisible action** from one of the four logical flow phases (1. Identification & Scoping, 2. Data Collection, 3. Analysis & Calculation, 4. Verification & Comparison). A subgoal must never combine actions from different phases.

            **CRITICAL EXAMPLE:** To check if door widths comply with a regulation:

            **- BAD (Combines all phases into one):**
            - "Verify all fire exit doors have a clear width of at least 1000mm."

            **- GOOD (Broken down into atomic, sequential subgoals):**
            1.  **(Identification & Scoping):** "Identify and list all doors designated as fire exits."
            2.  **(Data Collection):** "Obtain the necessary geometric data (e.g., wall thickness, door frame geometry, and leaf dimensions) for all identified fire exit doors."
            3.  **(Analysis & Calculation):** "Calculate the clear, unobstructed width for each fire exit door using its geometric data."
            4.  **(Verification & Comparison):** "Verify that the calculated clear width of each fire exit door is greater than or equal to 1000mm."


            ### Logical Flow (Optimized Sequence with Patterns)
            The data collection and verification process must follow this logical progression. Each step includes the primary **Goal Patterns** that belong to it:

            1.  **Identification & Scoping:** Determine the relevant elements, their context, and the scope of the check.
                * **Goal Patterns:**
                    * "Determine all [elements] relevant to the [specific requirement]";
                    * "Scope the check to [specific area or type]".

            2.  **Data Collection:** Gather necessary **stored properties** (i.e., data directly readable from the model).
                * **Goal Patterns:**
                    * "Obtain [stored property] data for all identified [elements]";
                    * "Collect initial [relationship] information for [elements]".

            3.  **Analysis & Calculation:** Execute complex operations to **derive new data** (e.g., spatial analysis, geometric calculations, relationship checks).
                * **Goal Patterns:**
                    * "**Calculate** the [derived metric/clearance] for [elements]";
                    * "**Analyze** the [spatial/topological pattern] between [elements]".

            4.  **Verification & Comparison:** Check the collected or derived data against the compliance requirements.
                * **Goal Patterns:**
                    * "Verify that all [elements] meet the [numerical/categorical requirement]";
                    * "Check that [relationship] exists and is compliant between [elements]".


            ### Other Key Guidelines
            -   **Focus on Goals, Not Methods**:
                -   **Good**: "Obtain width measurements for all doors"
                -   **Bad**: "Use the get_door_properties tool to extract the Width attribute"

            ### Subgoal Requirements
            -   **Format:** Each subgoal must be a JSON object with `description` and `rationale` fields.
            -   **Granularity:** Subgoals must be **atomic**. Decompose complex compliance requirements into a sequence of smaller steps, where each step aligns with a single action type (e.g., a single act of collecting data, a single calculation, or a single verification). Avoid creating subgoals that require multiple distinct logical operations.
            -   **Intent Focus:** Focus on the compliance intent. For instance, if a regulation is about clearance, use "Determine clear width" (a calculation goal) rather than the less precise "Obtain width measurement."
            """

            # Build interpretation section (always available now)
            term_clarifications_text = "\n".join([
                f"  - {tc.term}: {tc.meaning}" + (f" (IFC: {tc.ifc_mapping})" if tc.ifc_mapping else "")
                for tc in interpretation.term_clarifications
            ])
            misunderstandings_text = "\n".join([f"  - {m}" for m in interpretation.common_misunderstandings])

            interpretation_section = f"""
            ## Regulation Interpretation:
            Plain Language:
            {interpretation.plain_language}

            Key Terms:
            {term_clarifications_text if term_clarifications_text else "  (none)"}

            Common Misunderstandings to Avoid:
            {misunderstandings_text if misunderstandings_text else "  (none)"}
            """

            prompt = f"""
            ## Regulation:
            "{regulation_text}"
            {interpretation_section}

            Based on the regulation and all available information, generate initial subgoals for compliance checking.
            Remember: Focus on WHAT to achieve, not HOW."""

            # Call LLM to generate subgoals
            subgoals = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=SubgoalSetModel
            )

            print(f"SubgoalManagement: Generated {len(subgoals.subgoals)} initial subgoals")

            return AgentToolResult(
                success=True,
                agent_tool_name="generate_subgoals",
                result=subgoals
            )

        except Exception as e:
            print(f"SubgoalManagement: Failed to generate subgoals: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="generate_subgoals",
                error=f"Subgoal generation failed: {str(e)}"
            )


    @trace_method("subgoal_review")
    def review_and_update_subgoals(self, current_progress: str, suggested_completed_ids: List[int],) -> AgentToolResult:
        """Review and update all subgoals (handles ALL modifications after initial generation).

        This is the PRIMARY method for all subgoal modifications after initial generation, including:
        - Marking completed subgoals
        - Adjusting existing subgoal descriptions
        - Adding new subgoals when discovering new requirements
        - Removing or consolidating obsolete subgoals
        - Complete re-planning if the entire approach is wrong

        Verifies completion status and adjusts remaining subgoals based on Agent's progress report
        and tool execution history from SharedContext.

        Args:
            current_progress: Agent's description of current progress and any new discoveries
            suggested_completed_ids: Subgoal IDs that Agent believes are completed

        Returns:
            AgentToolResult with SubgoalSetModel in result field
        """
        try:
            regulation_text = self.shared_context.session_info.get("regulation_text", "")
            current_subgoals = self.shared_context.subgoals

            # Use SharedContext formatting method for evidence summary
            evidence_text = self.shared_context.format_successful_executions_summary(max_per_subgoal=3)

            # Build system prompt
            system_prompt = """You are a task management expert for building compliance checking.

            ## Your Task

            Review the Agent's progress and update all subgoals accordingly. You can perform ANY type of modification:
            1. **Verify completions**: Check if Agent's claimed completions are justified by tool execution history
            2. **Adjust existing subgoals**: Update descriptions or rationale if needed based on new discoveries
            3. **Add new subgoals**: If new requirements are discovered during execution
            4. **Remove/consolidate**: If some subgoals become irrelevant or can be merged
            5. **Complete re-planning**: If the Agent reports that the entire approach is wrong, you can replace all subgoals with a new strategy

            ## Verification Principles

            - A subgoal is "completed" if sufficient data has been gathered to fulfill its objective
            - Don't mark as completed if only partial data exists
            - Be conservative: when in doubt, keep it "pending"

            ## Update Principles

            - **Flexibility**: Support both incremental updates AND complete re-planning based on Agent's report
            - **Goal orientation**: Maintain high-level WHAT not HOW focus
            - **Independence**: Keep subgoals independent where possible
            - **Adaptability**: If Agent discovers the current approach is fundamentally flawed, create a completely new set of subgoals
            - **Evidence-based**: Ground decisions in actual tool execution history from SharedContext

            ## Output Format

            Return a complete SubgoalSetModel with all subgoals (updated/new/replaced).
            Each subgoal should have: id, description, status, rationale."""

            # Build user prompt
            prompt = f"""
            ## Regulation Context
            "{regulation_text}"

            ## Current Subgoals
            {json.dumps(current_subgoals, indent=2)}

            {evidence_text}

            ## Agent Progress Report
            {current_progress}

            ## Agent's Suggested Completed Subgoal IDs
            {suggested_completed_ids}

            Based on the evidence collected for each subgoal, review and update all subgoals.
            - Mark subgoals as "completed" only if sufficient IFC tool results have been collected
            - Update status of other subgoals as needed (e.g., mark next as "in_progress")
            - Adjust descriptions if needed based on new discoveries
            - Add new subgoals if required
            - Return the complete updated SubgoalSetModel."""

            # 5. Call LLM
            updated_subgoals = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=SubgoalSetModel
            )

            print(f"SubgoalManagement: Reviewed and updated subgoals - {len(updated_subgoals.subgoals)} total")
            completed_count = sum(1 for sg in updated_subgoals.subgoals if sg.status == "completed")
            print(f"SubgoalManagement: {completed_count} completed, {len(updated_subgoals.subgoals) - completed_count} pending")

            return AgentToolResult(
                success=True,
                agent_tool_name="review_and_update_subgoals",
                result=updated_subgoals
            )

        except Exception as e:
            print(f"SubgoalManagement: Failed to review subgoals: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="review_and_update_subgoals",
                error=f"Subgoal review failed: {str(e)}"
            )
