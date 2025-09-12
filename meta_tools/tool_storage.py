import json
import os
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from toolregistry import ToolRegistry
from utils.rag_tool import ToolVectorManager


class ToolStorage:
    """
    Meta Tool for unified tool storage, combining persistent filesystem storage
    and vector database management
    """
    
    def __init__(self, tool_registry: ToolRegistry, storage_dir: str = "tools", 
                 tool_vector_db=None):
        self.tool_registry = tool_registry
        self.base_dir = Path(storage_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Use ToolVectorManager for tool vector operations, fallback to passed tool_vector_db
        if tool_vector_db is None:
            try:
                self.tool_vector_db = ToolVectorManager(vectordb_path="vectordb/tools", collection_name="tool_vectors")
            except Exception as e:
                print(f"Warning: Could not initialize tool vector database: {e}")
                self.tool_vector_db = None
        else:
            self.tool_vector_db = tool_vector_db
        
        # Metadata file to track all tools
        self.metadata_file = self.base_dir / "metadata.json"
        
        # Create initial category directories
        self.initial_categories = ["builtin", "ifcopenshell", "mcp", "openapi", "langchain"]
        for category in self.initial_categories:
            (self.base_dir / category).mkdir(exist_ok=True)
    
    
    # Executor Interface
    def tool_storage(self, tool_name: str, code: str, description: str = "",
                     category: str = "builtin", metadata: str = "{}") -> str:
        """
        Executor interface for storing a tool with both filesystem persistence and vector database indexing
        
        Args:
            tool_name: Name of the tool
            code: Python code of the tool function
            description: Tool description
            category: Tool category for organization
            metadata: JSON string with additional tool metadata
            
        Returns:
            JSON string with storage result
        """
        try:
            # Parse metadata
            try:
                meta_dict = json.loads(metadata) if metadata else {}
            except:
                meta_dict = {}
            
            print(f"ToolStorage: Storing tool '{tool_name}' in category '{category}'")
            
            # Store the tool
            success = self.store_tool(tool_name, code, description, category, meta_dict)
            
            if success:
                # Get storage info
                tool_metadata = self.get_tool_metadata(tool_name)
                
                result = {
                    "success": True,
                    "tool_name": tool_name,
                    "category": category,
                    "file_path": tool_metadata.get("file_path") if tool_metadata else f"tools/{category}/{tool_name}.py",
                    "stored_at": tool_metadata.get("created_at") if tool_metadata else datetime.now().isoformat(),
                    "vector_db_indexed": self.tool_vector_db is not None,
                    "description": description
                }
                
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to store tool '{tool_name}'",
                    "tool_name": tool_name,
                    "category": category
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool storage failed: {str(e)}",
                "tool_name": tool_name
            })


    def store_tool(self, tool_name: str, code: str, description: str = "", 
                  category: str = "builtin", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a tool with both filesystem persistence and vector database indexing
        
        Args:
            tool_name: Name of the tool
            code: Python code of the tool function
            description: Tool description
            category: Tool category for organization
            metadata: Additional tool metadata
            
        Returns:
            True if storage successful, False otherwise
        """
        try:
            # Step 1: Save to filesystem using persistent storage
            filesystem_success = self._save_to_filesystem(tool_name, code, description, category)
            
            if not filesystem_success:
                print(f"Failed to save {tool_name} to filesystem")
                return False
            
            # Step 2: Update vector database if available
            vector_success = True
            if self.tool_vector_db is not None:
                vector_success = self._add_to_vector_db(tool_name, code, description, category, metadata)
                if not vector_success:
                    print(f"Warning: Failed to add {tool_name} to vector database")
            
            # Step 3: Update unified metadata
            self._update_unified_metadata(tool_name, description, category, metadata)
            
            print(f"Successfully stored tool: {tool_name} (filesystem: {filesystem_success}, vector: {vector_success})")
            return filesystem_success
            
        except Exception as e:
            print(f"Error storing tool {tool_name}: {e}")
            return False
    
    def load_all_tools(self) -> int:
        """
        Load all stored tools back into the ToolRegistry
        
        Returns:
            Number of tools successfully loaded
        """
        try:
            loaded_count = 0
            
            # Load tools from all category directories
            for category_dir in self.base_dir.iterdir():
                if category_dir.is_dir():
                    category_name = category_dir.name
                    
                    # Load all .py files in the category
                    for tool_file in category_dir.glob("*.py"):
                        tool_name = tool_file.stem
                        
                        try:
                            # Read and execute the tool code
                            with open(tool_file, 'r', encoding='utf-8') as f:
                                tool_code = f.read()
                            
                            # Register tool using ToolRegistry's native method
                            from domain_tools.tool_registry import register_from_code
                            success = register_from_code(self.tool_registry, tool_code, tool_name)
                            
                            if success:
                                loaded_count += 1
                                print(f"Loaded tool: {tool_name} ({category_name})")
                            
                        except Exception as e:
                            print(f"Failed to load tool {tool_name} from {category_name}: {e}")
            
            print(f"Loaded {loaded_count} tools from storage")
            return loaded_count
            
        except Exception as e:
            print(f"Error loading tools: {e}")
            return 0
    
    def search_stored_tools(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for stored tools using vector database
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of matching tool metadata
        """
        if self.tool_vector_db is None:
            print("Vector database not available for search")
            return []
        
        try:
            results = self.tool_vector_db.search_tools(query, k=k)
            return results
        except Exception as e:
            print(f"Error searching tools: {e}")
            return []
    
    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool metadata dictionary or None if not found
        """
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                return all_metadata.get(tool_name)
            return None
        except Exception as e:
            print(f"Error getting metadata for {tool_name}: {e}")
            return None
    
    def list_stored_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all stored tools, optionally filtered by category
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool information
        """
        tools = []
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                
                for tool_name, metadata in all_metadata.items():
                    if category is None or metadata.get('category') == category:
                        tools.append({
                            'name': tool_name,
                            'category': metadata.get('category', 'unknown'),
                            'description': metadata.get('description', ''),
                            'created_at': metadata.get('created_at', ''),
                            'file_path': metadata.get('file_path', '')
                        })
            
            return sorted(tools, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            print(f"Error listing tools: {e}")
            return []
    
    def delete_tool(self, tool_name: str) -> bool:
        """
        Delete a tool from storage (filesystem and vector database)
        
        Args:
            tool_name: Name of the tool to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Get tool metadata first
            metadata = self.get_tool_metadata(tool_name)
            if not metadata:
                print(f"Tool {tool_name} not found in metadata")
                return False
            
            # Delete from filesystem
            category = metadata.get('category', 'builtin')
            tool_file = self.base_dir / category / f"{tool_name}.py"
            if tool_file.exists():
                tool_file.unlink()
                print(f"Deleted {tool_name} from filesystem")
            
            # Remove from vector database
            if self.tool_vector_db is not None:
                # TODO: Implement vector database deletion if supported
                print(f"Vector database deletion not implemented for {tool_name}")
            
            # Remove from unified metadata
            self._remove_from_metadata(tool_name)
            
            return True
            
        except Exception as e:
            print(f"Error deleting tool {tool_name}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored tools
        
        Returns:
            Statistics dictionary
        """
        try:
            stats = {
                "total_tools": 0,
                "categories": {},
                "vector_db_available": self.tool_vector_db is not None,
                "storage_directory": str(self.base_dir)
            }
            
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                
                stats["total_tools"] = len(all_metadata)
                
                # Count by category
                for metadata in all_metadata.values():
                    category = metadata.get('category', 'unknown')
                    stats["categories"][category] = stats["categories"].get(category, 0) + 1
            
            # Add vector database stats if available
            if self.tool_vector_db is not None:
                try:
                    vector_stats = self.tool_vector_db.get_stats()
                    stats["vector_db_stats"] = vector_stats
                except:
                    stats["vector_db_stats"] = {"error": "Unable to get vector DB stats"}
            
            return stats
            
        except Exception as e:
            return {"error": f"Unable to get storage stats: {e}"}
    
    def _save_to_filesystem(self, tool_name: str, code: str, description: str, category: str) -> bool:
        """Save tool to categorized filesystem storage"""
        try:
            # Create category directory if it doesn't exist
            category_dir = self.base_dir / category
            category_dir.mkdir(exist_ok=True)
            
            # Save the code to categorized directory
            tool_file = category_dir / f"{tool_name}.py"
            
            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f'"""\nTool: {tool_name}\nCategory: {category}\nDescription: {description}\n"""\n\n')
                f.write(code)
            
            # Update metadata
            self._update_metadata(tool_name, description, category, str(tool_file))
            
            return True
            
        except Exception as e:
            print(f"Failed to save tool {tool_name}: {e}")
            return False
    
    def _update_metadata(self, tool_name: str, description: str, category: str, file_path: str):
        """Update metadata.json with tool information"""
        try:
            # Load existing metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Add/update tool metadata
            metadata[tool_name] = {
                "name": tool_name,
                "description": description,
                "category": category,
                "file_path": file_path,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Save metadata
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Failed to update metadata for {tool_name}: {e}")
    
    def _add_to_vector_db(self, tool_name: str, code: str, description: str, 
                         category: str, metadata: Optional[Dict[str, Any]]) -> bool:
        """Add tool to vector database for semantic search"""
        try:
            # Create comprehensive tool metadata for vector database
            tool_metadata = {
                'tool_name': tool_name,
                'category': category,
                'description': description,
                'code': code,  # Include code for better embedding
                'file_path': f"tools/{category}/{tool_name}.py",
                'created_at': datetime.now().isoformat(),
                'code_hash': hashlib.md5(code.encode()).hexdigest(),
                'auto_generated': False
            }
            
            # Add custom metadata if provided
            if metadata:
                tool_metadata.update(metadata)
            
            # Use vector database's add_tool method
            return self.tool_vector_db.add_tool(tool_metadata)
            
        except Exception as e:
            print(f"Vector database storage error: {e}")
            return False
    
    def _update_unified_metadata(self, tool_name: str, description: str, 
                                category: str, metadata: Optional[Dict[str, Any]]) -> None:
        """Update unified metadata file"""
        try:
            # Load existing metadata
            all_metadata = {}
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
            
            # Update tool metadata
            tool_metadata = {
                'description': description,
                'category': category,
                'file_path': f"tools/{category}/{tool_name}.py",
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if metadata:
                tool_metadata.update(metadata)
            
            all_metadata[tool_name] = tool_metadata
            
            # Save updated metadata
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Metadata update error: {e}")
    
    def _remove_from_metadata(self, tool_name: str) -> None:
        """Remove tool from unified metadata"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                
                if tool_name in all_metadata:
                    del all_metadata[tool_name]
                    
                    with open(self.metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
                        
        except Exception as e:
            print(f"Metadata removal error: {e}")
    
 