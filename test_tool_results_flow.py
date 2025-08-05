"""
Test that tool execution results flow correctly to checker
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tool_results_flow():
    """Test that tool execution results flow from executor to coordinator to checker"""
    print("Testing Tool Results Flow")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        from tool_library.tool_manager import ToolManager
        
        executor = Executor()
        
        # Mock tool manager to return specific results
        def mock_execute_tool(tool_name, ifc_file_path, parameters):
            return {
                "result": "pass",
                "detail": f"Successfully executed {tool_name}",
                "elements_checked": ["Door_001", "Door_002"],
                "issues": [],
                "element_count": 2,
                "element_type": "IfcDoor",
                "elements_data": [
                    {"id": "Door_001", "name": "Main Entrance"},
                    {"id": "Door_002", "name": "Emergency Exit"}
                ]
            }
        
        executor.tool_manager.execute_tool = MagicMock(side_effect=mock_execute_tool)
        
        # Mock LLM to return a simple sequence: extract doors -> complete
        call_count = 0
        def mock_llm_response(prompt, system_prompt):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                return '''{"thought": "I need to extract door elements from the IFC file", "action": "get_elements_by_type", "action_input": {"element_type": "IfcDoor"}, "is_final": false}'''
            else:
                return '''{"thought": "Task completed successfully", "is_final": true}'''
        
        executor.llm_client.generate_response = MagicMock(side_effect=mock_llm_response)
        
        print("1. Testing executor step execution:")
        
        test_step = {
            "step_id": "step_1",
            "description": "Extract door elements for accessibility check",
            "task_type": "element_extraction"
        }
        
        result = executor.execute_step(test_step, "test_ifc/sample.ifc")
        
        print(f"   Step status: {result.get('status')}")
        print(f"   Tool results included: {'tool_results' in result}")
        
        if "tool_results" in result:
            tool_results = result["tool_results"]
            print(f"   Number of tool results: {len(tool_results)}")
            
            for i, tool_result in enumerate(tool_results):
                print(f"   Tool result {i+1}:")
                print(f"     - Result: {tool_result.get('result')}")
                print(f"     - Detail: {tool_result.get('detail')}")
                print(f"     - Elements: {len(tool_result.get('elements_checked', []))}")
                print(f"     - Element type: {tool_result.get('element_type')}")
        
        print("\n2. Testing data structure compatibility with checker:")
        
        # Check if tool results have the expected fields for checker
        if "tool_results" in result:
            for tool_result in result["tool_results"]:
                required_fields = ["result", "detail", "issues", "elements_checked"]
                missing_fields = [field for field in required_fields if field not in tool_result]
                
                if not missing_fields:
                    print("   SUCCESS: Tool result has all required fields for checker")
                else:
                    print(f"   WARNING: Missing fields: {missing_fields}")
                
                # Check specific data
                print(f"   - Has elements data: {'elements_data' in tool_result}")
                print(f"   - Element count: {tool_result.get('element_count', 0)}")
        
        return result.get("status") == "success" and "tool_results" in result

def test_coordinator_collection():
    """Test that coordinator correctly collects tool results"""
    print("\n\nTesting Coordinator Tool Results Collection")
    print("=" * 50)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.coordinator import AgentCoordinator
        
        coordinator = AgentCoordinator()
        
        # Mock executor to return tool results
        def mock_execute_single_step(step, ifc_file_path, step_id):
            return {
                "step_status": "success",
                "step_result": {"message": "completed"},
                "tool_results": [
                    {
                        "result": "pass",
                        "detail": "Successfully extracted 3 IfcDoor elements",
                        "elements_checked": ["Door_001", "Door_002", "Door_003"],
                        "issues": [],
                        "element_count": 3,
                        "element_type": "IfcDoor",
                        "elements_data": [
                            {"id": "Door_001", "name": "Main Door"},
                            {"id": "Door_002", "name": "Side Door"},
                            {"id": "Door_003", "name": "Emergency Door"}
                        ]
                    }
                ]
            }
        
        coordinator.executor.execute_single_step = MagicMock(side_effect=mock_execute_single_step)
        
        # Mock other agents
        coordinator.planner.generate_initial_plan = MagicMock(return_value={
            "plan_id": "test_plan",
            "steps": [{"step_id": "step_1", "description": "Extract doors"}]
        })
        coordinator.checker.check_and_report = MagicMock(return_value={"status": "compliant"})
        
        print("1. Testing plan execution:")
        
        test_plan = {
            "plan_id": "test_plan",
            "steps": [{"step_id": "step_1", "description": "Extract doors"}]
        }
        
        result = coordinator.execute_plan(test_plan, "test_ifc/sample.ifc")
        
        execution_results = result.get("execution_results", [])
        print(f"   Execution results count: {len(execution_results)}")
        
        if execution_results:
            for i, exec_result in enumerate(execution_results):
                print(f"   Result {i+1}: {exec_result.get('detail', 'No detail')}")
                print(f"     - Elements: {len(exec_result.get('elements_checked', []))}")
                print(f"     - Element type: {exec_result.get('element_type', 'unknown')}")
        
        return len(execution_results) > 0

if __name__ == "__main__":
    print("Testing Tool Results Data Flow")
    print("=" * 80)
    
    # Run tests
    test1_success = test_tool_results_flow()
    test2_success = test_coordinator_collection()
    
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY:")
    print("=" * 80)
    
    print(f"1. Executor Tool Results Flow: {'PASS' if test1_success else 'FAIL'}")
    print(f"2. Coordinator Collection: {'PASS' if test2_success else 'FAIL'}")
    
    if test1_success and test2_success:
        print("\nSUCCESS: Tool execution results now flow correctly!")
        print("- Executor captures tool results during ReAct execution")
        print("- Coordinator collects tool results directly")
        print("- Checker should now receive properly formatted tool results")
    else:
        print("\nSome tests failed - check implementation")
    
    print("=" * 80)