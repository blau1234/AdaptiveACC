
import os
from typing import Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

from utils.ifc_parser import IFCParser
from .data_models import TestResult, ToolRequirement, DynamicTestResult
from .executor import LocalPythonExecutor
from models.blackboard_models import BlackboardMixin


class DynamicTester(BlackboardMixin):
    def __init__(self):
        super().__init__()
        self.executor = LocalPythonExecutor()
        self.ifc_parser = IFCParser()
    
    def test_tool(self, tool_code: str, tool_requirement: ToolRequirement, 
                  ifc_dependencies: Dict[str, Any], 
                  test_parameters: Dict[str, Any]) -> DynamicTestResult:
        
        ifc_file_path = test_parameters.get("ifc_file_path", "")
        print(f"Starting dynamic testing for IFC file: {ifc_file_path}")
        print(f"Function parameters: {list(test_parameters.keys())}")
        
        # Initialize result components
        issues_found = []
        data_availability = False
        tool_execution = False
        execution_details = {}
        missing_elements = []
        missing_properties = []
        
        try:
            # Step 1: Data availability check
            print("Step 1: Data availability check...")
            data_available, missing_data = self._check_data_availability(
                ifc_file_path, ifc_dependencies
            )
            data_availability = data_available
            missing_elements = missing_data.get("missing_elements", [])
            missing_properties = missing_data.get("missing_properties", [])
            
            if not data_available:
                issues_found.append("Data missing: IFC file does not contain required data types")
                for element in missing_elements:
                    issues_found.append(f"Missing IFC element type: {element}")
                
                return DynamicTestResult(
                    success=False,
                    issues=issues_found,
                    data_availability=data_availability,
                    tool_execution=tool_execution,
                    execution_details=execution_details,
                    missing_elements=missing_elements,
                    missing_properties=missing_properties
                )
            
            # Step 2: Tool execution
            print("Step 2: Tool execution...")
            execution_success, exec_details = self._execute_tool(
                tool_code, tool_requirement, test_parameters
            )
            tool_execution = execution_success
            execution_details = exec_details
            
            if not execution_success:
                issues_found.append(f"Tool execution failed: {execution_details.get('error', 'Unknown error')}")
                
                return DynamicTestResult(
                    success=False,
                    issues=issues_found,
                    data_availability=data_availability,
                    tool_execution=tool_execution,
                    execution_details=execution_details,
                    missing_elements=missing_elements,
                    missing_properties=missing_properties
                )
            
            # Step 3: Success
            print("Dynamic testing completed successfully")
            return DynamicTestResult(
                success=True,
                issues=[],
                data_availability=data_availability,
                tool_execution=tool_execution,
                execution_details=execution_details,
                missing_elements=missing_elements,
                missing_properties=missing_properties
            )
            
        except Exception as e:
            issues_found.append(f"Dynamic testing error: {str(e)}")
            print(f"Dynamic testing error: {str(e)}")
            return DynamicTestResult(
                success=False,
                issues=issues_found,
                data_availability=data_availability,
                tool_execution=tool_execution,
                execution_details=execution_details,
                missing_elements=missing_elements,
                missing_properties=missing_properties
            )
    
    def _check_data_availability(self, ifc_file_path: str, ifc_dependencies: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
       
        missing_data = {
            "missing_elements": [],
            "missing_properties": []
        }
        
        try:
            # Load IFC file
            if not self.ifc_parser.load_file(ifc_file_path):
                print("Failed to load IFC file")
                return False, missing_data
            
            # Check IFC dependencies (now directly as element types and properties)
            print(f"Checking for required elements: {list(ifc_dependencies.keys())}")
            
            # Check each element type and its properties
            for element_type, required_props in ifc_dependencies.items():
                elements = self.ifc_parser.get_elements_by_type(element_type)
                
                if not elements:
                    print(f"Missing required element type: {element_type} (found 0 elements)")
                    missing_data["missing_elements"].append(element_type)
                else:
                    print(f"Found {len(elements)} elements of type {element_type}")
                    
                    # Check required properties for this element type
                    if required_props and elements:
                        # Check properties on first element of this type
                        element_properties = self.ifc_parser.extract_properties(elements[0])
                        for prop in required_props:
                            if prop not in element_properties:
                                missing_data["missing_properties"].append(f"{element_type}:{prop}")
                                print(f"Missing property '{prop}' for element type '{element_type}'")
            
            # Determine if data is available
            has_missing_elements = len(missing_data["missing_elements"]) > 0
            has_missing_properties = len(missing_data["missing_properties"]) > 0
            
            data_available = not (has_missing_elements or has_missing_properties)
            
            if data_available:
                print("Data availability check passed")
            else:
                print("Data availability check failed")
                
            return data_available, missing_data
            
        except Exception as e:
            print(f"Data availability check error: {e}")
            return False, missing_data
    
    def _execute_tool(self, tool_code: str, tool_requirement: ToolRequirement, 
                      test_parameters: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        
        execution_details = {
            "success": False,
            "output": "",
            "error": ""
        }
        
        try:
            print(f"Executing tool function: {tool_requirement.function_name}")
            print(f"Function parameters: {[p['name'] for p in tool_requirement.parameters]}")
            
            # Create test execution code using test parameters
            test_code = self._create_test_execution_code(
                tool_code, tool_requirement.function_name, test_parameters
            )
            
            # Execute test code
            print("Running tool execution...")
            result = self.executor.execute_code(test_code)
            
            execution_details.update({
                "success": result.success,
                "output": result.output,
                "error": result.error
            })
            
            if result.success:
                print(f"Tool execution successful: {result.output}")
                return True, execution_details
            else:
                print(f"Tool execution failed: {result.error}")
                return False, execution_details
                
        except Exception as e:
            execution_details["error"] = str(e)
            print(f"Tool execution error: {e}")
            return False, execution_details
    
    def _create_test_execution_code(self, tool_code: str, function_name: str, 
                                   test_parameters: Dict[str, Any]) -> str:
        
        print(f"Creating test code with parameters: {test_parameters}")
        
        # Build parameter assignments directly using repr() for all values
        param_assignments = []
        param_names = []
        
        for param_name, param_value in test_parameters.items():
            param_names.append(param_name)
            # Use repr() for all parameter values - simple and reliable
            param_assignments.append(f'{param_name} = {repr(param_value)}')
        
        # Create simple test execution code - no validation, just execution
        test_code = f'''
        {tool_code}

        # Test execution
        import traceback

        try:
            # Set up parameters directly from SpecGenerator
            {chr(10).join(['    ' + assignment for assignment in param_assignments])}
            
            # Call function
            result = {function_name}({", ".join(param_names)})
            
            # Print result
            print(f"SUCCESS: Function executed successfully. Result: {{result}}")
            
        except Exception as e:
            print(f"FAILED: Function execution failed: {{e}}")
            print("Traceback:")
            traceback.print_exc()
            raise e
        '''
        
        return test_code