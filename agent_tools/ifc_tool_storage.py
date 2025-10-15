import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from utils.rag_tool import ToolVectorManager
from models.common_models import AgentToolResult, ToolMetadata
from models.shared_context import SharedContext
from telemetry.tracing import trace_method
from opentelemetry import trace


class ToolStorage:
    """Skill to store new tools with filesystem and vector DB persistence"""

    def __init__(self):
        from ifc_tools.ifc_tool_registry import IFCToolRegistry
        # Agent-created tools are stored in ifc_tools/generated/
        self.base_dir = Path("ifc_tools/generated")
        # Note: Directory created on-demand in store_tool() method, not here
        self.metadata_file = self.base_dir / "metadata.json"
        self.tool_registry = IFCToolRegistry.get_instance()


    def _get_tool_file_path(self, category: str, ifc_tool_name: str) -> str:
        """Get standardized tool file path for generated tools"""
        return str(self.base_dir / category / f"{ifc_tool_name}.py")
    
    # Executor Interface
    @trace_method("store_ifc_tool")
    def store_ifc_tool(self, ifc_tool_name: str) -> AgentToolResult:
        """Store a validated IFC tool for future use in filesystem and vector database.

        Retrieves a successfully created or fixed tool from SharedContext and
        persists it to the IFC tools directory and vector database for future
        semantic retrieval and use.

        Args:
            ifc_tool_name: Name of the IFC tool to store

        Returns:
            AgentToolResult: Success if tool stored successfully, failure otherwise
        """

        span = trace.get_current_span()

        try:
            # Record tool being stored
            span.set_attribute("store_ifc_tool.ifc_tool_name", ifc_tool_name)

            # Get tool information from SharedContext
            shared_context = SharedContext.get_instance()
            tool_result = shared_context.get_tool_by_name(ifc_tool_name)

            if not tool_result:
                span.set_attribute("store_ifc_tool.success", False)
                span.set_attribute("store_ifc_tool.error", f"Tool '{ifc_tool_name}' not found in SharedContext")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="store_ifc_tool",
                    error=f"IFC tool '{ifc_tool_name}' not found in SharedContext. Make sure the tool was created or fixed successfully."
                )
                return result

            # Extract tool information (tool_result is a dict from agent_history)
            code = tool_result.get('code')
            metadata_dict = tool_result.get('metadata')

            # Convert metadata dict to ToolMetadata object if needed
            if metadata_dict:
                if isinstance(metadata_dict, dict):
                    metadata = ToolMetadata(**metadata_dict)
                else:
                    metadata = metadata_dict
            else:
                metadata = None

            description = metadata.description if metadata else ""
            category = metadata.category if metadata else "uncategorized"

            # Record tool details
            span.set_attribute("store_ifc_tool.category", category)
            span.set_attribute("store_ifc_tool.description", description)

            # Store the tool with complete metadata
            success = self.store_tool(ifc_tool_name, code, description, category, metadata)

            if success:
                result_data = {
                    "success": True,
                    "ifc_tool_name": ifc_tool_name,
                    "category": category,
                    "file_path": self._get_tool_file_path(category, ifc_tool_name),
                    "stored_at": datetime.now().isoformat(),
                    "vector_db_indexed": ToolVectorManager.get_instance().is_available(),
                    "description": description
                }

                # Record successful storage
                span.set_attribute("store_ifc_tool.success", True)
                span.set_attribute("store_ifc_tool.file_path", result_data["file_path"])
                span.set_attribute("store_ifc_tool.vector_db_indexed", result_data["vector_db_indexed"])

                result = AgentToolResult(
                    success=True,
                    agent_tool_name="store_ifc_tool",
                    result=result_data
                )
                return result
            else:
                span.set_attribute("store_ifc_tool.success", False)
                span.set_attribute("store_ifc_tool.error", f"Failed to store IFC tool '{ifc_tool_name}'")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="store_ifc_tool",
                    error=f"Failed to store IFC tool '{ifc_tool_name}'"
                )
                return result

        except Exception as e:
            span.set_attribute("store_ifc_tool.success", False)
            span.set_attribute("store_ifc_tool.error", str(e))
            result = AgentToolResult(
                success=False,
                agent_tool_name="store_ifc_tool",
                error=f"IFC tool storage failed: {str(e)}"
            )
            return result


    def store_tool(self, ifc_tool_name: str, code: str, description: str,
                   category: str, metadata: ToolMetadata) -> bool:
        """Store tool with coordinated filesystem, vector DB and metadata management"""

        try:
            # Step 1: Save to filesystem using persistent storage with complete metadata
            filesystem_success = self._save_to_filesystem(ifc_tool_name, code, description, category, metadata)

            if not filesystem_success:
                print(f"Failed to save {ifc_tool_name} to filesystem")
                return False

            # Step 2: Update vector database if available
            vector_success = True
            vector_db = ToolVectorManager.get_instance()
            if vector_db.is_available():
                vector_success = self._add_to_vector_db(ifc_tool_name, metadata)
                if not vector_success:
                    print(f"Warning: Failed to add {ifc_tool_name} to vector database")
        
            # Metadata is already written to disk in _save_to_filesystem
            print(f"Successfully stored tool: {ifc_tool_name} (filesystem: {filesystem_success}, vector: {vector_success})")
            return True

        except Exception as e:
            print(f"Error storing tool {ifc_tool_name}: {e}")
            return False


    def _save_to_filesystem(self, ifc_tool_name: str, code: str, description: str, category: str, metadata: ToolMetadata) -> bool:
        """Save tool to categorized filesystem storage with complete metadata"""
        try:
            # Ensure base directory exists (lazy creation)
            self.base_dir.mkdir(parents=True, exist_ok=True)

            # Create category directory and get tool file path
            category_dir = self.base_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            tool_file = category_dir / f"{ifc_tool_name}.py"

            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f'"""\nTool: {ifc_tool_name}\nCategory: {category}\nDescription: {description}\n"""\n\n')
                f.write(code)

            # Prepare complete metadata with creation source
            # Note: ifc_tool_name is now included in metadata.model_dump()
            complete_metadata = {
                **metadata.model_dump(),
                'file_path': str(tool_file),
                'created_at': datetime.now().isoformat(),
                'creation_source': 'agent'  # Mark as agent-generated
            }

            # Save metadata to JSON file directly
            all_metadata = {}
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)

            all_metadata[ifc_tool_name] = complete_metadata

            # Ensure parent directory exists
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_metadata, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Failed to save tool {ifc_tool_name}: {e}")
            return False
    
    
    def _add_to_vector_db(self, ifc_tool_name: str, metadata: ToolMetadata) -> bool:
        """Add tool to vector database for semantic search"""
        try:
            # Prepare metadata for vector DB storage with creation source
            # Note: ifc_tool_name is now included in metadata.model_dump()
            tool_metadata = {
                **metadata.model_dump(),
                'creation_source': 'agent',  # Mark as agent-generated
                'created_at': datetime.now().isoformat()
            }

            # Use vector database's add_tool method
            return ToolVectorManager.get_instance().add_tool(tool_metadata)
            
        except Exception as e:
            print(f"Vector database storage error: {e}")
            return False


 