
from datetime import datetime
from typing import Dict, Any, Optional

from smolagents.local_python_executor import LocalPythonExecutor as SmolagentsExecutor
from .data_models import TestResult


class LocalPythonExecutor:
    """Local Python code executor using smolagents with sandboxing"""
    
    def __init__(self, timeout: int = 30, max_memory_mb: int = 512):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        # Add print function and other basic functions to allowed functions
        additional_functions = {
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'type': type,
            'isinstance': isinstance,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr
        }
        
        self.executor = SmolagentsExecutor(
            additional_authorized_imports=['pytest', 'ifcopenshell', 'os'],
            additional_functions=additional_functions
        )
    
    def execute_code(self, code: str, test_inputs: Optional[Dict[str, Any]] = None) -> TestResult:
        """Execute code with given inputs and return results"""
        try:
            # Prepare code with test inputs if provided
            if test_inputs:
                # Add test inputs to the code as global variables
                inputs_code = "# Test inputs\n"
                for key, value in test_inputs.items():
                    inputs_code += f"{key} = {repr(value)}\n"
                code = inputs_code + "\n" + code
            
            # Execute using smolagents executor
            result = self.executor(code)
            
            # Handle smolagents CodeOutput result
            if hasattr(result, 'output'):
                success = True  # If no exception was raised, consider it successful
                output = str(result.output) if result.output is not None else ""
                error = ""
            else:
                # Fallback for other result types
                success = True
                output = str(result)
                error = ""
                
        except Exception as e:
            success = False
            output = ""
            error = f"Execution error: {str(e)}"
        
        return TestResult(
            success=success,
            output=output,
            error=error
        )
    
    def execute_with_test_framework(self, code: str, test_code: str) -> TestResult:
        """Execute code with accompanying test code"""
        combined_code = f"""
        # Generated function code
        {code}

        # Test code
        {test_code}
        """
        return self.execute_code(combined_code)
    
    
    def validate_imports(self, code: str) -> TestResult:
        """Validate that all imports in the code are available"""
        # Extract import statements
        import_lines = []
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append(line)
        
        if not import_lines:
            return TestResult(
                success=True,
                output="No imports to validate",
                error=""
            )
        
        # Create test code that only tests imports
        test_code = '\n'.join(import_lines) + '\nprint("All imports successful")'
        
        return self.execute_code(test_code)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution environment statistics"""
        return {
            "timeout": self.timeout,
            "max_memory_mb": self.max_memory_mb,
            "executor_type": "smolagents.LocalPythonExecutor",
            "python_version": "Current runtime",
            "platform": "Sandboxed environment"
        }
    
    def execute_function_with_args(self, code: str, function_name: str, 
                                   args: list = None, kwargs: dict = None) -> TestResult:
        """Execute a specific function with provided arguments"""
        args = args or []
        kwargs = kwargs or {}
        
        # Create test execution code
        test_code = f"""
        {code}

        import json
        import traceback

        try:
            # Call the function with provided arguments
            result = {function_name}(*{repr(args)}, **{repr(kwargs)})
            print(f"SUCCESS: {{result}}")
            print(f"RESULT_TYPE: {{type(result).__name__}}")
            if hasattr(result, '__len__') and not isinstance(result, str):
                print(f"RESULT_LENGTH: {{len(result)}}")
        except Exception as e:
            print(f"ERROR: {{str(e)}}")
            print(f"ERROR_TYPE: {{type(e).__name__}}")
            print(f"TRACEBACK:")
            traceback.print_exc()
            raise
        """
        return self.execute_code(test_code)