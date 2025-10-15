
import json
from typing import Dict, Any
from utils.llm_client import LLMClient
from models.common_models import ComplianceEvaluationModel, AgentToolResult
from models.shared_context import SharedContext
from telemetry.tracing import trace_method


class ComplianceReport:
    """Generates structured compliance report from IFC tool execution results."""

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()

    @trace_method("compliance_report_generation")
    def generate_report(self) -> AgentToolResult:
        """Generate structured compliance report from IFC tool execution results.

        This function is automatically called by ComplianceAgent when the agent
        stops calling tools, indicating data collection is complete.

        Organizes and summarizes all IFC tool execution results from agent_history
        into a structured compliance report.

        Returns:
            AgentToolResult with ComplianceEvaluationModel in result field
        """
        try:
            # 1. Get regulation text
            regulation_text = self.shared_context.session_info.get("regulation_text", "")

            # 2. Get successful IFC tool executions from agent_history
            successful_executions = self.shared_context.get_successful_ifc_tool_executions()

            if not successful_executions:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_compliance_report",
                    error="No successful IFC tool executions found in agent_history"
                )

            # 3. Extract simplified tool execution results
            tool_results = []
            for entry in successful_executions:
                action_result = entry['action_result']
                result_data = action_result.get('result', {})

                # Extract IFC tool result
                if result_data:
                    tool_results.append({
                        "tool_name": result_data.get('ifc_tool_name', 'unknown'),
                        "result": result_data.get('result')
                    })

            if not tool_results:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_compliance_report",
                    error="No successful IFC tool execution results found to generate report"
                )

            # 4. Build system prompt
            system_prompt = """
            You are a building code compliance reporting expert. Your task is to generate a structured compliance report by organizing and summarizing tool execution results.

            ## CRITICAL: Your Core Responsibilities

            **Your primary role is to organize and summarize existing tool results. You MUST NOT re-evaluate or second-guess the compliance status determined by the tools.** 

            **1.  Organize & Report**: For compliance status, your job is to be a faithful reporter of the tool's findings.
                - If tool results contain judgment fields (e.g., `meets_threshold`, `passes_check`, boolean values) → USE them directly to determine `compliance_status`.
                - If tool results only contain raw data → Then you perform a simple evaluation to determine the `compliance_status`.
                - **Never alter a compliance judgment that is already present in the tool's results.**

            **2.  Analyze & Suggest**: For non-compliant items, **you ARE REQUIRED to generate a concise and actionable `suggested_fix`**. This is your main analytical contribution.

            ## Output Structure

            ### CheckedComponent (required for each component-rule pair)
            - **component_id**: IFC GUID or unique identifier from the tool results.
            - **component_type**: IFC class name (e.g., "IfcStair", "IfcDoor").
            - **checked_rule**: Specific requirement being checked (e.g., "Minimum width").
            - **data_used**: Key-value pairs extracted from execution results, providing evidence (e.g., {"width": "1000mm", "threshold": "914mm"}).
            - **compliance_status**: "compliant" / "non_compliant" / "uncertain".
            - **violation_reason**: Required if non_compliant or uncertain. Use judgment fields if available (e.g., "Does not meet threshold (comparison: 750mm >= 800mm = false)").
            - **suggested_fix**: Required if `compliance_status` is 'non_compliant'. You must generate a clear, actionable remediation suggestion based on the `violation_reason` and `data_used` fields. 
                For example, if the violation is "Width 750mm is less than required 800mm", a good suggestion would be "Increase width to 800mm or more".

            ### RelationshipCheck (optional, only if regulation involves component interactions)
            - **relation_type**: "geometry" / "topology" / "semantic".
            - **relation_name**: Descriptive name.
            - **involved_components**: List of component IDs.
            - **compliance_status**: "compliant" / "non_compliant" / "uncertain".
            - **analysis_evidence**: Supporting data.
            - **violation_reason**: Required if non_compliant.
            - **(Note: `suggested_fix` can also be added here if applicable for relationship violations)**

            ### overall_status (required)
            - **"compliant"**: All components meet requirements.
            - **"non_compliant"**: All components fail requirements.
            - **"partial"**: Mix of compliant and non-compliant.
            - **"uncertain"**: Insufficient data or ambiguous results.
            - **"not_applicable"**: Regulation doesn't apply.

            ## Process

            1.  Parse the provided tool execution results to extract component data and any pre-existing judgment fields.
            2.  For each checked component, create a `CheckedComponent` object.
            3.  Determine the `compliance_status` based on the judgment fields if present; otherwise, evaluate the raw data.
            4.  If a component is 'non_compliant', analyze its `violation_reason` and `data_used` to generate a practical `suggested_fix`.
            5.  After processing all components, determine the `overall_status`."""

            # 5. Get last action context
            last_action_text = self.shared_context.format_last_action()

            # 6. Build user prompt
            prompt = f"""
            REGULATION TEXT:
            {regulation_text}

            TOOL EXECUTION RESULTS:
            {json.dumps(tool_results, indent=2)}
            
            LAST ACTION:
            {last_action_text}

            TASK: Generate a structured compliance report based on the tool execution results. Each tool has produced result data. Use judgment fields (e.g., meets_threshold, comparison_result) directly if present in the result.
            """

            # 7. Call LLM to generate compliance report
            print(f"ComplianceReport: Generating report from {len(tool_results)} tool execution results...")
            report = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=ComplianceEvaluationModel
            )

            print(f"ComplianceReport: Report generated - {report.overall_status}")

            return AgentToolResult(
                success=True,
                agent_tool_name="generate_compliance_report",
                result=report
            )

        except Exception as e:
            print(f"ComplianceReport: Report generation failed: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="generate_compliance_report",
                error=f"Compliance report generation failed: {str(e)}"
            )
