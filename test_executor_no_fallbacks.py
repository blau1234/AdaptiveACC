"""
Test Executor with all fallback mechanisms removed
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_executor_successful_execution():
    """Test successful execution without fallbacks"""
    
    print("Testing Executor Successful Execution")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        # Test data
        plan = {
            "plan_id": "test_plan_123",
            "steps": [
                {
                    "step_id": "step_1",
                    "description": "Basic validation check",
                    "task_type": "validation", 
                    "priority": "high",
                    "required_tools": ["basic_validator"],
                    "expected_output": "Validation result",
                    "dependencies": []
                }
            ]
        }
        
        ifc_file_path = "test_file.ifc"
        
        print("1. Testing basic plan execution...")
        
        def mock_successful_react_responses(prompt, system_prompt):
            if "What action should I take next to complete this step?" in prompt:
                return """{
    "reasoning": "This is a basic validation step, I should use the basic_validator tool",
    "action": "use_tool", 
    "action_params": {
        "tool_name": "basic_validator",
        "parameters": {}
    }
}"""
            elif "Evaluate if this step is now complete or needs more actions:" in prompt:
                return """{
    "observation": "Basic validation completed successfully",
    "step_status": "completed"
}"""
            else:
                return '{"default": "response"}'
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            with patch.object(executor.llm_client, 'generate_response', side_effect=mock_successful_react_responses):
                
                try:
                    result = executor.execute_plan(plan, ifc_file_path)
                    
                    print("SUCCESS: Plan executed successfully!")
                    print(f"- Execution status: {result.get('execution_status')}")
                    print(f"- Completed steps: {result.get('completed_count')}")
                    print(f"- Failed steps: {result.get('failed_count')}")
                    print(f"- Total steps: {result.get('total_steps')}")
                    
                    return True
                    
                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return False

def test_executor_failure_scenarios():
    """Test that Executor raises exceptions instead of using fallbacks"""
    
    print("\nTesting Executor Failure Scenarios") 
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        # Test data
        step = {
            "step_id": "step_1",
            "description": "Test step",
            "required_tools": ["basic_validator"]
        }
        
        context = {"step_index": 0, "ifc_file_path": "test.ifc"}
        
        print("1. Testing reasoning step failure...")
        
        def mock_reasoning_failure(prompt, system_prompt):
            if "What action should I take next to complete this step?" in prompt:
                raise Exception("Simulated LLM reasoning failure")
            else:
                return '{"default": "response"}'
        
        with patch.object(executor.llm_client, 'generate_response', side_effect=mock_reasoning_failure):
            try:
                result = executor._execute_step_with_react(step, context)
                print("FAILED: Should have raised exception")
                test1_success = False
            except RuntimeError as e:
                if "ReAct reasoning step failed" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                    test1_success = True
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
                    test1_success = False
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
                test1_success = False
        
        print("\n2. Testing invalid JSON in reasoning response...")
        
        def mock_invalid_reasoning_json(prompt, system_prompt):
            if "What action should I take next to complete this step?" in prompt:
                return "This is not JSON at all"
            else:
                return '{"default": "response"}'
        
        with patch.object(executor.llm_client, 'generate_response', side_effect=mock_invalid_reasoning_json):
            try:
                result = executor._execute_step_with_react(step, context)
                print("FAILED: Should have raised exception")
                test2_success = False
            except RuntimeError as e:
                if "ReAct reasoning step failed" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                    test2_success = True
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
                    test2_success = False
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
                test2_success = False
        
        print("\n3. Testing observation step failure...")
        
        def mock_observation_failure(prompt, system_prompt):
            if "What action should I take next to complete this step?" in prompt:
                return """{
    "reasoning": "Test reasoning",
    "action": "use_tool",
    "action_params": {"tool_name": "basic_validator", "parameters": {}}
}"""
            elif "Evaluate if this step is now complete or needs more actions:" in prompt:
                return "Invalid JSON observation"
            else:
                return '{"default": "response"}'
        
        with patch('os.path.exists', return_value=True):
            with patch.object(executor.llm_client, 'generate_response', side_effect=mock_observation_failure):
                try:
                    result = executor._execute_step_with_react(step, context)
                    print("FAILED: Should have raised exception")
                    test3_success = False
                except RuntimeError as e:
                    if "ReAct observation step failed" in str(e):
                        print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                        test3_success = True
                    else:
                        print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
                        test3_success = False
                except Exception as e:
                    print(f"UNEXPECTED: Different exception type: {e}")
                    test3_success = False
        
        return test1_success, test2_success, test3_success

def test_removed_fallback_functions():
    """Test that fallback functions are actually removed"""
    
    print("\nTesting Removed Fallback Functions")
    print("=" * 40)
    
    from agents.executor import Executor
    
    executor = Executor()
    
    # Check that fallback_checker_tool is removed
    if hasattr(executor, '_fallback_checker_tool'):
        print("FAILED: _fallback_checker_tool still exists!")
        test1 = False
    else:
        print("SUCCESS: _fallback_checker_tool successfully removed")
        test1 = True
    
    # Check that fallback_checker is not in available_tools
    available_tools = executor.available_tools
    if 'fallback_checker' in available_tools:
        print("FAILED: fallback_checker still in available_tools!")
        test2 = False
    else:
        print("SUCCESS: fallback_checker removed from available_tools")
        test2 = True
    
    print(f"Available tools: {list(available_tools.keys())}")
    
    return test1 and test2

if __name__ == "__main__":
    print("Testing Executor with No Fallback Mechanisms")
    print("=" * 80)
    
    # Test successful execution
    success_test = test_executor_successful_execution()
    
    # Test failure scenarios
    failure_tests = test_executor_failure_scenarios()
    failure_test_success = all(failure_tests)
    
    # Test removed functions
    removal_test = test_removed_fallback_functions()
    
    print("\n" + "=" * 80)
    print("TEST RESULTS:")
    print(f"- Successful execution: {'PASS' if success_test else 'FAIL'}")
    print(f"- Failure handling: {'PASS' if failure_test_success else 'FAIL'}")
    print(f"  - Reasoning failure: {'PASS' if failure_tests[0] else 'FAIL'}")
    print(f"  - Invalid JSON: {'PASS' if failure_tests[1] else 'FAIL'}")
    print(f"  - Observation failure: {'PASS' if failure_tests[2] else 'FAIL'}")
    print(f"- Fallback removal: {'PASS' if removal_test else 'FAIL'}")
    
    all_passed = success_test and failure_test_success and removal_test
    
    if all_passed:
        print("\nALL TESTS PASSED!")
        print("EXECUTOR IMPROVEMENTS COMPLETED:")
        print("- Removed _fallback_checker_tool function")
        print("- Removed fallback_checker from available tools")
        print("- Updated JSON parsing to raise exceptions instead of fallback")
        print("- Consistent error handling throughout ReAct framework")
        print("- System fails fast when problems occur")
        print("\nEXECUTOR IS NOW CLEAN AND RELIABLE!")
    else:
        print("\nSome tests failed - check output above")
    
    print("=" * 80)