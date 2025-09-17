import json
import traceback
from typing import Dict, Any, Optional
from models.common_models import MetaToolResult, DomainToolResult, ToolCreatorOutput, ToolMetadata
from models.shared_context import SharedContext
from domain_tools.domain_tool_registry import DomainToolRegistry
from meta_tools.tool_creation_and_fix.code_generator import CodeGenerator

class ToolFix:
    """Meta tool to fix existing tools with various types of errors"""

    def __init__(self):
        self.domain_registry = DomainToolRegistry.get_instance()
        self.code_generator = CodeGenerator()
        self.shared_context = SharedContext.get_instance()

    # Executor Interface
    def tool_fix(self, check_result: DomainToolResult) -> MetaToolResult:
        """Fix an existing tool based on check result information"""

        try:
            # Parse check result and metadata
            try:
                check_data = json.loads(check_result) if check_result else {}
                check_result = DomainToolResult(**check_data)
            except Exception as e:
                result = MetaToolResult(
                    success=False,
                    meta_tool_name="tool_fix",
                    error=f"Invalid check_result format: {str(e)}"
                )
                self.shared_context.meta_tool_trace.append(result)
                return result
            

            # Step 1: Get original tool code and metadata
            original_tool_info = self._get_tool_info(check_result.domain_tool_name)
            if not original_tool_info:
                result =  MetaToolResult(
                    success=False,
                    meta_tool_name="tool_fix",
                    error=f"Tool '{check_result.domain_tool_name}' not found in registry for fixing"
                )
                self.shared_context.meta_tool_trace.append(result)
                return result

            original_metadata = original_tool_info["metadata"]
            tool_name = original_tool_info["name"]
            code = original_tool_info["code"]

            # Step 2: Fix the code using fix_code method
            fixed_code = self.code_generator.fix_code(
                code=code,
                check_result=check_result,
                metadata=original_metadata
            )

            if not fixed_code:
                result = MetaToolResult(
                    success=False,
                    meta_tool_name="tool_fix",
                    error=f"Failed to fix code for tool '{tool_name}'"
                )
                self.shared_context.meta_tool_trace.append(result)
                return result

            # Step 3: Create ToolCreatorOutput with fixed code and preserved metadata
            fixed_tool_output = ToolCreatorOutput(
                tool_name=tool_name,
                code=fixed_code,
                metadata=original_metadata 
            )

            result = MetaToolResult(
                success=True,
                meta_tool_name="tool_fix",
                result=fixed_tool_output  # ToolCreatorOutput object
            )
            print(f"ToolFix: Successfully fixed tool '{tool_name}'")

            self.shared_context.meta_tool_trace.append(result)
            return result

        except Exception as e:
            print(f"ToolFix: Fix failed with exception - {str(e)}")
            result = MetaToolResult(
                success=False,
                meta_tool_name="tool_fix",
                error=f"Tool fix failed: {str(e)}"
            )
            self.shared_context.meta_tool_trace.append(result)
            return result

    def _get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get original tool information, prioritizing SharedContext"""
        try:
            # First, try to get from SharedContext (recent tool creations/fixes)
            shared_context = SharedContext.get_instance()
            tool_creation_data = shared_context.get_tool_by_name(tool_name)

            if tool_creation_data:
                print(f"Found tool '{tool_name}' in SharedContext meta_tool_trace")
                # tool_creation_data should be a ToolCreatorOutput
                return {
                    "name": tool_creation_data.tool_name,
                    "code": tool_creation_data.code,
                    "metadata": tool_creation_data.metadata
                }

        except Exception as e:
            print(f"Failed to get tool info for '{tool_name}': {e}")
            return None