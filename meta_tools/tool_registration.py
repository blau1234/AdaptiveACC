import ast
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable
from toolregistry import ToolRegistry


class ToolRegistrar:
    """
    Meta Tool for intelligent tool registration with validation and conflict detection
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.registered_tools = {}  # Track registered tools with metadata
    

    # Executor Interface
    def tool_registration(self, tool_code: str, tool_name: str, metadata: str = "{}") -> str:
        """
        Executor interface for registering a tool from code
        
        Args:
            tool_code: Python code string containing the tool function
            tool_name: Name of the tool to register
            metadata: JSON string with tool metadata
            
        Returns:
            JSON string with registration result
        """
        try:
            # Parse metadata
            try:
                meta_dict = json.loads(metadata) if metadata else {}
            except:
                meta_dict = {}
            
            print(f"ToolRegistrar: Registering tool '{tool_name}'")
            
            # Register the tool
            success = self.register_from_code(tool_code, tool_name, meta_dict)
            
            if success:
                # Get validation info
                validation_result = self.validate_tool_compatibility(tool_name)
                
                result = {
                    "success": True,
                    "tool_name": tool_name,
                    "registration_time": self.registered_tools[tool_name]["registration_time"],
                    "validation": validation_result,
                    "available_in_registry": tool_name in self.tool_registry.get_available_tools()
                }
                
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to register tool '{tool_name}'",
                    "tool_name": tool_name
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool registration failed: {str(e)}",
                "tool_name": tool_name
            })

    def register_from_code(self, code: str, tool_name: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a tool from code string with validation and conflict detection
        
        Args:
            code: Python code string containing the tool function
            tool_name: Name of the tool to register
            metadata: Optional metadata about the tool
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate code syntax first
            validation_result = self._validate_code_syntax(code)
            if not validation_result["valid"]:
                print(f"Code validation failed for {tool_name}: {validation_result['error']}")
                return False
            
            # Check for naming conflicts
            if self._has_naming_conflict(tool_name):
                print(f"Naming conflict detected for {tool_name}")
                return False
            
            # Use the existing registration function from domain_tools.tool_registry
            from domain_tools.tool_registry import register_from_code
            success = register_from_code(self.tool_registry, code, tool_name)
            
            if success:
                # Track the registered tool
                self._track_registered_tool(tool_name, code, metadata)
                print(f"Successfully registered tool: {tool_name}")
                return True
            else:
                print(f"Failed to register tool: {tool_name}")
                return False
                
        except Exception as e:
            print(f"Error during tool registration for {tool_name}: {e}")
            return False
    
    def register_function(self, func: Callable, tool_name: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a function directly as a tool
        
        Args:
            func: Python function to register as a tool
            tool_name: Optional custom name for the tool (defaults to function name)
            metadata: Optional metadata about the tool
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            actual_name = tool_name or func.__name__
            
            # Check for naming conflicts
            if self._has_naming_conflict(actual_name):
                print(f"Naming conflict detected for function {actual_name}")
                return False
            
            # Register directly with ToolRegistry
            self.tool_registry.register(func)
            
            # Track the registered tool
            self._track_registered_tool(actual_name, None, metadata, func)
            print(f"Successfully registered function as tool: {actual_name}")
            return True
            
        except Exception as e:
            print(f"Error during function registration for {func.__name__}: {e}")
            return False
    
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered tool
        
        Args:
            tool_name: Name of the tool to get info for
            
        Returns:
            Tool information dictionary or None if not found
        """
        if tool_name in self.registered_tools:
            return self.registered_tools[tool_name].copy()
        return None
    
    def list_registered_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools registered through this registrar
        
        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": name,
                "registration_time": info.get("registration_time"),
                "has_metadata": info.get("metadata") is not None,
                "source": info.get("source", "unknown")
            }
            for name, info in self.registered_tools.items()
        ]
    
    def validate_tool_compatibility(self, tool_name: str) -> Dict[str, Any]:
        """
        Validate that a tool is compatible with the system
        
        Args:
            tool_name: Name of the tool to validate
            
        Returns:
            Validation result dictionary
        """
        try:
            # Check if tool exists in registry
            available_tools = self.tool_registry.get_available_tools()
            if tool_name not in available_tools:
                return {
                    "valid": False,
                    "error": f"Tool {tool_name} not found in registry",
                    "available_tools": available_tools
                }
            
            # Get tool schema to validate structure
            try:
                tools_schema = self.tool_registry.get_tools_json()
                tool_schema = None
                for schema in tools_schema:
                    if schema.get("function", {}).get("name") == tool_name:
                        tool_schema = schema
                        break
                
                if not tool_schema:
                    return {
                        "valid": False,
                        "error": f"Schema not found for tool {tool_name}"
                    }
                
                # Validate schema structure
                function_info = tool_schema.get("function", {})
                if not function_info.get("name") or not function_info.get("parameters"):
                    return {
                        "valid": False,
                        "error": f"Invalid schema structure for tool {tool_name}"
                    }
                
                return {
                    "valid": True,
                    "schema": tool_schema,
                    "parameter_count": len(function_info.get("parameters", {}).get("properties", {}))
                }
                
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Schema validation failed: {e}"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": f"Compatibility check failed: {e}"
            }
    
    def _validate_code_syntax(self, code: str) -> Dict[str, Any]:
        """
        Validate Python code syntax
        
        Args:
            code: Python code string to validate
            
        Returns:
            Validation result dictionary
        """
        try:
            # Parse the code to check syntax
            ast.parse(code)
            
            # Check if code contains at least one function definition
            tree = ast.parse(code)
            has_function = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
            
            if not has_function:
                return {
                    "valid": False,
                    "error": "Code must contain at least one function definition"
                }
            
            return {
                "valid": True,
                "syntax_check": "passed"
            }
            
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"Syntax error: {e.msg} at line {e.lineno}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Code validation error: {e}"
            }
    
    def _has_naming_conflict(self, tool_name: str) -> bool:
        """
        Check if a tool name conflicts with existing tools
        
        Args:
            tool_name: Name to check for conflicts
            
        Returns:
            True if there's a conflict, False otherwise
        """
        existing_tools = self.tool_registry.get_available_tools()
        return tool_name in existing_tools
    
    def _track_registered_tool(self, tool_name: str, code: Optional[str], 
                             metadata: Optional[Dict[str, Any]], 
                             func: Optional[Callable] = None) -> None:
        """
        Track a registered tool with metadata
        
        Args:
            tool_name: Name of the registered tool
            code: Code string (if registered from code)
            metadata: Tool metadata
            func: Function object (if registered from function)
        """
        from datetime import datetime
        
        # Generate code hash for tracking changes
        code_hash = None
        if code:
            code_hash = hashlib.md5(code.encode()).hexdigest()
        
        self.registered_tools[tool_name] = {
            "name": tool_name,
            "registration_time": datetime.now().isoformat(),
            "code_hash": code_hash,
            "metadata": metadata or {},
            "source": "code" if code else "function",
            "function_ref": func
        }
    
  
       