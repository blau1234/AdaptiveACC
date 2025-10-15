"""
Script to incrementally sync the tool vector database with current domain tools
"""

from datetime import datetime
from typing import Dict, List, Any
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from utils.rag_tool import ToolVectorManager


def extract_tool_metadata(tool_name: str, tool_schema: dict) -> dict:
    """Extract metadata from tool schema"""

    # Get function details
    function = tool_schema.get("function", {})
    parameters = function.get("parameters", {})
    properties = parameters.get("properties", {})

    # Extract parameter names
    param_names = list(properties.keys())

    # Extract description
    description = function.get("description", "")

    metadata = {
        "tool_name": tool_name,
        "description": description,
        "parameters": ", ".join(param_names)
    }

    return metadata


def has_tool_changed(current_tool: dict, existing_tool: dict) -> bool:
    """Check if tool metadata has changed

    Args:
        current_tool: Tool metadata from DomainToolRegistry
        existing_tool: Tool metadata from vectordb

    Returns:
        True if tool has changed, False otherwise
    """
    # Compare key fields that affect semantic search
    current_desc = current_tool.get('description', '').strip()
    existing_desc = existing_tool.get('description', '').strip()

    current_params = current_tool.get('parameters', '').strip()
    existing_params = existing_tool.get('parameters', '').strip()

    return (current_desc != existing_desc or
            current_params != existing_params)


def sync_vectordb():
    """Incrementally sync vector database with current domain tools"""

    print("=" * 60)
    print("SYNCING TOOL VECTOR DATABASE")
    print("=" * 60)

    # Step 1: Load current tools from registry
    print("\n[1/5] Loading current domain tools from registry...")
    domain_registry = IFCToolRegistry.get_instance()
    tool_schemas = domain_registry.get_tools_json(api_format="openai-chatcompletion")

    current_tools = {}
    for tool_schema in tool_schemas:
        function_name = tool_schema.get("function", {}).get("name", "unknown")
        metadata = extract_tool_metadata(function_name, tool_schema)
        current_tools[function_name] = metadata

    print(f"Found {len(current_tools)} tools in registry")

    # Step 2: Load existing tools from vectordb
    print("\n[2/5] Loading existing tools from vector database...")
    tool_vector_manager = ToolVectorManager.get_instance()

    if not tool_vector_manager.is_available():
        print("ERROR: Vector database not available. Please run rebuild_tool_vectordb.py first.")
        return False

    existing_tools = tool_vector_manager.get_all_tools()
    existing_tool_map = {t['tool_name']: t for t in existing_tools}

    print(f"Found {len(existing_tools)} tools in vector database")

    # Step 3: Calculate differences
    print("\n[3/5] Calculating differences...")
    current_names = set(current_tools.keys())
    existing_names = set(existing_tool_map.keys())

    to_add = current_names - existing_names
    to_delete = existing_names - current_names
    to_check = current_names & existing_names

    # Check for modifications in existing tools
    to_update = set()
    for tool_name in to_check:
        if has_tool_changed(current_tools[tool_name], existing_tool_map[tool_name]):
            to_update.add(tool_name)

    print(f"  To add: {len(to_add)}")
    print(f"  To delete: {len(to_delete)}")
    print(f"  To update: {len(to_update)}")
    print(f"  Unchanged: {len(to_check) - len(to_update)}")

    # Step 4: Apply changes
    print("\n[4/5] Applying changes...")

    deleted_count = 0
    added_count = 0
    updated_count = 0

    # Delete removed tools
    if to_delete:
        print(f"\n  [DELETE] Removing {len(to_delete)} tools...")
        for tool_name in sorted(to_delete):
            if tool_vector_manager.delete_tool(tool_name):
                deleted_count += 1
                print(f"    - Deleted: {tool_name}")
            else:
                print(f"    - Failed to delete: {tool_name}")

    # Add new tools
    if to_add:
        print(f"\n  [ADD] Adding {len(to_add)} new tools...")
        for tool_name in sorted(to_add):
            if tool_vector_manager.add_tool(current_tools[tool_name]):
                added_count += 1
                print(f"    + Added: {tool_name}")
            else:
                print(f"    + Failed to add: {tool_name}")

    # Update modified tools
    if to_update:
        print(f"\n  [UPDATE] Updating {len(to_update)} modified tools...")
        for tool_name in sorted(to_update):
            if tool_vector_manager.update_tool(current_tools[tool_name]):
                updated_count += 1
                print(f"    * Updated: {tool_name}")
            else:
                print(f"    * Failed to update: {tool_name}")

    # Step 5: Summary
    print("\n[5/5] Verification...")
    stats = tool_vector_manager.get_stats()
    final_count = stats.get('tool_count', 0)

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"Deleted: {deleted_count}")
    print(f"Added: {added_count}")
    print(f"Updated: {updated_count}")
    print(f"Unchanged: {len(to_check) - len(to_update)}")
    print(f"Total in database: {final_count}")

    expected_count = len(current_tools)
    if final_count == expected_count:
        print(f"\n[SUCCESS] Vector database is in sync ({final_count} tools)")
        return True
    else:
        print(f"\n[WARNING] Count mismatch: expected {expected_count}, got {final_count}")
        return False


if __name__ == "__main__":
    try:
        success = sync_vectordb()
        if not success:
            print("\n[WARNING] Sync completed with warnings")
    except Exception as e:
        print(f"\n[ERROR] Sync failed with error: {e}")
        import traceback
        traceback.print_exc()
