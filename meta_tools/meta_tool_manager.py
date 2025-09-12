from typing import List, Dict, Any
from toolregistry import ToolRegistry
from .tool_selection import ToolSelector
from .tool_execution import ToolExecutor
from .tool_registration import ToolRegistrar
from .tool_storage import ToolStorage
from .tool_creation.tool_creator import ToolCreatorAgent


class MetaToolManager:
    """
    Simplified Meta Tool Manager that initializes meta tool components
    and provides registration functionality to MetaToolRegistry
    """
    
    def __init__(self, domain_tool_registry: ToolRegistry, tool_vector_db=None, 
                 storage_dir: str = "tools", vectordb_path: str = "vectordb/docs"):
        self.domain_tool_registry = domain_tool_registry
        self.tool_vector_db = tool_vector_db
        self.shared_context = None  # Will be set by coordinator if available
        
        # Initialize all meta tool components
        self.tool_selector = ToolSelector(domain_tool_registry, tool_vector_db)
        self.tool_executor = ToolExecutor(domain_tool_registry)
        self.tool_registrar = ToolRegistrar(domain_tool_registry)
        self.tool_storage = ToolStorage(domain_tool_registry, storage_dir, tool_vector_db)
        self.tool_creator = ToolCreatorAgent(
            vectordb_path=vectordb_path,
            tool_vector_db=tool_vector_db
        )
    
    def set_shared_context(self, shared_context) -> None:
        """Set shared context for meta tools that need it"""
        self.shared_context = shared_context
        # Pass to components that might need context
        if hasattr(self.tool_creator, 'set_shared_context'):
            self.tool_creator.set_shared_context(shared_context)
    
    def get_context_for_tools(self) -> Dict[str, Any]:
        """Get context information for meta tools"""
        if self.shared_context:
            return {
                "session_info": self.shared_context.session_info,
                "current_state": self.shared_context.current_state,
                "recent_results": self.shared_context.execution_summary[-5:] if self.shared_context.execution_summary else []
            }
        return {}
    
    
    # Meta Tool Registration
    def register_meta_tools_to_registry(self, meta_registry) -> List[str]:
        """
        Register all 5 meta tool executor interfaces to the ToolRegistry
        
        Args:
            meta_registry: ToolRegistry instance to register the meta tools to
            
        Returns:
            List of registered meta tool names
        """
        # The 5 core meta tool interfaces
        meta_tool_interfaces = [
            self.tool_selector.tool_selection,
            self.tool_creator.tool_creation,
            self.tool_executor.tool_execution,
            self.tool_registrar.tool_registration,
            self.tool_storage.tool_storage
        ]
        
        registered_names = []
        for tool_func in meta_tool_interfaces:
            try:
                meta_registry.register(tool_func)
                registered_names.append(tool_func.__name__)
            except Exception as e:
                print(f"Failed to register meta tool interface {tool_func.__name__}: {e}")
        
        print(f"Registered {len(registered_names)} meta tools to ToolRegistry")
        return registered_names
    
    
    # Meta Tool Descriptions (for Executor prompt)
    @staticmethod
    def get_meta_tools_description() -> str:
        """Get hardcoded meta tools description for Executor's ReAct prompt"""
        return """Available meta tools:

        ### tool_selection
        - **Description**: Search and select the best domain tool for a given task using semantic search and LLM reasoning
        - **Parameters**:
        - step_description (string) (required): Clear description of the task or step that needs a domain tool
        - execution_context (string) (optional): JSON context containing execution details like ifc_file_path

        ### tool_creation
        - **Description**: Create a new domain tool when no existing tool can handle the current task
        - **Parameters**:
        - step_description (string) (required): Detailed description of what the new tool should accomplish
        - step_id (string) (optional): Identifier for the step, defaults to "auto_generated"

        ### tool_execution
        - **Description**: Execute a specific domain tool with given parameters for building compliance tasks
        - **Parameters**:
        - tool_name (string) (required): Name of the domain tool to execute
        - parameters (string) (required): JSON string of parameters required by the domain tool
        - execution_context (string) (optional): JSON context with ifc_file_path and other execution details

        ### tool_registration
        - **Description**: Register a newly created tool to the domain tool registry for future use
        - **Parameters**:
        - tool_code (string) (required): Complete source code of the tool function to register
        - tool_name (string) (required): Name of the tool to register
        - metadata (string) (optional): JSON metadata including description and category, defaults to "{}"

        ### tool_storage
        - **Description**: Store a tool for future use with metadata and semantic search capabilities
        - **Parameters**:
        - tool_name (string) (required): Name of the tool to store
        - code (string) (required): Source code of the tool to store
        - description (string) (optional): Description of what the tool does
        - category (string) (optional): Category classification, defaults to "general"
        - tags (string) (optional): Comma-separated tags for searchability, defaults to ""

        """