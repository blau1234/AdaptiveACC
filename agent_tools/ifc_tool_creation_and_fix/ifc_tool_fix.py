import json
import traceback
from typing import Dict, Any, Optional
from models.common_models import AgentToolResult, IFCToolResult, ToolCreatorOutput, ToolMetadata
from models.shared_context import SharedContext
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from agent_tools.ifc_tool_creation_and_fix.code_generator import CodeGenerator
from telemetry.tracing import trace_method
from opentelemetry import trace

class ToolFix:
    """Skill to fix existing tools with various types of errors"""

    def __init__(self):
        self.tool_registry = IFCToolRegistry.get_instance()
        self.code_generator = CodeGenerator()
        self.shared_context = SharedContext.get_instance()

    # Executor Interface
    @trace_method("fix_ifc_tool")
    def fix_ifc_tool(self, ifc_tool_name: str = "") -> AgentToolResult:
        """Fix an IFC tool that failed execution.

        Gets error information from SharedContext and attempts to fix the tool
        that encountered runtime or syntax errors. If ifc_tool_name is not provided,
        uses the most recent failed tool execution from the context.

        Args:
            ifc_tool_name: Name of the IFC tool to fix (optional, gets error info from SharedContext if missing)

        Returns:
            AgentToolResult: Success with fixed tool info, or failure if fix unsuccessful
        """

        span = trace.get_current_span()

        try:
            # Record tool being fixed
            span.set_attribute("fix_ifc_tool.target_ifc_tool_name", ifc_tool_name)

            # Step 1: Get error information from SharedContext
            check_result = self.shared_context.get_error_info_from_context(ifc_tool_name)
            if not check_result:
                span.set_attribute("fix_ifc_tool.success", False)
                span.set_attribute("fix_ifc_tool.error", f"No error information found for IFC tool '{ifc_tool_name}'")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="fix_ifc_tool",
                    error=f"No error information found for IFC tool '{ifc_tool_name}' in execution history"
                )
                return result

            # Record error information (check_result is a dict from agent_history)
            span.set_attribute("fix_ifc_tool.error_type", check_result.get('exception_type') or "unknown")
            span.set_attribute("fix_ifc_tool.error_message", check_result.get('error_message') or "")

            # Step 2: Get original tool code and metadata
            original_tool_info = self._get_tool_info(check_result.get('ifc_tool_name'))
            if not original_tool_info:
                span.set_attribute("fix_ifc_tool.success", False)
                span.set_attribute("fix_ifc_tool.error", f"IFC tool '{check_result.get('ifc_tool_name')}' not found")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="fix_ifc_tool",
                    error=f"IFC tool '{check_result.get('ifc_tool_name')}' not found in registry for fixing"
                )
                return result

            original_metadata = original_tool_info["metadata"]
            ifc_tool_name = original_tool_info["name"]
            code = original_tool_info["code"]

            # Step 2: Fix the code using fix_code method
            # Convert check_result dict to IFCToolResult for code_generator
            span.set_attribute("llm_call.purpose", "ifc_tool_code_fix")
            check_result_obj = IFCToolResult(**check_result)
            fixed_code = self.code_generator.fix_code(
                code=code,
                check_result=check_result_obj,
                metadata=original_metadata
            )

            if not fixed_code:
                span.set_attribute("fix_ifc_tool.success", False)
                span.set_attribute("fix_ifc_tool.error", f"Failed to fix code for IFC tool '{ifc_tool_name}'")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="fix_ifc_tool",
                    error=f"Failed to fix code for IFC tool '{ifc_tool_name}'"
                )
                return result

            # Step 3: Create ToolCreatorOutput with fixed code and preserved metadata
            fixed_tool_output = ToolCreatorOutput(
                ifc_tool_name=ifc_tool_name,
                code=fixed_code,
                metadata=original_metadata
            )

            # Record successful fix
            span.set_attribute("fix_ifc_tool.success", True)
            span.set_attribute("fix_ifc_tool.fixed_ifc_tool_name", ifc_tool_name)
            span.set_attribute("fix_ifc_tool.fixed_code", fixed_code[:500] + "..." if len(fixed_code) > 500 else fixed_code)

            result = AgentToolResult(
                success=True,
                agent_tool_name="fix_ifc_tool",
                result=fixed_tool_output  # ToolCreatorOutput object
            )
            print(f"ToolFix: Successfully fixed IFC tool '{ifc_tool_name}'")

            return result

        except Exception as e:
            print(f"ToolFix: IFC tool fix failed with exception - {str(e)}")
            span.set_attribute("fix_ifc_tool.success", False)
            span.set_attribute("fix_ifc_tool.error", str(e))
            result = AgentToolResult(
                success=False,
                agent_tool_name="fix_ifc_tool",
                error=f"IFC tool fix failed: {str(e)}"
            )
            return result



    def _get_tool_info(self, ifc_tool_name: str) -> Optional[Dict[str, Any]]:
        """Get original tool information, prioritizing SharedContext"""
        try:
            # First, try to get from SharedContext (recent tool creations/fixes)
            shared_context = SharedContext.get_instance()
            tool_creation_data = shared_context.get_tool_by_name(ifc_tool_name)

            if tool_creation_data:
                print(f"Found tool '{ifc_tool_name}' in SharedContext meta_tool_trace")
                # tool_creation_data is a dict from agent_history
                return {
                    "name": tool_creation_data.get('ifc_tool_name'),
                    "code": tool_creation_data.get('code'),
                    "metadata": tool_creation_data.get('metadata')
                }

        except Exception as e:
            print(f"Failed to get tool info for '{ifc_tool_name}': {e}")
            return None