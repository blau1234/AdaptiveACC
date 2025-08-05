"""
Test the cleaned up Planner after removing fallback functions
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_cleaned_planner():
    """Test the cleaned up Planner functionality"""
    
    print("Testing Cleaned Up Planner")
    print("=" * 40)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.planner import Planner
        
        # Read regulation text
        regulation_file = os.path.join("test_regulation", "1.txt")
        with open(regulation_file, 'r', encoding='utf-8') as f:
            regulation_text = f.read().strip()
        
        print(f"Regulation text: '{regulation_text}'")
        print()
        
        # Initialize Planner
        planner = Planner()
        print("Planner initialized successfully")
        
        # Test 1: Successful plan generation
        print("\n1. Testing successful plan generation...")
        
        def mock_successful_response(prompt, system_prompt):
            if "analyze this building regulation text" in prompt.lower():
                return """{
    "summary": "Stairway width requirement - minimum 36 inches clear width",
    "requirements": [
        {
            "id": "req_1",
            "description": "Stairways must have minimum clear width of 36 inches",
            "type": "accessibility",
            "measurable": true,
            "criteria": "Measure clear width at narrowest point"
        }
    ],
    "complexity": "low",
    "estimated_checks": 2
}"""
            elif "create a step-by-step execution plan" in prompt.lower():
                return """[
    {
        "step_id": "step_1",
        "description": "Identify and locate all stairways in the IFC file",
        "task_type": "element_check",
        "priority": "high",
        "tool_description": "IFC element scanner to find all stairway objects",
        "expected_output": "List of all stairway elements with IDs",
        "dependencies": []
    },
    {
        "step_id": "step_2",
        "description": "Measure clear width of each identified stairway",
        "task_type": "measurement",
        "priority": "high",
        "tool_description": "Width measurement tool with millimeter precision",
        "expected_output": "Width measurements for each stairway in inches",
        "dependencies": ["step_1"]
    }
]"""
            else:
                return "Mock response"
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_successful_response):
            try:
                plan = planner.generate_initial_plan(regulation_text)
                print(f"SUCCESS: Generated plan with {len(plan.get('steps', []))} steps")
                print(f"Plan ID: {plan.get('plan_id')}")
                print(f"Summary: {plan.get('regulation_summary')}")
            except Exception as e:
                print(f"FAILED: {e}")
        
        # Test 2: Failed plan generation (no fallback)
        print("\n2. Testing failed plan generation (should raise exception)...")
        
        def mock_failing_response(prompt, system_prompt):
            raise Exception("Simulated LLM API failure")
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_failing_response):
            try:
                plan = planner.generate_initial_plan(regulation_text)
                print("FAILED: Should have raised exception but didn't")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Raised different exception: {e}")
        
        # Test 3: Plan modification
        print("\n3. Testing plan modification...")
        
        # Create a mock current plan
        current_plan = {
            "plan_id": "test_plan_123",
            "regulation_summary": "Test regulation",
            "requirements": [],
            "steps": [
                {
                    "step_id": "step_1",
                    "description": "Original step",
                    "task_type": "validation",
                    "priority": "high"
                }
            ],
            "status": "initial",
            "modification_count": 0
        }
        
        feedback = {
            "issue_type": "tool_failure",
            "issue_description": "Tool not available",
            "step_index": 0
        }
        
        def mock_modification_response(prompt, system_prompt):
            return """{
    "plan_id": "test_plan_123",
    "regulation_summary": "Test regulation",
    "requirements": [],
    "steps": [
        {
            "step_id": "step_1",
            "description": "Modified step - use alternative tool",
            "task_type": "validation",
            "priority": "high"
        }
    ]
}"""
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_modification_response):
            try:
                modified_plan = planner.modify_plan(current_plan, feedback)
                print(f"SUCCESS: Modified plan")
                print(f"Modification count: {modified_plan.get('modification_count')}")
                print(f"Modified step: {modified_plan['steps'][0]['description']}")
            except Exception as e:
                print(f"FAILED: {e}")
        
        # Test 4: Failed plan modification (should raise exception)
        print("\n4. Testing failed plan modification...")
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_failing_response):
            try:
                modified_plan = planner.modify_plan(current_plan, feedback)
                print("FAILED: Should have raised exception but didn't")
            except Exception as e:
                print(f"SUCCESS: Correctly handled failure: {e}")

if __name__ == "__main__":
    print("Testing Cleaned Up Planner (No Fallback Functions)")
    print("=" * 60)
    
    test_cleaned_planner()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("- Removed fallback plan functions")
    print("- Now raises exceptions instead of returning dummy plans")
    print("- Cleaner error handling - let caller decide what to do")
    print("- More reliable system - failures are explicit, not hidden")
    print("=" * 60)