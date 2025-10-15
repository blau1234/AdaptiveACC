
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
            additional_authorized_imports=[
                # Original imports
                'pytest', 'ifcopenshell', 'os', 'json', 'traceback',
                # Standard library (essential for type hints)
                'typing', 'collections',
                # Third-party libraries (geometry operations)
                'shapely', 'trimesh', 'numpy',
                # Custom modules - top level
                'ifc_tool_utils', 'utils',
                # Custom modules - submodules (explicit paths required by smolagents)
                'utils.ifc_file_manager',
                'ifc_tool_utils.ifcopenshell',
                'ifc_tool_utils.ifcopenshell.element_queries',
                'ifc_tool_utils.ifcopenshell.property_queries',
                'ifc_tool_utils.ifcopenshell.geometry_queries',
                'ifc_tool_utils.ifcopenshell.relationship_queries',
                'ifc_tool_utils.shapely',
                'ifc_tool_utils.shapely.geometry_utils',
                'ifc_tool_utils.trimesh',
                'ifc_tool_utils.trimesh.mesh_utils'
            ],
            additional_functions=additional_functions
        )
        # Initialize static_tools by calling send_tools (required for additional_functions to work)
        self.executor.send_tools({})
    
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
        import json

        args = args or []
        kwargs = kwargs or {}

        # Build parameter assignment code to avoid dynamic unpacking
        # This creates individual parameter assignments that the sandbox can validate
        param_setup = []
        if kwargs:
            for key, value in kwargs.items():
                # Use repr for safe serialization of values
                param_setup.append(f"_{key} = {repr(value)}")

        # Build function call with explicit parameter names (no * or ** unpacking)
        if kwargs:
            # Named parameters
            param_names = ', '.join([f"{key}=_{key}" for key in kwargs.keys()])
            call_code = f"{function_name}({param_names})"
        elif args:
            # Positional parameters (construct as explicit list)
            args_repr = ', '.join([repr(arg) for arg in args])
            call_code = f"{function_name}({args_repr})"
        else:
            call_code = f"{function_name}()"

        # Build complete test code
        # Note: smolagents should handle builtins via additional_functions parameter
        test_code = f"""{code}

# Parameter setup (explicit assignments, no unpacking)
{chr(10).join(param_setup)}

# Call function with explicit parameters (sandbox-safe)
_result = {call_code}
_result
"""
        return self.execute_code(test_code)