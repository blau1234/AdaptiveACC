
import os
import json
import importlib.util
from typing import Dict, List
from pathlib import Path
from toolregistry import ToolRegistry


class PersistentToolStorage:
    """Handle saving and loading of categorized tools"""
    
    def __init__(self, storage_dir: str = "tools"):
        self.base_dir = Path(storage_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Metadata file to track all tools
        self.metadata_file = self.base_dir / "metadata.json"
        
        # Ensure category directories exist
        self.categories = ["builtin", "ifcopenshell", "mcp", "openapi", "langchain"]
        for category in self.categories:
            (self.base_dir / category).mkdir(exist_ok=True)
        
    def save_tool(self, tool_name: str, code: str, description: str = "", category: str = "builtin") -> bool:
        """
        Save a tool to categorized filesystem storage
        
        Args:
            tool_name: Name of the tool
            code: Python code of the tool function
            description: Optional description
            category: Tool category (builtin, ifcopenshell, mcp, etc.)
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate category
            if category not in self.categories:
                category = "builtin"  # Default fallback
                
            # Save the code to categorized directory
            category_dir = self.base_dir / category
            tool_file = category_dir / f"{tool_name}.py"
            
            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f'"""\nTool: {tool_name}\nCategory: {category}\nDescription: {description}\n"""\n\n')
                f.write(code)
            
            # Update metadata
            self._update_metadata(tool_name, description, category)
            
            return True
            
        except Exception as e:
            print(f"Failed to save tool {tool_name}: {e}")
            return False
    
    def load_all_tools(self, registry: ToolRegistry) -> int:
        """
        Load all saved tools from all categories into the registry
        
        Args:
            registry: ToolRegistry instance to load tools into
            
        Returns:
            int: Number of tools loaded
        """
        loaded_count = 0
        
        try:
            # Load tools from each category directory
            for category in self.categories:
                category_loaded = self._load_tools_from_category(registry, category)
                loaded_count += category_loaded
                    
        except Exception as e:
            print(f"Error loading tools: {e}")
            
        return loaded_count
    
    def _load_tools_from_category(self, registry: ToolRegistry, category: str) -> int:
        """Load all tools from a specific category directory"""
        loaded_count = 0
        category_dir = self.base_dir / category
        
        if not category_dir.exists():
            return 0
            
        # Create a category class for namespace
        category_class_name = f"{category.capitalize()}Tools"
        category_tools = {}
        
        try:
            # Load all .py files in category directory
            for tool_file in category_dir.glob("*.py"):
                tool_name = tool_file.stem
                
                # Load the module dynamically
                spec = importlib.util.spec_from_file_location(tool_name, tool_file)
                if spec is None or spec.loader is None:
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find functions in the module (only user-defined ones)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (callable(attr) and 
                        not attr_name.startswith('_') and 
                        hasattr(attr, '__module__') and 
                        attr.__module__ == tool_name):  # Only functions defined in this module
                        category_tools[attr_name] = attr
                        loaded_count += 1
        
            # Register tools with namespace if any were found
            if category_tools:
                # Create dynamic class with tools as static methods
                dynamic_class = type(category_class_name, (), {})
                for name, func in category_tools.items():
                    setattr(dynamic_class, name, staticmethod(func))
                
                # Register class with namespace
                registry.register_from_class(dynamic_class, with_namespace=True)
                
        except Exception as e:
            print(f"Error loading tools from {category}: {e}")
            
        return loaded_count
    
    def _update_metadata(self, tool_name: str, description: str, category: str):
        """Update the tools metadata file"""
        metadata = {}
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception:
                pass
        
        metadata[tool_name] = {
            "description": description,
            "category": category,
            "created_at": __import__("datetime").datetime.now().isoformat()
        }
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def list_saved_tools(self) -> List[Dict]:
        """List all saved tools with metadata"""
        if not self.metadata_file.exists():
            return []
            
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            return [
                {
                    "name": name,
                    "description": info.get("description", ""),
                    "created_at": info.get("created_at", "")
                }
                for name, info in metadata.items()
            ]
        except Exception:
            return []
    
    def delete_tool(self, tool_name: str, category: str = None) -> bool:
        """Delete a saved tool"""
        try:
            # If category not specified, search all categories
            if category is None:
                for cat in self.categories:
                    tool_file = self.base_dir / cat / f"{tool_name}.py"
                    if tool_file.exists():
                        tool_file.unlink()
                        break
            else:
                tool_file = self.base_dir / category / f"{tool_name}.py"
                if tool_file.exists():
                    tool_file.unlink()
            
            # Update metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                if tool_name in metadata:
                    del metadata[tool_name]
                    
                with open(self.metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to delete tool {tool_name}: {e}")
            return False


def create_persistent_tool_registry(storage_dir: str = "tools") -> ToolRegistry:
    """
    Create a ToolRegistry with persistent storage capability
    
    This function:
    1. Creates a standard ToolRegistry
    2. Registers built-in tools
    3. Loads any previously saved tools
    4. Returns the registry with all tools available
    """
    from .tool_registry import register_builtin_tools
    
    # Create registry and add built-in tools
    registry = ToolRegistry()
    register_builtin_tools(registry)
    
    # Load saved tools
    storage = PersistentToolStorage(storage_dir)
    loaded_count = storage.load_all_tools(registry)
    
    if loaded_count > 0:
        print(f"Loaded {loaded_count} saved tools from {storage_dir}")
    
    return registry


# Usage example
if __name__ == "__main__":
    # Create persistent registry
    registry = create_persistent_tool_registry()
    print(f"Registry has {len(registry.get_available_tools())} tools")
    print("Available tools:", registry.get_available_tools())
    
    # Example of saving a new tool
    storage = PersistentToolStorage()
    sample_code = '''
def example_persistent_tool(param: str) -> dict:
    """Example tool that will be saved"""
    return {"result": "pass", "detail": f"Processed: {param}"}
'''
    
    storage.save_tool("example_persistent_tool", sample_code, "Example persistent tool", "ifcopenshell")
    print("Tool saved. Restart the script to see it loaded automatically.")