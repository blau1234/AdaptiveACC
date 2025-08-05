"""
Test integration with simplified Checker
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_coordinator_with_simplified_checker():
    """Test that Coordinator works with the simplified Checker"""
    
    print("Testing Coordinator with Simplified Checker")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.coordinator import AgentCoordinator
        
        coordinator = AgentCoordinator()
        
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        
        print("1. Testing coordinator initialization...")
        print(f"   Planner type: {type(coordinator.planner).__name__}")
        print(f"   Executor type: {type(coordinator.executor).__name__}")
        print(f"   Checker type: {type(coordinator.checker).__name__}")
        
        # Mock successful responses for all agents
        def mock_responses(prompt, system_prompt):
            if system_prompt and "building code regulation analysis expert" in system_prompt.lower():
                return """{
    "summary": "Stairway width requirement - minimum 36 inches",
    "requirements": [
        {
            "id": "req_1",
            "description": "Minimum 36 inch clear width",
            "type": "accessibility",
            "measurable": true,
            "criteria": "Measure clear width"
        }
    ],
    "complexity": "low",
    "estimated_checks": 2
}"""
            elif "generate a detailed execution plan" in prompt.lower():
                return """[
    {
        "step_id": "step_1",
        "description": "Check stairway widths",
        "task_type": "measurement",
        "priority": "high",
        "tool_description": "Width measurement tool",
        "expected_output": "Width measurements",
        "dependencies": []
    }
]"""
            elif system_prompt and "building code compliance expert" in system_prompt.lower():
                return """{
    "compliant": true,
    "confidence": 0.9,
    "summary": "All stairways meet width requirements",
    "violations": [],
    "passed_checks": ["All stairway widths verified"],
    "recommendations": ["Maintain current standards"]
}"""
            else:
                return '{"default": "response"}'
        
        # Mock executor execution
        def mock_executor_execute(plan, ifc_file_path, max_feedback_rounds=3):
            return {
                "status": "completed",
                "results": [
                    {
                        "result": "pass",
                        "detail": "Stairway width check completed",
                        "elements_checked": ["stairway_1"],
                        "issues": []
                    }
                ],
                "feedback_rounds": 0,
                "steps_completed": 1
            }
        
        with patch.object(coordinator.planner.llm_client, 'generate_response', side_effect=mock_responses):
            with patch.object(coordinator.checker.llm_client, 'generate_response', side_effect=mock_responses):
                with patch.object(coordinator.executor, 'execute_plan', side_effect=mock_executor_execute):
                    
                    print("\n2. Testing _request_compliance_check method...")
                    
                    # Test the specific method that calls the simplified checker
                    mock_execution_results = [
                        {
                            "result": "pass", 
                            "detail": "Test check",
                            "elements_checked": [],
                            "issues": []
                        }
                    ]
                    
                    mock_plan = {"plan_id": "test_plan", "steps": []}
                    
                    try:
                        compliance_report = coordinator._request_compliance_check(
                            mock_execution_results, regulation_text, mock_plan
                        )
                        
                        print("SUCCESS: Compliance check completed!")
                        print(f"   Report ID: {compliance_report.get('report_id')}")
                        print(f"   Status: {compliance_report.get('executive_summary', {}).get('status')}")
                        print(f"   Has metadata: {'metadata' in compliance_report}")
                        
                        return True
                        
                    except Exception as e:
                        print(f"FAILED: {e}")
                        import traceback
                        traceback.print_exc()
                        return False

if __name__ == "__main__":
    print("Integration Test: Simplified Checker with Coordinator")
    print("=" * 70)
    
    success = test_coordinator_with_simplified_checker()
    
    print("\n" + "=" * 70)
    if success:
        print("INTEGRATION TEST PASSED!")
        print("Simplified Checker works correctly with Coordinator!")
    else:
        print("Integration test failed - check output above")
    print("=" * 70)