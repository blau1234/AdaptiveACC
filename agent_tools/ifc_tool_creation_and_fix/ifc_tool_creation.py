
from models.common_models import AgentToolResult, IFCToolResult, ToolCreatorOutput
from models.shared_context import SharedContext
from .spec_generator import SpecGenerator
from .code_generator import CodeGenerator
from utils.rag_doc import DocumentRetriever
from telemetry.tracing import trace_method
from opentelemetry import trace


class ToolCreation:
    """Meta tool to create new tools based on task step analysis"""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()
        self.spec_generator = SpecGenerator()
        self.code_generator = CodeGenerator()
        self.document_retriever = DocumentRetriever.get_instance()
        self.max_static_iterations = 3
        
    # Executor Interface
    @trace_method("create_ifc_tool")
    def create_ifc_tool(self, task_description: str) -> AgentToolResult:
        """Create a new IFC tool when none exists for the task.

        Analyzes the task description, generates a tool specification,
        retrieves relevant documentation, generates code, and performs static checking
        to create a new IFC tool that can handle the current task requirements.

        Args:
            task_description: Description of what the tool should accomplish

        Returns:
            AgentToolResult: Success with created tool info, or failure if creation failed
        """

        span = trace.get_current_span()
        print(f"=== Creating IFC tool ===")
        print(f"Task description: {task_description}")

        try:
            # Record task information
            span.set_attribute("create_ifc_tool.task_description", task_description)

            # Step 1: SpecGenerator analyzes task description
            print("\n[Step 1] Generating tool specification...")
            tool_spec = self.spec_generator.generate_spec(task_description)

            # Step 2: Retrieve relevant documentation
            print("\n[Step 2] Retrieving relevant documentation...")
            relevant_docs = self.document_retriever.retrieve_relevant_docs(
                tool_spec.description, k=5
            )
            print(f"Retrieved {len(relevant_docs)} relevant documents")
            span.set_attribute("create_ifc_tool.docs_retrieved", len(relevant_docs))

            # Step 3: Use CodeGeneratorAgent to generate tool with structured output
            print("\n[Step 3] Generating tool code...")
            tool_output = self.code_generator.generate_code(tool_spec, relevant_docs)
            print("\n[Step 3] Tool Code Generated")
            
            if not tool_output:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="create_ifc_tool",
                    error="Failed to generate tool output"
                )

            # Step 4: Static checking with retry on generated code
            print("\n[Step 4] Static code analysis...")
            current_code = tool_output.code

            for iteration in range(1, self.max_static_iterations + 1):
                check_result = self._check_syntax(current_code, tool_output.ifc_tool_name)

                if check_result.success:
                    print(f"Static analysis PASSED after {iteration} iterations")
                    # Update tool_output with validated code if it was modified
                    if current_code != tool_output.code:
                        tool_output.code = current_code
                    break

                if iteration < self.max_static_iterations:
                    print(f"Found syntax issues, attempting to fix...")
                    # Use simplified fix_code method
                    current_code = self.code_generator.fix_code(
                        code=current_code,
                        check_result=check_result,
                        metadata=tool_output.metadata
                    )
                else:
                    return AgentToolResult(
                        success=False,
                        agent_tool_name="create_ifc_tool",
                        error=f"Static check failed: {check_result.error_message or 'Unknown syntax error'}"
                    )

            # Step 5: Output final tool
            print(f"\n[Step 5] IFC tool '{tool_output.ifc_tool_name}' created successfully")

            # Record successful creation
            span.set_attribute("create_ifc_tool.success", True)
            span.set_attribute("create_ifc_tool.final_tool_name", tool_output.ifc_tool_name)
            span.set_attribute("create_ifc_tool.generated_code", tool_output.code[:500] + "..." if len(tool_output.code) > 500 else tool_output.code)

            # Create result with ToolCreatorOutput
            result = AgentToolResult(
                success=True,
                agent_tool_name="create_ifc_tool",
                result=tool_output  # ToolCreatorOutput object
            )

            return result

        except Exception as e:
            print(f"\n=== IFC tool creation FAILED with exception ===")
            print(f"Error: {str(e)}")

            span.set_attribute("create_ifc_tool.success", False)
            span.set_attribute("create_ifc_tool.error", str(e))

            return AgentToolResult(
                success=False,
                agent_tool_name="create_ifc_tool",
                error=f"Unexpected error: {str(e)}"
            )
    

    def _check_syntax(self, code: str, tool_name: str = "unknown") -> IFCToolResult:
        """Enhanced syntax and structure checking"""
        try:
            # Step 1: Basic syntax check
            compile(code, '<string>', 'exec')

            # Step 2: Check function definition exists
            import ast
            tree = ast.parse(code)

            # Find all function definitions
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

            if not functions:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    error_message="No function definition found in code",
                    exception_type="ValidationError"
                )

            # Step 3: Check if function name matches tool_name
            function_names = [f.name for f in functions]
            if tool_name != "unknown" and tool_name not in function_names:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    error_message=f"Function name mismatch. Expected '{tool_name}', found: {function_names}",
                    exception_type="ValidationError"
                )

            # Step 4: Check for required imports (IFCFileManager is commonly needed)
            import_names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    import_names.append(node.module)
                elif isinstance(node, ast.Import):
                    import_names.extend([alias.name for alias in node.names])

            # Validation passed
            return IFCToolResult(
                success=True,
                ifc_tool_name=tool_name
            )

        except SyntaxError as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                error_message=f"Syntax error at line {e.lineno}: {e.msg}",
                exception_type="SyntaxError",
                line_number=e.lineno
            )
        except Exception as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                error_message=f"Code analysis error: {e}",
                exception_type=type(e).__name__
            )    
