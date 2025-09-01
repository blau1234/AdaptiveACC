
from typing import Dict, List, Any, Optional
from toolregistry import ToolRegistry
from utils.ifc_parser import IFCParser


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register core building-specific tools from builtin directory"""
    from tools.persistent_tool_storage import PersistentToolStorage
    
    # Use PersistentToolStorage to load builtin tools with namespace
    storage = PersistentToolStorage()
    builtin_loaded = storage._load_tools_from_category(registry, "builtin")
    
    if builtin_loaded == 0:
        print("Warning: No builtin tools found in tools/builtin/ directory")
    else:
        print(f"Loaded {builtin_loaded} builtin tools with namespace")


def register_from_code(registry: ToolRegistry, code: str, tool_name: str) -> bool:
    """
    Register a tool from generated code string - minimal implementation
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create execution environment
        exec_globals = {
            '__builtins__': __builtins__,
            'IFCParser': IFCParser,
        }
        exec_locals = {}
        
        # Execute the code
        exec(code, exec_globals, exec_locals)
        
        # Find the function
        func = None
        for name, obj in exec_locals.items():
            if callable(obj) and not name.startswith('_'):
                func = obj
                break
        
        if func is None:
            print(f"No function found in code for {tool_name}")
            return False
        
        # Register directly
        registry.register(func)
        return True
        
    except Exception as e:
        print(f"Failed to register {tool_name}: {e}")
        return False


def create_building_tool_registry(enable_persistence: bool = True) -> ToolRegistry:
    """
    Create a ToolRegistry instance with categorized building tools
    
    Args:
        enable_persistence: Whether to load previously saved categorized tools
    
    Uses ToolRegistry namespace features for organized tool management
    """
    registry = ToolRegistry()
    
    # Register built-in tools with namespace
    register_builtin_tools(registry)
    
    # Load persistent tools from all categories if enabled
    if enable_persistence:
        try:
            from .persistent_tool_storage import PersistentToolStorage
            storage = PersistentToolStorage()
            loaded_count = storage.load_all_tools(registry)
            if loaded_count > 0:
                print(f"Loaded {loaded_count} categorized tools")
        except Exception as e:
            print(f"Failed to load persistent tools: {e}")
    
    return registry


# Example usage - much cleaner!
if __name__ == "__main__":
    # Create registry directly
    registry = create_building_tool_registry()
    
    # Use all ToolRegistry features directly
    print("Available tools:", registry.get_available_tools())
    print("Schema:", registry.get_tools_json(api_format="openai-chatcompletion"))
    
    # Register new tools easily
    sample_code = '''
def test_tool(ifc_file_path: str) -> dict:
    return {"result": "pass", "detail": "test"}
'''
    
    if register_from_code(registry, sample_code, "test_tool"):
        print("New tool registered successfully!")
        print("Updated tools:", registry.get_available_tools())