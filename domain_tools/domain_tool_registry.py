from pathlib import Path
from toolregistry import ToolRegistry
import importlib.util
from utils.base_classes import Singleton


class DomainToolRegistry(Singleton):
    """Singleton Domain Tool Registry for global access to domain tools"""

    def _initialize(self):
        self.registry = ToolRegistry()
        self._register_domain_tools()
        print("DomainToolRegistry: Singleton instance initialized")
    
    # Removed duplicate get_instance method - inherited from Singleton base class
    
    def _register_domain_tools(self):
        """Register all domain tools from all discovered categories using importlib"""
       
        tools_base_dir = Path("domain_tools")
        if not tools_base_dir.exists():
            print("Warning: No domain_tools directory found at domain_tools/")
            return
        
        total_loaded = 0
        discovered_categories = []
        
        # Dynamically discover all category directories
        for category_dir in tools_base_dir.iterdir():
            if (category_dir.is_dir() and 
                not category_dir.name.startswith('.') and 
                category_dir.name != '__pycache__'):
                
                category_name = category_dir.name
                discovered_categories.append(category_name)
                
                category_loaded = self._load_tools_from_category(category_name)
                if category_loaded > 0:
                    print(f"DomainToolRegistry: Loaded {category_loaded} tools from {category_name} category")
                    total_loaded += category_loaded
        
        if not discovered_categories:
            print("Warning: No tool categories discovered in tools/ directory")
        elif total_loaded == 0:
            print(f"Warning: No domain tools were successfully loaded from {len(discovered_categories)} categories: {discovered_categories}")
        else:
            print(f"DomainToolRegistry: Total loaded {total_loaded} domain tools from {len(discovered_categories)} categories: {discovered_categories}")
    
    def _load_tools_from_category(self, category: str) -> int:
        """Load all tools from a specific category directory"""
        
        category_dir = Path("domain_tools") / category
        loaded_count = 0
        
        if not category_dir.exists():
            # Not all categories may exist, this is normal
            return 0
            
        for tool_file in category_dir.glob("*.py"):
            tool_name = tool_file.stem
            try:
                # Use importlib to load the module
                spec = importlib.util.spec_from_file_location(
                    f"{category}_{tool_name}", tool_file
                )
                if spec is None or spec.loader is None:
                    print(f"Warning: Could not create spec for {category}/{tool_name}")
                    continue
                    
                module = importlib.util.module_from_spec(spec)
               
                spec.loader.exec_module(module)
                
                # Find and register the tool function
                tool_registered = False
                for attr_name in dir(module):
                    if attr_name.startswith('_'):
                        continue
                        
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, '__doc__'):
                        # Register the function directly
                        self.registry.register(attr)
                        loaded_count += 1
                        tool_registered = True
                        print(f"Loaded {category} tool: {tool_name} (function: {attr_name})")
                        break
                
                if not tool_registered:
                    print(f"Warning: No valid function found in {category}/{tool_name}")
                    
            except Exception as e:
                print(f"Failed to load {category} tool {tool_name}: {e}")
        
        return loaded_count
    
    # Proxy methods to underlying ToolRegistry
    def get_available_tools(self):
        """Get list of available tool names"""
        return self.registry.get_available_tools()
    
    def get_tools_json(self, api_format="openai-chatcompletion"):
        """Get tools schema in JSON format"""
        return self.registry.get_tools_json(api_format=api_format)
    
    def execute_tool_calls(self, tool_calls):
        """Execute tool calls"""
        return self.registry.execute_tool_calls(tool_calls)
    
    def register(self, func):
        """Register a new tool function"""
        return self.registry.register(func)
    
    def get_tool(self, tool_name):
        """Get a specific tool by name"""
        return self.registry.get_tool(tool_name)      