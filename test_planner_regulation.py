"""
Test script for Planner's generate_initial_plan functionality
Using regulation text from test_regulation/1.txt
"""

import os
import sys
import json
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_planner_with_regulation():
    """Test Planner's generate_initial_plan with regulation text from 1.txt"""
    
    print("Testing Planner's generate_initial_plan functionality")
    print("=" * 60)
    
    try:
        # Mock the environment for testing
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_key_for_planner', 
            'OPENAI_MODEL_NAME': 'gpt-4'
        }):
            
            # Import after setting environment
            from agents.planner import Planner
            
            # Read regulation text from test file
            regulation_file = os.path.join("test_regulation", "1.txt")
            with open(regulation_file, 'r', encoding='utf-8') as f:
                regulation_text = f.read().strip()
            
            print(f"Regulation text loaded:")
            print(f"   '{regulation_text}'")
            print()
            
            # Initialize Planner
            planner = Planner()
            print("Planner initialized successfully")
            
            # Mock the LLM client's generate_response method to avoid actual API calls
            def mock_regulation_analysis_response(prompt, system_prompt):
                if "analyze this building regulation text" in prompt.lower():
                    return json.dumps({
                        "summary": "Stairway width requirement - minimum 36 inches clear width",
                        "requirements": [
                            {
                                "id": "req_1",
                                "description": "Stairways must have minimum clear width of 36 inches",
                                "type": "accessibility",
                                "measurable": True,
                                "criteria": "Measure clear width at narrowest point"
                            }
                        ],
                        "complexity": "low",
                        "estimated_checks": 2
                    })
                elif "create a step-by-step execution plan" in prompt.lower():
                    return json.dumps([
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
                    ])
                else:
                    return "Mock response"
            
            # Apply the mock
            with patch.object(planner.llm_client, 'generate_response', side_effect=mock_regulation_analysis_response):
                
                print("Generating initial plan...")
                plan = planner.generate_initial_plan(regulation_text)
                
                print("Plan generated successfully!")
                print()
                
                # Display plan details
                print("Generated Plan Details:")
                print("=" * 40)
                print(f"Plan ID: {plan.get('plan_id', 'N/A')}")
                print(f"Status: {plan.get('status', 'N/A')}")
                print(f"Regulation Summary: {plan.get('regulation_summary', 'N/A')}")
                print(f"Requirements Count: {len(plan.get('requirements', []))}")
                print(f"Steps Count: {len(plan.get('steps', []))}")
                print(f"Created At: {plan.get('created_at', 'N/A')}")
                print()
                
                # Display requirements
                requirements = plan.get('requirements', [])
                if requirements:
                    print("Requirements:")
                    for i, req in enumerate(requirements, 1):
                        print(f"  {i}. ID: {req.get('id', 'N/A')}")
                        print(f"     Description: {req.get('description', 'N/A')}")
                        print(f"     Type: {req.get('type', 'N/A')}")
                        print(f"     Measurable: {req.get('measurable', 'N/A')}")
                        print()
                
                # Display steps
                steps = plan.get('steps', [])
                if steps:
                    print("Execution Steps:")
                    for i, step in enumerate(steps, 1):
                        print(f"  Step {i}: {step.get('step_id', 'N/A')}")
                        print(f"    Description: {step.get('description', 'N/A')}")
                        print(f"    Task Type: {step.get('task_type', 'N/A')}")
                        print(f"    Priority: {step.get('priority', 'N/A')}")
                        print(f"    Tool Description: {step.get('tool_description', 'N/A')}")
                        print(f"    Expected Output: {step.get('expected_output', 'N/A')}")
                        print(f"    Dependencies: {step.get('dependencies', [])}")
                        print()
                
                # Validate plan structure
                print("Plan Validation:")
                print("=" * 30)
                
                validation_results = {
                    "Has plan_id": bool(plan.get('plan_id')),
                    "Has regulation_summary": bool(plan.get('regulation_summary')),
                    "Has requirements": len(plan.get('requirements', [])) > 0,
                    "Has steps": len(plan.get('steps', [])) > 0,
                    "Has status": bool(plan.get('status')),
                    "Has creation_time": bool(plan.get('created_at')),
                    "Modification count initialized": plan.get('modification_count') == 0
                }
                
                for check, result in validation_results.items():
                    status = "PASS" if result else "FAIL"
                    print(f"  {status} {check}: {result}")
                
                all_passed = all(validation_results.values())
                print()
                print(f"Overall validation: {'PASSED' if all_passed else 'FAILED'}")
                
                # Save plan to file for inspection
                output_file = "test_planner_output.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(plan, f, ensure_ascii=False, indent=2)
                print(f"Plan saved to: {output_file}")
                
                return True
                
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_planner_with_regulation()
    print()
    print("=" * 60)
    if success:
        print("Planner test completed successfully!")
    else:
        print("Planner test failed!")
    print("=" * 60)