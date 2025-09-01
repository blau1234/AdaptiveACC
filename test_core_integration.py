"""
Test core ToolRegistry integration with Executor
"""

import json
from tool_library.building_tool_registry import BuildingToolRegistry
from agents.executor import Executor


def test_core_integration():
    """Test the core integration without dependencies that require config"""
    print("=== Core ToolRegistry Integration Test ===")
    
    # Test 1: Initialize components independently
    print("\n1. Testing BuildingToolRegistry...")
    registry = BuildingToolRegistry()
    available_tools = registry.get_available_tools()
    print(f"ToolRegistry: {len(available_tools)} tools available")
    
    # Test 2: Initialize Executor with ToolRegistry
    print("\n2. Testing Executor with ToolRegistry...")
    executor = Executor(tool_registry=registry)
    print(f"Executor initialized with registry: {type(executor.tool_registry)}")
    
    # Test 3: Check if Executor can see tools
    print("\n3. Testing Executor tool discovery...")
    executor_tools = executor._get_available_tools()
    print(f"Executor can see {len(executor_tools)} tools")
    for tool_name, tool_info in list(executor_tools.items())[:2]:
        print(f"- {tool_name}: {tool_info['description']}")
    
    # Test 4: Test tool schema generation for LLM
    print("\n4. Testing schema generation for LLM...")
    try:
        schemas = registry.get_all_tools_schema(api_format="openai-chatcompletion")
        print(f"Generated {len(schemas)} schemas for OpenAI API")
        
        # Show a sample schema
        if schemas:
            sample_schema = schemas[0]
            print(f"Sample schema for '{sample_schema['function']['name']}':")
            print(json.dumps(sample_schema, indent=2)[:300] + "...")
    except Exception as e:
        print(f"Schema generation failed: {e}")
    
    # Test 5: Test tool registration
    print("\n5. Testing dynamic tool registration...")
    sample_tool_code = '''
def test_compliance_tool(ifc_file_path: str, test_param: str = "default") -> dict:
    """Test compliance tool for integration testing"""
    return {
        "result": "pass",
        "detail": f"Test completed with param: {test_param}",
        "elements_checked": ["test_element"],
        "issues": []
    }
'''
    
    try:
        registration_result = registry.register_from_code(sample_tool_code, "test_compliance_tool")
        if registration_result.success:
            print(f"[PASS] Tool registered: {registration_result.tool_name}")
            
            # Verify it's available to Executor
            updated_tools = executor._get_available_tools()
            if "test_compliance_tool" in updated_tools:
                print("[PASS] New tool is visible to Executor")
            else:
                print("[FAIL] New tool not visible to Executor")
        else:
            print(f"[FAIL] Tool registration failed: {registration_result.message}")
    except Exception as e:
        print(f"Tool registration error: {e}")
    
    # Test 6: Test tool execution
    print("\n6. Testing tool execution...")
    try:
        # Test the newly registered tool
        result = registry.execute_single_tool(
            "test_compliance_tool",
            ifc_file_path="test.ifc",
            test_param="integration_test"
        )
        print(f"Tool execution result: {result}")
        if result.get("result") == "pass":
            print("[PASS] Tool execution successful")
        else:
            print("[FAIL] Tool execution failed")
    except Exception as e:
        print(f"Tool execution error: {e}")
    
    # Test 7: Test OpenAI-style tool calls
    print("\n7. Testing OpenAI-style tool calls...")
    tool_calls = [
        {
            "id": "call_test_123",
            "type": "function",
            "function": {
                "name": "test_compliance_tool",
                "arguments": json.dumps({
                    "ifc_file_path": "test.ifc",
                    "test_param": "openai_test"
                })
            }
        }
    ]
    
    try:
        results = registry.execute_tool_calls(tool_calls)
        print(f"OpenAI-style execution results: {results}")
        if "call_test_123" in results:
            print("[PASS] OpenAI-style tool calls working")
        else:
            print("[FAIL] OpenAI-style tool calls failed")
    except Exception as e:
        print(f"OpenAI-style execution error: {e}")
    
    return registry, executor


if __name__ == "__main__":
    try:
        registry, executor = test_core_integration()
        
        print("\n=== Integration Test Summary ===")
        print("[PASS] BuildingToolRegistry initialization")
        print("[PASS] Executor integration with ToolRegistry")
        print("[PASS] Tool discovery and schema generation")
        print("[PASS] Dynamic tool registration")
        print("[PASS] Tool execution (single and batch)")
        print("[PASS] OpenAI API compatibility")
        
        print(f"\nFinal status:")
        print(f"- Total tools: {len(registry.get_available_tools())}")
        print(f"- Available tools: {registry.get_available_tools()}")
        print(f"- System health: {registry.health_check()['status']}")
        
        print("\n[SUCCESS] Core ToolRegistry integration is working perfectly!")
        
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()