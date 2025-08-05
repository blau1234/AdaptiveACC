"""
Test the new LLM-driven dynamic plan modification
"""

import json
from unittest.mock import patch, MagicMock
from agents.planner import Planner


def test_llm_plan_modification():
    """Test the new LLM-based plan modification"""
    print("=== Testing LLM-Driven Plan Modification ===")
    
    # Create planner instance
    planner = Planner("test-model", "test-key")
    
    # Sample current plan
    current_plan = {
        "plan_id": "test_plan_123",
        "regulation_summary": "Fire safety requirements",
        "requirements": [
            {"id": "req_1", "description": "Exit width check", "type": "measurement"}
        ],
        "steps": [
            {
                "step_id": "step_1",
                "description": "Measure exit door width",
                "task_type": "measurement",
                "priority": "high",
                "tool_description": "width measurement tool",
                "expected_output": "Door width in meters",
                "dependencies": []
            },
            {
                "step_id": "step_2", 
                "description": "Validate exit capacity",
                "task_type": "calculation",
                "priority": "medium",
                "tool_description": "capacity calculator",
                "expected_output": "Maximum occupancy",
                "dependencies": ["step_1"]
            }
        ],
        "status": "initial",
        "modification_count": 0
    }
    
    # Sample feedback indicating step_1 failed due to tool failure
    feedback = {
        "issue_type": "tool_failure",
        "issue_description": "Width measurement tool not available",
        "failed_step": {
            "step_id": "step_1",
            "description": "Measure exit door width"
        },
        "step_index": 0,
        "error_message": "Tool 'width_measurement_tool' not found",
        "execution_context": {
            "completed_steps": 0,
            "total_steps": 2
        }
    }
    
    # Mock LLM response for plan modification
    modified_plan_response = {
        "plan_id": "test_plan_123",
        "regulation_summary": "Fire safety requirements", 
        "requirements": [
            {"id": "req_1", "description": "Exit width check", "type": "measurement"}
        ],
        "steps": [
            {
                "step_id": "step_1_alt",
                "description": "Alternative: Visual inspection of exit door width using manual measurement",
                "task_type": "measurement",
                "priority": "high",
                "tool_description": "manual measurement tape or ruler",
                "expected_output": "Door width estimate in meters",
                "dependencies": []
            },
            {
                "step_id": "step_1b",
                "description": "Cross-verify door width with building plans if available",
                "task_type": "validation",
                "priority": "medium", 
                "tool_description": "document analyzer",
                "expected_output": "Plan-based width confirmation",
                "dependencies": ["step_1_alt"]
            },
            {
                "step_id": "step_2",
                "description": "Validate exit capacity using measured width",
                "task_type": "calculation",
                "priority": "medium",
                "tool_description": "capacity calculator",
                "expected_output": "Maximum occupancy",
                "dependencies": ["step_1_alt", "step_1b"]
            }
        ]
    }
    
    # Test the LLM modification
    with patch.object(planner.llm_client, 'generate_response') as mock_llm:
        mock_llm.return_value = json.dumps(modified_plan_response)
        
        modified_plan = planner.modify_plan(current_plan, feedback)
        
        # Verify the modification worked
        print("SUCCESS: LLM plan modification test results:")
        print(f"   - Original steps: {len(current_plan['steps'])}")
        print(f"   - Modified steps: {len(modified_plan['steps'])}")
        print(f"   - Modification count: {modified_plan['modification_count']}")
        print(f"   - Status: {modified_plan['status']}")
        print(f"   - Plan ID preserved: {modified_plan['plan_id'] == current_plan['plan_id']}")
        
        # Check that LLM was called with proper context
        assert mock_llm.called, "LLM should have been called"
        call_args = mock_llm.call_args
        prompt = call_args[0][0]  # First positional argument
        
        assert "CURRENT PLAN:" in prompt, "Prompt should include current plan"
        assert "EXECUTOR FEEDBACK:" in prompt, "Prompt should include feedback"
        assert "tool_failure" in prompt, "Prompt should include issue type"
        
        # Verify modification results
        assert modified_plan["modification_count"] == 1, "Should increment modification count"
        assert modified_plan["status"] == "modified", "Should update status to modified"
        assert len(modified_plan["steps"]) == 3, "Should have 3 steps after modification"
        assert "step_1_alt" in [s["step_id"] for s in modified_plan["steps"]], "Should have alternative step"
        
        print("SUCCESS: All LLM plan modification tests passed!")


def test_fallback_plan_modification():
    """Test fallback when LLM fails"""
    print("\n=== Testing Fallback Plan Modification ===")
    
    planner = Planner("test-model", "test-key")
    
    current_plan = {
        "plan_id": "test_plan_456",
        "steps": [
            {
                "step_id": "step_1",
                "description": "Original step",
                "task_type": "measurement"
            }
        ],
        "modification_count": 0
    }
    
    feedback = {
        "issue_type": "tool_failure",
        "issue_description": "Tool failed",
        "step_index": 0
    }
    
    # Mock LLM to return invalid JSON
    with patch.object(planner.llm_client, 'generate_response') as mock_llm:
        mock_llm.return_value = "Invalid JSON response"
        
        modified_plan = planner.modify_plan(current_plan, feedback)
        
        print("SUCCESS: Fallback plan modification test results:")
        print(f"   - Fallback triggered successfully")
        print(f"   - Modified step description: {modified_plan['steps'][0]['description']}")
        print(f"   - Step has notes: {'notes' in modified_plan['steps'][0]}")
        
        assert "Simplified:" in modified_plan['steps'][0]['description'], "Should simplify description"
        assert "notes" in modified_plan['steps'][0], "Should add notes"
        
        print("SUCCESS: Fallback test passed!")


if __name__ == "__main__":
    try:
        test_llm_plan_modification()
        test_fallback_plan_modification()
        print("\nSUCCESS: All tests passed! LLM-driven plan modification is working correctly.")
    except Exception as e:
        print(f"\nERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()