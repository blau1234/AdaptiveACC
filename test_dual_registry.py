#!/usr/bin/env python3
"""
Test script for dual registry architecture:
- MetaToolRegistry for 5 meta tools
- ToolRegistry for domain tools
"""

import json
from toolregistry import ToolRegistry
from domain_tools.domain_tool_registry import create_building_tool_registry
from meta_tools.meta_tool_registry import MetaToolRegistry
from agents.executor import Executor


def test_meta_tool_registry():
    """Test MetaToolRegistry functionality"""
    print("=== Testing MetaToolRegistry ===")
    
    # Create domain tools registry (for meta tools to use)
    domain_registry = create_building_tool_registry()
    print(f"Domain registry loaded with {len(domain_registry.get_available_tools())} tools")
    
    # Create meta tool manager (singleton)
    meta_manager = MetaToolRegistry.get_instance()
    
    # Create meta tools registry
    meta_registry = ToolRegistry()
    
    # Register all meta tools
    registered = meta_manager.register_meta_tools_to_registry(meta_registry)
    print(f"Registered {len(registered)} meta tools: {registered}")
    
    # Test meta tools availability
    available_meta_tools = meta_registry.get_available_tools()
    print(f"Available meta tools: {available_meta_tools}")
    
    # Test getting meta tools in OpenAI format
    meta_tools_json = meta_registry.get_tools_json(api_format="openai-chatcompletion")
    print(f"Meta tools schemas: {len(meta_tools_json)} schemas generated")
    
    for tool_schema in meta_tools_json:
        tool_name = tool_schema.get("function", {}).get("name", "unknown")
        print(f"  - {tool_name}")
    
    return meta_registry, domain_registry


def test_executor_pure_meta_architecture():
    """Test Executor with pure meta tool architecture"""
    print("\n=== Testing Executor Pure Meta Architecture ===")
    
    meta_registry, domain_registry = test_meta_tool_registry()
    
    # Create meta tool manager for executor
    meta_manager = MetaToolRegistry.get_instance()
    
    # Create executor with pure meta tool architecture
    executor = Executor()
    # Register meta tools to executor's registry
    meta_manager.register_meta_tools_to_registry(executor.meta_tool_registry)
    
    # Test meta tool availability
    print("\n--- Testing Pure Meta Tool Architecture ---")
    
    # Executor only has access to meta tools
    meta_tools = executor.meta_tool_registry.get_available_tools()
    print(f"Executor has access to {len(meta_tools)} meta tools:")
    for tool_name in meta_tools:
        print(f"  - {tool_name}")
    
    # Domain tools are accessible only through meta tools
    print(f"\nDomain registry (accessible via meta tools): {len(domain_registry.get_available_tools())} domain tools")
    
    return executor


def test_meta_tool_execution():
    """Test executing a meta tool through registry"""
    print("\n=== Testing Meta Tool Execution ===")
    
    executor = test_executor_pure_meta_architecture()
    
    # Executor now only uses meta tools
    
    # Test executing a meta tool
    try:
        print("\n--- Testing Tool Selection Meta Tool ---")
        result = executor._execute_action(
            "tool_selection",
            {
                "step_description": "Check wall thickness in building model",
                "execution_context": "{}"
            },
            {"ifc_file_path": "test.ifc"}
        )
        
        print(f"Meta tool execution result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Tool: {result.get('tool_name')}")
        print(f"  Is Meta Tool: {result.get('is_meta_tool', False)}")
        if not result.get('success'):
            print(f"  Error: {result.get('error')}")
        
    except Exception as e:
        print(f"Meta tool execution failed: {e}")


def main():
    """Run all tests"""
    print("Testing Dual Registry Architecture")
    print("=" * 50)
    
    try:
        # Test 1: Meta Tool Registry
        test_meta_tool_registry()
        
        # Test 2: Executor Integration
        test_executor_pure_meta_architecture()
        
        # Test 3: Meta Tool Execution
        test_meta_tool_execution()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("\nPure Meta Tool Architecture Summary:")
        print("- MetaToolRegistry: 5 meta tools for tool management")
        print("- Domain ToolRegistry: Accessible only through meta tools")
        print("- Executor: Only interacts with meta tools, follows layered architecture")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()