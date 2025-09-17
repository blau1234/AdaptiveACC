import json
import uuid
import traceback
from typing import Dict, List, Any, Optional
from models.common_models import MetaToolResult, DomainToolResult
from models.shared_context import SharedContext
from domain_tools.domain_tool_registry import DomainToolRegistry
from utils.sandbox_executor import LocalPythonExecutor

class ToolExecution:
    """Meta tool to execute domain-specific tools with parameter preparation"""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()
        self.domain_registry =DomainToolRegistry.get_instance()

    # Executor Interface
    def tool_execution(self, tool_name: str, parameters: str, execution_mode: str = "safe") -> MetaToolResult:
        """Execute a tool with specified execution mode (safe or sandbox)"""

        try:
            # Parse LLM-provided parameters (no modification)
            try:
                params = json.loads(parameters) if parameters else {}
            except:
                params = {}

            print(f"ToolExecutor: Executing tool '{tool_name}' in {execution_mode} mode with {len(params)} parameters")

            # Execute based on mode
            if execution_mode == "sandbox":
                execution_result = self._execute_in_sandbox(tool_name, params)
            else:
                execution_result = self._execute_in_domain_registry(tool_name, params)

            result = MetaToolResult(
                success=execution_result.success,
                meta_tool_name="tool_execution",
                result=execution_result.model_dump(),
            )
            # Record tool execution result to SharedContext
            self.shared_context.meta_tool_trace.append(result)

            return result

        except Exception as e:
            result = MetaToolResult(
                success=False,
                meta_tool_name="tool_execution",
                error=f"Tool execution failed: {str(e)}"
            )
            self.shared_context.meta_tool_trace.append(result)
            return result


    def _execute_in_domain_registry(self, tool_name: str, parameters: Dict[str, Any]) -> DomainToolResult:

        try:
            # Check if tool exists
            if tool_name not in self.domain_registry.get_available_tools():
                return DomainToolResult(
                    success=False,
                    domain_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' not found in tool registry"
                )

            # Construct standard tool call format for ToolRegistry
            tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
            tool_call = {
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(parameters)
                }
            }

            # Execute using ToolRegistry's native execute_tool_calls method
            print(f"Executing tool '{tool_name}' with parameters: {list(parameters.keys())}")
            tool_responses = self.domain_registry.execute_tool_calls([tool_call])

            if tool_call_id in tool_responses:
                result = tool_responses[tool_call_id]

                return DomainToolResult(
                    success=True,
                    domain_tool_name=tool_name,
                    parameters_used=parameters,
                    result=result
                )
            else:
                return DomainToolResult(
                    success=False,
                    domain_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool execution returned no result for '{tool_name}'"
                )

        except Exception as e:
            return DomainToolResult(
                success=False,
                domain_tool_name=tool_name,
                parameters_used=parameters,
                error_message=f"Tool execution failed: {str(e)}",
                exception_type=type(e).__name__,
                traceback=traceback.format_exc()
            )

    def _execute_in_sandbox(self, tool_name: str, parameters: Dict[str, Any]) -> DomainToolResult:
        """Execute tool in sandbox environment for newly created tools"""
        try:
            # Get tool code from SharedContext
            shared_context = SharedContext.get_instance()
            tool_result = shared_context.get_tool_by_name(tool_name)

            if not tool_result:
                return DomainToolResult(
                    success=False,
                    domain_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' source code not found in SharedContext"
                )

            # Create sandbox executor and execute directly
            sandbox = LocalPythonExecutor()
            result = sandbox.execute_function_with_args(
                code=tool_result.code,
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

                return DomainToolResult(
                    success=True,
                    domain_tool_name=tool_name,
                    parameters_used=parameters,
                    result=parsed_result
                )
            else:
                return DomainToolResult(
                    success=False,
                    domain_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Sandbox execution failed: {result.error}"
                )

        except Exception as e:
            return DomainToolResult(
                success=False,
                domain_tool_name=tool_name,
                parameters_used=parameters,
                error_message=f"Sandbox execution error: {str(e)}",
                exception_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
