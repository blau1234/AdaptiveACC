import json
from typing import List, Tuple, Optional
from utils.llm_client import LLMClient
from models.common_models import RetrievedDocument, ToolSpec, ToolCreatorOutput, ToolMetadata, ToolParam, DomainToolResult, FixedCodeOutput


class CodeGenerator:
    """Agent to generate Python code based on ToolSpec and relevant documentation"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    

    def generate_code(self, tool_spec: ToolSpec, relevant_docs: List[RetrievedDocument]) -> ToolCreatorOutput:
        """Generate complete tool with structured output using instructor"""

        system_prompt = """You are an expert Python developer specializing in IFC file processing and building compliance checking.
        Your task is to generate complete, production-ready Python functions based on precise tool specifications.

        CORE RESPONSIBILITIES:
        - Generate complete, runnable Python functions with proper structure
        - Follow IFC processing best practices
        - Implement comprehensive error handling
        - Create accurate metadata describing the tool

        STRUCTURED OUTPUT REQUIREMENTS:
        You must provide:
        1. tool_name: The function name from the specification
        2. code: Complete Python function code ready to execute
        3. metadata: Detailed tool metadata including:
           - description: Clear description of what the tool does
           - parameters: List of ToolParam objects with name, type, description, required, default
           - return_type: Expected return type
           - category: Tool category (use the primary library name)
           - tags: List of relevant keywords for search and discovery

        CODE QUALITY REQUIREMENTS:
        - Include proper imports and type hints
        - Follow PEP 8 style guidelines
        - Add comprehensive docstrings
        - Implement robust error handling
        - Use appropriate data structures for return values
        - All comments and docstrings must be in English
        """

        # Process relevant documentation
        docs_context = ""
        if relevant_docs:
            docs_context = "RELEVANT DOCUMENTATION:\n"
            for i, doc in enumerate(relevant_docs, 1):
                docs_context += f"Document {i} (relevance: {doc.relevance_score:.3f}):\n"
                docs_context += f"{doc.content[:500]}...\n\n"

        # Format parameters for prompt
        param_descriptions = []
        for param in tool_spec.parameters:
            param_descriptions.append(f"- {param['name']}: {param['type']} - {param.get('description', 'No description')}")

        prompt = f"""
        {docs_context}

        TOOL SPECIFICATION:
        Function name: {tool_spec.function_name}
        Description: {tool_spec.description}
        Primary Library: {tool_spec.library}
        Return type: {tool_spec.return_type}

        Parameters:
        {chr(10).join(param_descriptions)}

        Generate a complete tool implementation with all required metadata.
        The generated function should use {tool_spec.library} as the primary library.
        """

        try:
            tool_output = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                response_model=ToolCreatorOutput,
                max_retries=3
            )
            return tool_output

        except Exception as e:
            print(f"LLM structured tool generation failed: {e}")
            return None

    def fix_code(self, code: str, check_result: DomainToolResult, metadata: ToolMetadata) -> str:
        """修复代码错误，专注于代码本身的修复"""

        system_prompt = """You are an expert Python developer specializing in IFC file processing and building compliance checking.
        Your task is to fix Python code issues while maintaining the original functionality.

        CORE RESPONSIBILITIES:
        - Analyze the specific error type and context
        - Fix the root cause of the error
        - Maintain original function signature and behavior
        - Follow IFC processing best practices
        - Implement comprehensive error handling

        CODE QUALITY REQUIREMENTS:
        - Include proper imports and type hints
        - Follow PEP 8 style guidelines
        - Add comprehensive docstrings with parameter descriptions
        - Implement robust error handling with meaningful messages
        - Validate input parameters and handle edge cases
        - Use appropriate data structures for return values
        - All comments and docstrings must be in English

        OUTPUT FORMAT:
        - Return the corrected code and a brief summary of changes made
        - Focus on fixing the specific error while preserving functionality"""

        # Build error context based on exception type
        error_context = self._build_error_context(check_result)

        user_prompt = f"""Fix the Python code based on the following error information:

        ERROR DETAILS:
        - Tool Name: {check_result.tool_name}
        - Error Type: {check_result.exception_type or 'Unknown'}
        - Error Message: {check_result.error_message or 'No error message'}
        {f"- Line Number: {check_result.line_number}" if check_result.line_number else ""}

        {error_context}

        CURRENT CODE:
        {code}

        TOOL METADATA:
        - Function Name: {check_result.tool_name}
        - Description: {metadata.description}
        - Parameters: {[param.model_dump() for param in metadata.parameters]}
        - Return Type: {metadata.return_type}
        - Category: {metadata.category}

        Fix the error while maintaining the original functionality and requirements."""

        try:
            fixed_output = self.llm_client.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_model=FixedCodeOutput,
                max_retries=3
            )

            return fixed_output.code

        except Exception as e:
            print(f"LLM code fixing failed: {e}")
            # Return original code if fixing fails
            return code

    def _build_error_context(self, check_result: DomainToolResult) -> str:
        """Build error-specific context for fixing"""

        context_map = {
            # Syntax errors
            "SyntaxError": "SYNTAX ERROR: Check for missing parentheses, brackets, quotes, or incorrect indentation.",
            "IndentationError": "INDENTATION ERROR: Fix inconsistent indentation, mixing tabs and spaces.",
            "TabError": "TAB ERROR: Ensure consistent use of tabs or spaces for indentation.",

            # Import errors
            "ImportError": "IMPORT ERROR: Fix import statements, check module names, or add missing dependencies.",
            "ModuleNotFoundError": "MODULE ERROR: The required module is not installed or the import path is incorrect. Consider alternative imports or add proper imports.",

            # Runtime errors
            "NameError": "NAME ERROR: The variable or function name is not defined. Check for typos or missing imports.",
            "TypeError": "TYPE ERROR: Fix type mismatches, incorrect argument types, or missing/extra arguments.",
            "AttributeError": "ATTRIBUTE ERROR: The object doesn't have the specified attribute or method. Check object type and available methods.",
            "ValueError": "VALUE ERROR: Fix invalid argument values or data conversion issues.",
            "RuntimeError": "RUNTIME ERROR: General runtime issue, check logic flow and error conditions.",

            # Logic errors
            "KeyError": "KEY ERROR: Dictionary key doesn't exist. Add key existence checks or use .get() method.",
            "IndexError": "INDEX ERROR: List/array index is out of range. Add bounds checking.",
            "AssertionError": "ASSERTION ERROR: An assertion failed. Check the assertion condition and fix the logic.",
        }

        error_type = check_result.exception_type or "Unknown"
        context = context_map.get(error_type, f"UNKNOWN ERROR ({error_type}): Analyze the error message and fix accordingly.")

        # Add traceback context if available
        if check_result.traceback:
            context += f"\n\nTRACEBACK ANALYSIS:\n{check_result.traceback[:500]}..."

        return context