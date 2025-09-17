
from datetime import datetime
from typing import Dict, Any, Optional

from smolagents.local_python_executor import LocalPythonExecutor as SmolagentsExecutor
from models.common_models import TestResult


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
            additional_authorized_imports=['pytest', 'ifcopenshell', 'os', 'json', 'traceback'],
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

    def execute_function_with_args(self, code: str, function_name: str,
                                   args: list = None, kwargs: dict = None) -> TestResult:
        """Execute a specific function with provided arguments"""
        args = args or []
        kwargs = kwargs or {}
        
        # Create test execution code
        test_code = f"""{code}

# Call the function with provided arguments
_result = {function_name}(*{repr(args)}, **{repr(kwargs)})
_result  # Return the result
"""
        return self.execute_code(test_code)