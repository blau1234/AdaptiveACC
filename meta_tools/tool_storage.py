import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from utils.rag_tool import ToolVectorManager
from models.common_models import MetaToolResult, ToolMetadata
from models.shared_context import SharedContext


class ToolStorage:
    """Meta tool to store new tools with filesystem and vector DB persistence"""

    def __init__(self):
        from domain_tools.domain_tool_registry import DomainToolRegistry
        # Direct path management - simple and clear
        self.base_dir = Path("domain_tools")
        self.base_dir.mkdir(exist_ok=True)
        self.metadata_file = self.base_dir / "metadata.json"
        self.domain_registry = DomainToolRegistry.get_instance()

    
    def _get_tool_file_path(self, category: str, tool_name: str) -> str:
        """Get standardized tool file path"""
        return str(self.base_dir / category / f"{tool_name}.py")
    
    # Executor Interface
    def tool_storage(self, tool_name: str) -> MetaToolResult:
        """Store a validated tool from SharedContext for future use"""

        try:
            # Get tool information from SharedContext
            shared_context = SharedContext.get_instance()
            tool_result = shared_context.get_tool_by_name(tool_name)

            if not tool_result:
                result = MetaToolResult(
                    success=False,
                    meta_tool_name="tool_storage",
                    error=f"Tool '{tool_name}' not found in SharedContext. Make sure the tool was created or fixed successfully."
                )
                shared_context.meta_tool_trace.append(result)
                return result

            # Extract tool information
            code = tool_result.code
            metadata = tool_result.metadata
            description = metadata.description if metadata else ""
            category = metadata.category if metadata else "uncategorized"

            # Store the tool with complete metadata
            success = self.store_tool(tool_name, code, description, category, metadata)

            if success:
                result_data = {
                    "success": True,
                    "tool_name": tool_name,
                    "category": category,
                    "file_path": self._get_tool_file_path(category, tool_name),
                    "stored_at": datetime.now().isoformat(),
                    "vector_db_indexed": ToolVectorManager.get_instance().is_available(),
                    "description": description
                }

                result = MetaToolResult(
                    success=True,
                    meta_tool_name="tool_storage",
                    result=result_data
                )
                shared_context.meta_tool_trace.append(result)
                return result
            else:
                result = MetaToolResult(
                    success=False,
                    meta_tool_name="tool_storage",
                    error=f"Failed to store tool '{tool_name}'"
                )
                shared_context.meta_tool_trace.append(result)
                return result

        except Exception as e:
            result = MetaToolResult(
                success=False,
                meta_tool_name="tool_storage",
                error=f"Tool storage failed: {str(e)}"
            )
            shared_context = SharedContext.get_instance()
            shared_context.meta_tool_trace.append(result)
            return result


    def store_tool(self, tool_name: str, code: str, description: str,
                   category: str, metadata: ToolMetadata) -> bool:
        """Store tool with coordinated filesystem, vector DB and metadata management"""

        try:
            # Step 1: Save to filesystem using persistent storage with complete metadata
            filesystem_success = self._save_to_filesystem(tool_name, code, description, category, metadata)

            if not filesystem_success:
                print(f"Failed to save {tool_name} to filesystem")
                return False

            # Step 2: Update vector database if available
            vector_success = True
            vector_db = ToolVectorManager.get_instance()
            if vector_db.is_available():
                vector_success = self._add_to_vector_db(tool_name, metadata)
                if not vector_success:
                    print(f"Warning: Failed to add {tool_name} to vector database")
        
            # Metadata is already written to disk in _save_to_filesystem
            print(f"Successfully stored tool: {tool_name} (filesystem: {filesystem_success}, vector: {vector_success})")
            return True

        except Exception as e:
            print(f"Error storing tool {tool_name}: {e}")
            return False


    def _save_to_filesystem(self, tool_name: str, code: str, description: str, category: str, metadata: ToolMetadata) -> bool:
        """Save tool to categorized filesystem storage with complete metadata"""
        try:
            # Create category directory and get tool file path
            category_dir = self.base_dir / category
            category_dir.mkdir(exist_ok=True)
            tool_file = category_dir / f"{tool_name}.py"

            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f'"""\nTool: {tool_name}\nCategory: {category}\nDescription: {description}\n"""\n\n')
                f.write(code)

            # Prepare complete metadata
            complete_metadata = {
                **metadata.model_dump(),
                'tool_name': tool_name,
                'file_path': str(tool_file),
                'created_at': datetime.now().isoformat()
            }

            # Save metadata to JSON file directly
            all_metadata = {}
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)

            all_metadata[tool_name] = complete_metadata

            # Ensure parent directory exists
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_metadata, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Failed to save tool {tool_name}: {e}")
            return False
    
    
    def _add_to_vector_db(self, tool_name: str, metadata: ToolMetadata) -> bool:
        """Add tool to vector database for semantic search"""
        try:
            # Prepare metadata for vector DB storage
            tool_metadata = {
                'tool_name': tool_name,
                **metadata.model_dump()  
            }
            
            # Use vector database's add_tool method
            return ToolVectorManager.get_instance().add_tool(tool_metadata)
            
        except Exception as e:
            print(f"Vector database storage error: {e}")
            return False


 