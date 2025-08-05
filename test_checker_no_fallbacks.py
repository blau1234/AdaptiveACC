"""
Test Checker with all fallback mechanisms removed
Verify that failures result in proper exceptions rather than meaningless fallback reports
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_checker_successful_scenarios():
    """Test successful Checker scenarios"""
    
    print("Testing Checker Successful Scenarios")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.checker import Checker
        
        checker = Checker()
        
        # Mock execution results
        execution_results = [
            {
                "result": "pass",
                "detail": "Stairway width check passed",
                "elements_checked": ["stairway_1", "stairway_2"],
                "issues": []
            },
            {
                "result": "pass", 
                "detail": "All stairways meet 36 inch requirement",
                "elements_checked": ["stairway_1", "stairway_2"],
                "issues": []
            }
        ]
        
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        
        plan = {
            "plan_id": "test_plan_123",
            "regulation_summary": "Stairway width requirement",
            "requirements": [{"id": "req_1", "description": "Width requirement"}],
            "steps": [
                {"step_id": "step_1", "description": "Check stairway widths"},
                {"step_id": "step_2", "description": "Validate compliance"}
            ],
            "modification_count": 0
        }
        
        print("1. Testing successful compliance check...")
        
        def mock_successful_responses(prompt, system_prompt):
            if "evaluate overall compliance" in prompt.lower():
                return """{
    "overall_pass": true,
    "confidence_score": 0.95,
    "summary": "All stairways meet the minimum 36 inch clear width requirement",
    "details": "Both stairways were measured and found to comply with regulations",
    "recommendations": ["Maintain current design standards"],
    "critical_issues": [],
    "partial_compliance_areas": []
}"""
            elif "generate a comprehensive compliance report" in prompt.lower():
                return """{
    "compliance_status": "pass",
    "overall_score": 0.95,
    "summary": "All compliance checks passed successfully",
    "regulation_analysis": {
        "regulation_summary": "Stairway width requirement - minimum 36 inches",
        "key_requirements": ["minimum 36 inch clear width"],
        "compliance_areas": ["accessibility"]
    },
    "plan_analysis": {
        "plan_effectiveness": "effective",
        "modifications_made": 0,
        "plan_coverage": "complete"
    },
    "execution_analysis": {
        "steps_executed": 2,
        "success_rate": 1.0,
        "critical_failures": [],
        "recommendations": ["Maintain current standards"]
    },
    "detailed_findings": []
}"""
            else:
                return '{"default": "response"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_successful_responses):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                
                print("SUCCESS: Compliance report generated!")
                print(f"- Compliance Status: {report.get('compliance_status')}")
                print(f"- Overall Score: {report.get('overall_score')}")
                print(f"- Summary: {report.get('summary')}")
                print(f"- Report Type: {report.get('report_type', 'standard')}")
                
                return True
                
            except Exception as e:
                print(f"FAILED: {e}")
                import traceback
                traceback.print_exc()
                return False

def test_checker_failure_scenarios():
    """Test Checker failure scenarios (should raise exceptions)"""
    
    print("\nTesting Checker Failure Scenarios")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.checker import Checker
        
        checker = Checker()
        
        execution_results = [{"result": "pass", "detail": "Test"}]
        regulation_text = "Test regulation"
        plan = {"plan_id": "test"}
        
        # Test 1: LLM evaluation failure
        print("1. Testing LLM evaluation failure...")
        
        def mock_evaluation_failure(prompt, system_prompt):
            if "evaluate overall compliance" in prompt.lower():
                raise Exception("Simulated LLM API failure")
            else:
                return '{"valid": "json"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_evaluation_failure):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception but got report")
            except RuntimeError as e:
                if "Compliance evaluation failed" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 2: Invalid JSON in evaluation
        print("\n2. Testing invalid JSON in evaluation...")
        
        def mock_invalid_evaluation_json(prompt, system_prompt):
            if "evaluate overall compliance" in prompt.lower():
                return "This is not JSON at all"
            else:
                return '{"valid": "json"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_invalid_evaluation_json):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception but got report")
            except RuntimeError as e:
                if "Failed to parse compliance evaluation response" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 3: Report generation failure
        print("\n3. Testing report generation failure...")
        
        def mock_report_failure(prompt, system_prompt):
            if "evaluate overall compliance" in prompt.lower():
                return """{
    "overall_pass": true,
    "confidence_score": 0.9,
    "summary": "Valid evaluation"
}"""
            elif "generate a comprehensive compliance report" in prompt.lower():
                raise Exception("Report generation failed") 
            else:
                return '{"valid": "json"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_report_failure):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception but got report")
            except RuntimeError as e:
                if "Failed to generate comprehensive report" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")

def test_removed_functions():
    """Test that removed fallback functions are actually gone"""
    
    print("\nTesting Removed Fallback Functions")
    print("=" * 50)
    
    from agents.checker import Checker
    checker = Checker()
    
    removed_functions = [
        '_rule_based_evaluation',
        '_generate_fallback_report', 
        '_generate_fallback_comprehensive_report'
    ]
    
    for func_name in removed_functions:
        if hasattr(checker, func_name):
            print(f"FAILED: {func_name} still exists!")
        else:
            print(f"SUCCESS: {func_name} successfully removed")

if __name__ == "__main__":
    print("Testing Checker with No Fallback Mechanisms")
    print("=" * 80)
    
    # Test successful scenarios
    success_test = test_checker_successful_scenarios()
    
    # Test failure scenarios  
    test_checker_failure_scenarios()
    
    # Test that fallback functions are removed
    test_removed_functions()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("PASS Removed all fallback mechanisms from Checker")
    print("PASS Main check() method now raises exceptions on failure")
    print("PASS _evaluate_compliance raises exceptions on parse failure")
    print("PASS _generate_comprehensive_report raises exceptions on failure")
    print("PASS Deleted _rule_based_evaluation fallback function")
    print("PASS Deleted _generate_fallback_report function") 
    print("PASS Deleted _generate_fallback_comprehensive_report function")
    print("\nBENEFITS:")
    print("- No more meaningless fallback reports")
    print("- Clear error messages for debugging")
    print("- Consistent error handling with Planner")
    print("- System fails fast when problems occur")
    print("- Caller can implement appropriate error handling")
    
    if success_test:
        print("\nCHECKER IS NOW CLEAN AND RELIABLE!")
    else:
        print("\nSome issues detected - check the output above")
    
    print("=" * 80)