import json
import uuid
from typing import Dict, List, Any, Optional
from toolregistry import ToolRegistry


class ToolExecutor:
    """
    Meta Tool for intelligent tool execution with parameter preparation and result handling
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    # Executor Interface
    def tool_execution(self, tool_name: str, parameters: str, execution_context: str = "") -> str:
        """
        Executor interface for executing a domain-specific tool with parameter preparation
        
        Args:
            tool_name: Name of the tool to execute
            parameters: JSON string of parameters
            execution_context: JSON string of current execution context
            
        Returns:
            JSON string with execution result
        """
        try:
            # Parse parameters and context
            try:
                params = json.loads(parameters) if parameters else {}
            except:
                params = {}
            
            try:
                context = json.loads(execution_context) if execution_context else {}
            except:
                context = {}
            
            print(f"ToolExecutor: Executing tool '{tool_name}' with {len(params)} parameters")
            
            # Get tool schema for parameter preparation
            tool_schema = None
            tools_json = self.tool_registry.get_tools_json()
            for schema in tools_json:
                if schema.get("function", {}).get("name") == tool_name:
                    tool_schema = schema
                    break
            
            if not tool_schema:
                return json.dumps({
                    "success": False,
                    "error": f"Tool schema not found for '{tool_name}'"
                })
            
            # Prepare parameters intelligently
            prepared_params = self.prepare_parameters(
                tool_schema=tool_schema,
                action_input=params,
                execution_context=context
            )
            
            # Execute the tool
            execution_result = self.execute_tool(
                tool_name=tool_name,
                parameters=prepared_params,
                execution_context=context
            )
            
            return json.dumps(execution_result, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            })



    def prepare_parameters(self, tool_schema: Dict[str, Any], action_input: Dict[str, Any], 
                         execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Intelligently prepare parameters for tool execution
        
        Args:
            tool_schema: Complete tool schema with parameter definitions
            action_input: Raw parameters from ReAct action
            execution_context: Current execution context (e.g., ifc_file_path)
            
        Returns:
            Prepared parameters ready for tool execution
        """
        # Start with action input
        prepared_params = action_input.copy()
        
        # Add context parameters if available and needed
        if execution_context:
            # Add IFC file path if tool requires it and it's available
            if execution_context.get('ifc_file_path'):
                function_params = tool_schema.get('function', {}).get('parameters', {})
                properties = function_params.get('properties', {})
                
                # Check if tool expects ifc_file_path parameter
                if 'ifc_file_path' in properties and 'ifc_file_path' not in prepared_params:
                    prepared_params['ifc_file_path'] = execution_context['ifc_file_path']
            
            # Add other context parameters as needed
            for context_key in ['current_step_index', 'session_id']:
                if context_key in execution_context and context_key in properties:
                    if context_key not in prepared_params:
                        prepared_params[context_key] = execution_context[context_key]
        
        # Validate required parameters
        self._validate_parameters(tool_schema, prepared_params)
        
        return prepared_params
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                    execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a tool with comprehensive error handling and result formatting
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for tool execution
            execution_context: Current execution context
            
        Returns:
            Standardized execution result
        """
        try:
            # Check if tool exists
            if tool_name not in self.tool_registry.get_available_tools():
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found in tool registry",
                    "tool_name": tool_name,
                    "available_tools": self.tool_registry.get_available_tools(),
                    "critical_failure": False
                }
            
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
            tool_responses = self.tool_registry.execute_tool_calls([tool_call])
            
            if tool_call_id in tool_responses:
                result = tool_responses[tool_call_id]
                
                return {
                    "success": True,
                    "tool_name": tool_name,
                    "parameters_used": parameters,
                    "result": result,
                    "execution_time": None  # TODO: Add timing if needed
                }
            else:
                return {
                    "success": False,
                    "error": f"Tool execution returned no result for '{tool_name}'",
                    "tool_name": tool_name,
                    "parameters_used": parameters,
                    "critical_failure": True
                }
                
        except Exception as e:
            error_msg = str(e)
            is_critical = "critical" in error_msg.lower()
            
            return {
                "success": False,
                "error": f"Tool execution failed: {error_msg}",
                "tool_name": tool_name,
                "parameters_used": parameters,
                "critical_failure": is_critical,
                "exception_type": type(e).__name__
            }
    
    def execute_special_action(self, action_name: str, action_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle special actions that don't correspond to domain tools
        
        Args:
            action_name: Name of the special action
            action_input: Input for the special action
            
        Returns:
            Execution result for the special action
        """
        if action_name == "final_answer":
            return {
                "success": True,
                "result": action_input,
                "is_final": True,
                "action_type": "final_answer"
            }
        elif action_name == "no_action":
            return {
                "success": True,
                "result": {"message": "No action required"},
                "is_final": False,
                "action_type": "no_action"
            }
        else:
            return {
                "success": False,
                "error": f"Unknown special action: {action_name}",
                "action_type": "unknown"
            }
    
    def execute_action(self, action_name: str, action_input: Dict[str, Any], 
                      execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Universal action execution - handles both special actions and tool execution
        
        Args:
            action_name: Name of the action/tool to execute
            action_input: Parameters for the action
            execution_context: Current execution context
            
        Returns:
            Standardized execution result
        """
        # Handle special actions first
        special_actions = {"final_answer", "no_action"}
        if action_name in special_actions:
            return self.execute_special_action(action_name, action_input)
        
        # Handle regular tool execution
        return self.execute_tool(action_name, action_input, execution_context)
    
    def format_observation(self, action_result: Dict[str, Any]) -> str:
        """
        Format action execution result into a readable observation
        
        Args:
            action_result: Result from action execution
            
        Returns:
            Formatted observation string for ReAct loop
        """
        if action_result.get("is_final", False):
            return f"Task completed successfully with final answer: {action_result.get('result', {})}"
        
        if action_result.get("success", False):
            tool_name = action_result.get("tool_name", "unknown")
            result = action_result.get("result", {})
            
            # Format result based on type
            if isinstance(result, dict):
                if "error" in result:
                    return f"Tool '{tool_name}' executed but returned error: {result.get('error', 'Unknown error')}"
                elif "result" in result and "data" in result:
                    return f"Tool '{tool_name}' executed successfully. Status: {result.get('result', 'unknown')}, Data: {len(result.get('data', []))} items found"
                elif isinstance(result.get("data"), list):
                    return f"Tool '{tool_name}' found {len(result['data'])} items"
                else:
                    return f"Tool '{tool_name}' executed successfully: {str(result)[:200]}..."
            else:
                return f"Tool '{tool_name}' executed successfully: {str(result)[:200]}..."
        else:
            error = action_result.get("error", "Unknown error")
            tool_name = action_result.get("tool_name", "unknown")
            return f"Tool '{tool_name}' failed: {error}"
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tool execution
        
        Returns:
            Dictionary containing execution statistics
        """
        # TODO: Implement execution statistics tracking
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0
        }
    
    def _validate_parameters(self, tool_schema: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        """
        Validate that required parameters are present
        
        Args:
            tool_schema: Complete tool schema
            parameters: Parameters to validate
            
        Raises:
            ValueError: If required parameters are missing
        """
        function_schema = tool_schema.get('function', {})
        param_schema = function_schema.get('parameters', {})
        required_params = param_schema.get('required', [])
        
        missing_params = [param for param in required_params if param not in parameters]
        if missing_params:
            tool_name = function_schema.get('name', 'unknown')
            raise ValueError(f"Missing required parameters for tool '{tool_name}': {missing_params}")
    
   
   