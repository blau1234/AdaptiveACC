import json
import uuid
import traceback
from typing import Dict, List, Any, Optional
from models.common_models import AgentToolResult, IFCToolResult
from models.shared_context import SharedContext
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from utils.sandbox_executor import LocalPythonExecutor
from telemetry.tracing import trace_method
from opentelemetry import trace

class ToolExecution:
    """Skill to execute IFC tools with parameter preparation"""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()
        self.tool_registry = IFCToolRegistry.get_instance()

    # Executor Interface
    @trace_method("execute_ifc_tool")
    def execute_ifc_tool(self, ifc_tool_name: str, parameters: str, execution_mode: str) -> AgentToolResult:
        """Execute an IFC tool with given parameters and mode.

        Args:
            ifc_tool_name: Name of the IFC tool to execute
            parameters: JSON string of parameters for the tool
            execution_mode: Execution mode - 'safe' for existing tools, 'sandbox' for newly created tools

        Returns:
            AgentToolResult: Success with execution results, or failure if execution failed
        """

        span = trace.get_current_span()

        try:
            # Parse LLM-provided parameters (no modification)
            try:
                params = json.loads(parameters) if parameters else {}
            except:
                params = {}

            # Record execution details
            span.set_attribute("execute_ifc_tool.tool_name", ifc_tool_name)
            span.set_attribute("execute_ifc_tool.execution_mode", execution_mode)
            span.set_attribute("execute_ifc_tool.parameters", parameters)

            print(f"ToolExecutor: Executing IFC tool '{ifc_tool_name}' in {execution_mode} mode with {len(params)} parameters")

            # Execute based on mode
            if execution_mode == "sandbox":
                execution_result = self.execute_in_sandbox(ifc_tool_name, params)
            else:
                execution_result = self.execute_in_tool_registry(ifc_tool_name, params)

            # Record execution result
            span.set_attribute("execute_ifc_tool.success", execution_result.success)
            span.set_attribute("execute_ifc_tool.result", str(execution_result))

            result = AgentToolResult(
                success=execution_result.success,
                agent_tool_name="execute_ifc_tool",
                result=execution_result  # Directly embed IFCToolResult
            )

            return result

        except Exception as e:
            span.set_attribute("execute_ifc_tool.success", False)
            span.set_attribute("execute_ifc_tool.error", str(e))
            result = AgentToolResult(
                success=False,
                agent_tool_name="execute_ifc_tool",
                error=f"IFC tool execution failed: {str(e)}"
            )
            return result


    def execute_in_tool_registry(self, tool_name: str, parameters: Dict[str, Any]) -> IFCToolResult:

        try:
            # Check if tool exists
            if tool_name not in self.tool_registry.get_available_tools():
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' not found in tool registry"
                )

            # Construct standard tool call format for DomainToolRegistry
            tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
            tool_call = {
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(parameters)
                }
            }

            # Execute using DomainToolRegistry's native execute_tool_calls method
            print(f"Executing tool '{tool_name}' with parameters: {list(parameters.keys())}")
            tool_responses = self.tool_registry.execute_tool_calls([tool_call])

            if tool_call_id in tool_responses:
                result = tool_responses[tool_call_id]

                return IFCToolResult(
                    success=True,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    result=result
                )
            else:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool execution returned no result for '{tool_name}'"
                )

        except Exception as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                parameters_used=parameters,
                error_message=f"Tool execution failed: {str(e)}",
                exception_type=type(e).__name__,
                traceback=traceback.format_exc()
            )

    def execute_in_sandbox(self, tool_name: str, parameters: Dict[str, Any]) -> IFCToolResult:
        """Execute tool in sandbox environment for newly created tools"""
        try:
            # Get tool code from SharedContext
            shared_context = SharedContext.get_instance()
            tool_result = shared_context.get_tool_by_name(tool_name)

            if not tool_result:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' source code not found in SharedContext"
                )

            # Handle both dict and object formats (tool_result may be serialized as dict)
            if isinstance(tool_result, dict):
                code = tool_result.get('code')
                metadata = tool_result.get('metadata', {})
            else:
                code = tool_result.code
                metadata = tool_result.metadata

            if not code:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' has no code in SharedContext"
                )

            # Create sandbox executor and execute directly
            sandbox = LocalPythonExecutor()
            result = sandbox.execute_function_with_args(
                code=code,
                function_name=tool_name,
                kwargs=parameters
            )

            if result.success:
                # Parse the output to extract the actual return value
                try:
                    import ast
                    parsed_result = ast.literal_eval(result.output.strip())
                except:
                    parsed_result = result.output.strip()

                return IFCToolResult(
                    success=True,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    result=parsed_result
                )
            else:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Sandbox execution failed: {result.error}"
                )

        except Exception as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                parameters_used=parameters,
                error_message=f"Sandbox execution error: {str(e)}",
                exception_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
