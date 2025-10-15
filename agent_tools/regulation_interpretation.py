
from utils.llm_client import LLMClient
from models.common_models import RegulationInterpretation, AgentToolResult
from models.shared_context import SharedContext
from telemetry.tracing import trace_method


class RegulationInterpretationTool:
    """Agent tool for generating regulation interpretations"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()

    @trace_method("regulation_interpretation")
    def generate_interpretation(self) -> AgentToolResult:
        """
        Generate human-readable interpretation of a building regulation.

        This tool disambiguates technical terms, maps them to IFC entities/properties,
        and clarifies common misunderstandings. Automatically incorporates context from
        web searches stored in SharedContext.

        Returns:
            AgentToolResult with RegulationInterpretation in result field
        """
        try:
            # Get regulation text from SharedContext
            regulation_text = self.shared_context.session_info.get("regulation_text", "")

            # Build system prompt
            system_prompt = """
            You are a building code interpretation expert with deep knowledge of both building regulations and IFC (Industry Foundation Classes) schema.

            Your task is to interpret building code regulations and clarify their semantics, especially focusing on:
            1. Technical term disambiguation
            2. IFC entity/property mappings
            3. Implicit requirements and constraints
            4. Common misinterpretations to avoid

            ## IFC Common Pitfalls:

            - **IfcOpeningElement** is the VOID/HOLE in a wall, NOT the door itself
            - **IfcDoor** is the physical door element that fills an opening
            - **"Exit" identification**: Check IsExternal=True, UsageType="Exit", or FireExit property
            - **"Accessible" elements**: Check UsageType="Accessible" or accessibility-related property sets

            ## Building Code Semantic Patterns:

            **Threshold Requirements**:
            - Language: "minimum X is Y", "maximum X is Y", "X shall be at least Y", "X must be no less than Y"
            - Intent: VERIFY that ALL elements meet the threshold (not counting or statistics)
            - Example: "minimum height is 2032mm" → check EACH element height >= 2032mm
            - NOT: count how many elements meet the threshold

            **Counting Requirements**:
            - Language: "at least N", "no more than M", "shall have N", "minimum of N"
            - Intent: COUNT elements and verify the quantity
            - Example: "at least 2 exits" → count exits, verify count >= 2

            **Consistency Requirements**:
            - Language: "same", "identical", "uniform", "consistent", "equal"
            - Intent: VERIFY all values in a group are equal
            - Example: "same elevation" → verify all elevations in a group are identical
            - Often requires grouping first (e.g., "per floor", "within each zone")

            **Spatial/Relationship Requirements**:
            - Language: "adjacent to", "connected to", "within", "distance from"
            - Intent: Check spatial or topological relationships
            - Requires relational or topological analysis

            **Implicit Requirements**:
            - Language: Often unstated or assumed. Implied by the primary requirement.
            - Intent: To identify necessary intermediate steps, data, or logical connections that are not explicitly mentioned but are required for the check.
            - Example: Regulation "travel distance to an exit shall not exceed 30m" IMPLIES the need to:
                (1) Identify all habitable spaces and all designated exits.
                (2) Perform a topological analysis of the building model to find valid travel paths (e.g., through corridors and doors).
                (3) Calculate the length of these paths. A simple geometric distance check is incorrect.

            **Filtering Keywords**:
            - "required", "designated", "accessible", "emergency", "fire-rated", "exit"
            - Meaning: Need to identify a SUBSET of elements, not all elements of a type
            - Often requires checking properties like IsExternal, FireExit, UsageType
            - Example: "required exit" ≠ "all doors", need to filter to exits only

            ## Output Guidelines:

            Provide a structured interpretation with:
            1. **plain_language**: A simple 2-3 sentence explanation of what the regulation requires, avoiding jargon
            2. **term_clarifications**: For each technical term that might be ambiguous:
            - What it means in this context
            - How it maps to IFC (specific entities/properties)
            - Examples if helpful
            3. **common_misunderstandings**: Mistakes to avoid (e.g., confusing counting with verification, wrong IFC entities)

            Focus on DISAMBIGUATION and CLARITY. Your interpretation will guide the plan generation process.
            Do NOT prescribe HOW to check compliance - that will be determined in later stages."""

            # Build user prompt with automatic search context integration
            all_summaries = self.shared_context.get_all_summaries()

            additional_context_text = ""
            if all_summaries:
                additional_context_text = f"""
                ## Additional Context (from web searches):
                {all_summaries}

                Please incorporate this additional information into your interpretation.
                """

            prompt = f"""Interpret this building regulation:
            "{regulation_text}"
            {additional_context_text}
            Based on the regulation and any provided context, provide a structured interpretation focusing on its precise meaning, technical terms, and IFC mappings.
            """

            # Call LLM to generate interpretation
            interpretation = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=RegulationInterpretation
            )

            # Check if LLM call failed
            if isinstance(interpretation, str):
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_interpretation",
                    error=f"LLM call failed: {interpretation}"
                )

            print(f"RegulationInterpretation: Generated interpretation with {len(interpretation.term_clarifications)} term clarifications")

            # Store in SharedContext for future use
            self.shared_context.session_info["interpretation"] = interpretation

            return AgentToolResult(
                success=True,
                agent_tool_name="generate_interpretation",
                result=interpretation
            )

        except Exception as e:
            print(f"RegulationInterpretation: Failed to generate interpretation: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="generate_interpretation",
                error=f"Interpretation generation failed: {str(e)}"
            )
