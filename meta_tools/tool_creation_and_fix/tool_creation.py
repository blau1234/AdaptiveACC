
from models.common_models import MetaToolResult, DomainToolResult, ToolCreatorOutput
from models.shared_context import SharedContext
from .spec_generator import SpecGenerator
from .code_generator import CodeGenerator
from utils.rag_doc import DocumentRetriever


class ToolCreation:
    """Meta tool to create new tools based on task step analysis"""

    def __init__(self):
        
        self.spec_generator = SpecGenerator()
        self.code_generator = CodeGenerator()
        self.document_retriever = DocumentRetriever.get_instance()
        self.max_static_iterations = 3
        
    # Executor Interface
    def tool_creation(self) -> MetaToolResult:

        print(f"=== Creating tool ===")
        
        try:
            step = self.shared_context.current_task.get("step")

            # Step 1: SpecGenerator analyzes step content
            tool_spec = self.spec_generator.generate_spec(step)

            # Step 2: Retrieve relevant documentation
            print("\n[Step 2] Retrieving relevant documentation...")
            relevant_docs = self.document_retriever.retrieve_relevant_docs(
                tool_spec.description, k=5
            )
            print(f"  Retrieved {len(relevant_docs)} relevant documents")

            # Step 3: Use CodeGeneratorAgent to generate tool with structured output
            tool_output = self.code_generator.generate_code(tool_spec, relevant_docs)

            if not tool_output:
                return MetaToolResult(
                    success=False,
                    tool_name="tool_creation",
                    error="Failed to generate tool output"
                )

            # Step 4: Static checking with retry on generated code
            print("\n[Step 4] Static code analysis...")
            current_code = tool_output.code

            for iteration in range(1, self.max_static_iterations + 1):
                check_result = self._check_syntax(current_code, tool_output.tool_name)

                if check_result.success:
                    print(f"  Static analysis PASSED after {iteration} iterations")
                    # Update tool_output with validated code if it was modified
                    if current_code != tool_output.code:
                        tool_output.code = current_code
                    break

                if iteration < self.max_static_iterations:
                    print(f"  Found syntax issues, attempting to fix...")
                    # Use simplified fix_code method
                    current_code = self.code_generator.fix_code(
                        code=current_code,
                        check_result=check_result,
                        metadata=tool_output.metadata
                    )
                else:
                    return MetaToolResult(
                        success=False,
                        tool_name="tool_creation",
                        error=f"Static check failed: {check_result.error_message or 'Unknown syntax error'}"
                    )

            # Step 5: Output final tool
            print(f"\n[Step 5] Tool '{tool_output.tool_name}' created successfully")

            
            # Create result with ToolCreatorOutput
            result = MetaToolResult(
                success=True,
                meta_tool_name="tool_creation",
                result=tool_output  # ToolCreatorOutput object
            )
            
            # Record successful tool creation to SharedContext
            shared_context = SharedContext.get_instance()
            shared_context.meta_tool_trace.append(result)

            return result
            
        except Exception as e:
            print(f"\n=== Tool creation FAILED with exception ===")
            print(f"Error: {str(e)}")
            
            return MetaToolResult(
                success=False,
                tool_name="tool_creation",
                error=f"Unexpected error: {str(e)}"
            )
    

    def _check_syntax(self, code: str, tool_name: str = "unknown") -> DomainToolResult:
        """Basic syntax checking"""
        try:
            compile(code, '<string>', 'exec')
            return DomainToolResult(
                success=True,
                domain_tool_name=tool_name
            )
        except SyntaxError as e:
            return DomainToolResult(
                success=False,
                domain_tool_name=tool_name,
                error_message=f"Syntax error at line {e.lineno}: {e.msg}",
                exception_type="SyntaxError",
                line_number=e.lineno
            )
        except Exception as e:
            return DomainToolResult(
                success=False,
                domain_tool_name=tool_name,
                error_message=f"Code analysis error: {e}",
                exception_type=type(e).__name__
            )    
