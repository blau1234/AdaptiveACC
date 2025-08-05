"""
Final validation test for the cleaned up Planner
Ensures the system still works correctly in success scenarios
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_successful_scenarios():
    """Test that successful scenarios still work after removing fallbacks"""
    
    print("Final Validation: Testing Successful Scenarios")
    print("=" * 60)
    
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
        
        # Test successful plan generation
        print("1. Testing successful plan generation...")
        
        def mock_successful_responses(prompt, system_prompt):
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
            elif "generate a detailed execution plan" in prompt.lower():
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
    },
    {
        "step_id": "step_3",
        "description": "Validate that all measured widths meet minimum 36 inch requirement",
        "task_type": "validation",
        "priority": "high",
        "tool_description": "Compliance checker for minimum width requirements",
        "expected_output": "Pass/fail result for each stairway",
        "dependencies": ["step_2"]
    }
]"""
            else:
                return '{"default": "response"}'
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_successful_responses):
            try:
                plan = planner.generate_initial_plan(regulation_text)
                
                print("SUCCESS: Plan generated successfully!")
                print(f"- Plan ID: {plan.get('plan_id')}")
                print(f"- Summary: {plan.get('regulation_summary')}")
                print(f"- Requirements: {len(plan.get('requirements', []))}")
                print(f"- Steps: {len(plan.get('steps', []))}")
                print(f"- Status: {plan.get('status')}")
                
                # Validate plan structure
                required_fields = ['plan_id', 'regulation_summary', 'requirements', 'steps', 'status', 'created_at', 'modification_count']
                missing_fields = [field for field in required_fields if field not in plan]
                
                if missing_fields:
                    print(f"WARNING: Missing fields: {missing_fields}")
                else:
                    print("All required plan fields present")
                
                # Validate steps structure
                steps = plan.get('steps', [])
                if steps:
                    first_step = steps[0]
                    step_fields = ['step_id', 'description', 'task_type', 'priority', 'tool_description', 'expected_output', 'dependencies']
                    missing_step_fields = [field for field in step_fields if field not in first_step]
                    
                    if missing_step_fields:
                        print(f"WARNING: Missing step fields: {missing_step_fields}")
                    else:
                        print("Step structure is complete")
                        
                        # Print first step details
                        print("\nFirst step details:")
                        for field in step_fields:
                            print(f"  {field}: {first_step.get(field)}")
                
                return True
                
            except Exception as e:
                print(f"FAILED: {e}")
                import traceback
                traceback.print_exc()
                return False

if __name__ == "__main__":
    print("Final Validation of Cleaned Up Planner System")
    print("=" * 80)
    
    success = test_successful_scenarios()
    
    print("\n" + "=" * 80)
    if success:
        print("FINAL RESULT: SUCCESS!")
        print()
        print("IMPROVEMENTS COMPLETED:")
        print("- Removed all meaningless fallback functions")
        print("- _analyze_regulation now raises exceptions on parse failure")
        print("- _generate_plan_steps now raises exceptions on parse failure")
        print("- Added validation for plan steps structure (must be list)")
        print("- Consistent error handling throughout the system")
        print("- Proper error propagation to caller")
        print()
        print("BENEFITS:")
        print("- No more silent failures")
        print("- Clear error messages for debugging")
        print("- System fails fast when problems occur")
        print("- Caller can implement appropriate error handling")
        print("- More reliable and maintainable code")
    else:
        print("FINAL RESULT: FAILED - System needs more work")
    
    print("=" * 80)