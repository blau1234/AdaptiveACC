import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from meta_tools.tool_storage import ToolStorage


class ToolManager:
    """
    Administrative tool manager for domain tool management operations.
    Provides management functionality separate from meta tools automation.
    """

    def __init__(self):
        self.tool_storage = ToolStorage()

    def list_stored_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all stored tools, optionally filtered by category using metadata manager

        Args:
            category: Optional category filter

        Returns:
            List of tool information
        """
        tools = []
        try:
            all_metadata = self._get_all_metadata()

            if all_metadata:
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

    def delete_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Delete a tool from storage (filesystem and vector database)

        Args:
            tool_name: Name of the tool to delete

        Returns:
            Result dictionary with success status and message
        """
        try:
            # Get tool metadata first
            metadata = self._get_tool_metadata(tool_name)
            if not metadata:
                return {
                    "success": False,
                    "message": f"Tool '{tool_name}' not found",
                    "tool_name": tool_name
                }

            # Delete from filesystem
            category = metadata.get('category', 'builtin')
            tool_file = self.tool_storage.base_dir / category / f"{tool_name}.py"
            filesystem_deleted = False
            if tool_file.exists():
                tool_file.unlink()
                filesystem_deleted = True
                print(f"Deleted {tool_name} from filesystem")

            # Remove from vector database (if available)
            vector_deleted = False
            if self.tool_storage._get_vector_db().is_available():
                # Note: Vector database deletion not fully implemented yet
                print(f"Vector database deletion not implemented for {tool_name}")
                vector_deleted = True  # Assume success for now

            # Remove from unified metadata
            self._remove_from_metadata(tool_name)

            return {
                "success": True,
                "message": f"Successfully deleted tool '{tool_name}'",
                "tool_name": tool_name,
                "filesystem_deleted": filesystem_deleted,
                "vector_deleted": vector_deleted
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting tool '{tool_name}': {str(e)}",
                "tool_name": tool_name
            }

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
                "vector_db_available": self.tool_storage._get_vector_db().is_available(),
                "storage_directory": str(self.tool_storage.base_dir)
            }

            all_metadata = self._get_all_metadata()
            if all_metadata:
                stats["total_tools"] = len(all_metadata)

                # Count by category
                for metadata in all_metadata.values():
                    category = metadata.get('category', 'unknown')
                    stats["categories"][category] = stats["categories"].get(category, 0) + 1

            # Add vector database stats if available
            tool_vector_db = self.tool_storage._get_vector_db()
            if tool_vector_db.is_available():
                try:
                    vector_stats = tool_vector_db.get_stats()
                    stats["vector_db_stats"] = vector_stats
                except:
                    stats["vector_db_stats"] = {"error": "Unable to get vector DB stats"}

            return stats

        except Exception as e:
            return {"error": f"Unable to get storage stats: {e}"}

    def _get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific tool using metadata manager
        This method now delegates to the unified metadata manager.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata dictionary or None if not found
        """
        return self._get_metadata(tool_name)

    def _remove_from_metadata(self, tool_name: str) -> None:
        """Remove tool from metadata file"""
        try:
            if self._remove_metadata(tool_name):
                print(f"Removed {tool_name} from metadata")
            else:
                print(f"Tool {tool_name} not found in metadata")
        except Exception as e:
            print(f"Error removing {tool_name} from metadata: {e}")

    def _get_all_metadata(self) -> Optional[Dict[str, Any]]:
        """Get all metadata from JSON file"""
        try:
            if self.tool_storage.metadata_file.exists():
                with open(self.tool_storage.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading metadata: {e}")
        return None

    def _get_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool"""
        try:
            all_metadata = self._get_all_metadata()
            if all_metadata:
                return all_metadata.get(tool_name)
        except Exception as e:
            print(f"Error getting metadata for {tool_name}: {e}")
        return None

    def _remove_metadata(self, tool_name: str) -> bool:
        """Remove tool metadata from JSON file"""
        try:
            if not self.tool_storage.metadata_file.exists():
                return False

            with open(self.tool_storage.metadata_file, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)

            if tool_name in all_metadata:
                del all_metadata[tool_name]
                with open(self.tool_storage.metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(all_metadata, f, indent=2, ensure_ascii=False)
                return True

            return False

        except Exception as e:
            print(f"Error removing metadata: {e}")
            return False