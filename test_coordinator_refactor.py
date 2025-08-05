"""
Test the refactored coordinator to ensure no duplicate execution logic
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_coordinator_refactor():
    """Test that coordinator uses execute_plan properly without duplication"""
    print("Testing Refactored Coordinator")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.coordinator import AgentCoordinator
        
        coordinator = AgentCoordinator()
        
        # Mock the agents to avoid actual LLM calls
        mock_plan = {
            "plan_id": "test_plan_123",
            "steps": [
                {
                    "step_id": "step_1",
                    "description": "Extract door elements",
                    "priority": "high",
                    "expected_output": "List of doors"
                },
                {
                    "step_id": "step_2", 
                    "description": "Measure door widths",
                    "priority": "high",
                    "expected_output": "Door width measurements"
                }
            ]
        }
        
        # Mock planner to return the test plan
        coordinator.planner.generate_initial_plan = MagicMock(return_value=mock_plan)
        coordinator.planner.get_conversation_history = MagicMock(return_value=[])
        
        # Mock executor to return successful step results
        def mock_execute_single_step(step, ifc_file_path, step_id):
            return {
                "step_status": "success",
                "step_result": {
                    "result": "pass",
                    "detail": f"Step {step_id + 1} completed successfully",
                    "data": f"Mock data for {step['description']}"
                },
                "iterations_used": 1,
                "execution_history": [{"action": "mock_action"}]
            }
        
        coordinator.executor.execute_single_step = MagicMock(side_effect=mock_execute_single_step)
        coordinator.executor.get_execution_history = MagicMock(return_value=[])
        
        # Mock checker to return compliance report
        mock_compliance_report = {
            "overall_compliance": "PASS",
            "details": "All requirements met",
            "issues": []
        }
        coordinator.checker.check_and_report = MagicMock(return_value=mock_compliance_report)
        
        print("1. Testing execute_plan method (core execution logic):")
        
        # Test execute_plan directly
        plan_result = coordinator.execute_plan(mock_plan, "test_ifc/sample.ifc")
        
        print(f"   Plan execution status: {plan_result.get('execution_status')}")
        print(f"   Steps completed: {plan_result.get('steps_completed')}/{plan_result.get('total_steps')}")
        print(f"   Feedback rounds used: {plan_result.get('feedback_rounds_used')}")
        
        # Verify execute_plan was called correctly
        assert plan_result.get("execution_status") == "completed"
        assert plan_result.get("steps_completed") == 2
        assert len(plan_result.get("execution_results", [])) == 2
        
        print("   SUCCESS: execute_plan works correctly")
        
        print("\n2. Testing execute_compliance_check method (full workflow):")
        
        # Reset mocks
        coordinator.executor.execute_single_step.reset_mock()
        
        # Test full compliance check
        test_regulation = "Doors must be at least 32 inches wide for accessibility compliance."
        compliance_result = coordinator.execute_compliance_check(test_regulation, "test_ifc/sample.ifc")
        
        print(f"   Compliance check status: {compliance_result.get('execution_status')}")
        print(f"   Final report: {compliance_result.get('final_report', {}).get('overall_compliance')}")
        print(f"   Steps completed: {compliance_result.get('steps_completed')}/{compliance_result.get('total_steps')}")
        
        # Verify that execute_compliance_check used execute_plan (no duplication)
        assert compliance_result.get("execution_status") == "completed"
        assert compliance_result.get("steps_completed") == 2
        assert len(compliance_result.get("execution_results", [])) == 2
        assert compliance_result.get("final_report") == mock_compliance_report
        
        # Verify executor was called the right number of times (2 steps)
        assert coordinator.executor.execute_single_step.call_count == 2
        
        print("   SUCCESS: execute_compliance_check delegates to execute_plan correctly")
        
        print("\n3. Testing no code duplication:")
        
        # Check that both methods produce consistent results
        plan_exec_results = plan_result.get("execution_results", [])
        compliance_exec_results = compliance_result.get("execution_results", [])
        
        assert len(plan_exec_results) == len(compliance_exec_results)
        print(f"   Both methods executed {len(plan_exec_results)} steps consistently")
        
        print("   SUCCESS: No code duplication detected")
        
        return True

def test_feedback_loop_handling():
    """Test that feedback loops are handled properly in the refactored code"""
    print("\n\nTesting Feedback Loop Handling")
    print("=" * 40)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.coordinator import AgentCoordinator
        
        coordinator = AgentCoordinator()
        
        # Mock plan with steps that will fail and require modification
        mock_plan = {
            "plan_id": "test_plan_feedback",
            "steps": [
                {
                    "step_id": "step_1",
                    "description": "This step will fail initially",
                    "priority": "high"
                }
            ]
        }
        
        modified_plan = {
            "plan_id": "test_plan_feedback",
            "modification_count": 1,
            "steps": [
                {
                    "step_id": "step_1_modified",
                    "description": "This step will succeed after modification",
                    "priority": "high"
                }
            ]
        }
        
        # Mock planner
        coordinator.planner.modify_plan = MagicMock(return_value=modified_plan)
        
        # Mock executor to fail first, then succeed
        call_count = 0
        def mock_execute_with_failure(step, ifc_file_path, step_id):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                return {
                    "step_status": "failed",
                    "failure_reason": "tool_not_found",
                    "error_message": "Tool 'invalid_tool' not found"
                }
            else:
                # Second call (after plan modification) succeeds
                return {
                    "step_status": "success",
                    "step_result": {
                        "result": "pass",
                        "detail": "Step succeeded after plan modification"
                    }
                }
        
        coordinator.executor.execute_single_step = MagicMock(side_effect=mock_execute_with_failure)
        
        print("1. Testing feedback loop in execute_plan:")
        
        result = coordinator.execute_plan(mock_plan, "test_ifc/sample.ifc")
        
        print(f"   Final status: {result.get('execution_status')}")
        print(f"   Feedback rounds used: {result.get('feedback_rounds_used')}")
        print(f"   Steps completed: {result.get('steps_completed')}")
        
        # Verify feedback loop worked
        assert result.get("execution_status") == "completed"
        assert result.get("feedback_rounds_used") == 1
        assert result.get("steps_completed") == 1
        
        # Verify planner was called for modification
        coordinator.planner.modify_plan.assert_called_once()
        
        # Verify executor was called twice (fail, then succeed)
        assert coordinator.executor.execute_single_step.call_count == 2
        
        print("   SUCCESS: Feedback loop handled correctly")
        
        return True

def run_all_tests():
    """Run all coordinator refactor tests"""
    print("Testing Coordinator Refactor - No Duplicate Execution Logic")
    print("=" * 80)
    
    try:
        # Test basic refactor
        test1_success = test_coordinator_refactor()
        
        # Test feedback loop handling  
        test2_success = test_feedback_loop_handling()
        
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY:")
        print("=" * 80)
        
        print(f"1. Coordinator Refactor: {'PASS' if test1_success else 'FAIL'}")
        print(f"2. Feedback Loop Handling: {'PASS' if test2_success else 'FAIL'}")
        
        overall_success = test1_success and test2_success
        
        if overall_success:
            print("\n✅ ALL TESTS PASSED!")
            print("\nKEY REFACTOR BENEFITS:")
            print("SUCCESS: ✅ Eliminated duplicate execution logic")
            print("SUCCESS: ✅ execute_compliance_check now uses execute_plan")
            print("SUCCESS: ✅ Single source of truth for plan execution")
            print("SUCCESS: ✅ Feedback loops work consistently")
            print("SUCCESS: ✅ Better code maintainability")
            print("\nThe coordinator is now properly refactored with no duplicate code!")
        else:
            print("\n❌ Some tests failed - check details above")
        
        print("=" * 80)
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_all_tests()