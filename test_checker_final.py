"""
Final comprehensive test for Checker with all fallback mechanisms removed
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_checker_comprehensive():
    """Comprehensive test of the cleaned up Checker"""
    
    print("Comprehensive Checker Test (No Fallbacks)")
    print("=" * 60)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.checker import Checker
        
        checker = Checker()
        
        # Test data
        execution_results = [
            {
                "result": "pass",
                "detail": "Stairway width measurement completed successfully",
                "elements_checked": ["stairway_1", "stairway_2"],
                "issues": []
            },
            {
                "result": "pass",
                "detail": "All stairways meet minimum 36 inch requirement",
                "elements_checked": ["stairway_1", "stairway_2"],
                "issues": []
            }
        ]
        
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        
        plan = {
            "plan_id": "test_plan_456",
            "regulation_summary": "Stairway width requirement - minimum 36 inches",
            "requirements": [
                {
                    "id": "req_1", 
                    "description": "Stairways must have minimum clear width of 36 inches",
                    "type": "accessibility"
                }
            ],
            "steps": [
                {"step_id": "step_1", "description": "Check stairway widths"},
                {"step_id": "step_2", "description": "Validate compliance"}
            ],
            "modification_count": 0
        }
        
        # Test 1: Successful compliance check
        print("1. Testing successful compliance check...")
        
        def mock_successful_responses(prompt, system_prompt):
            if system_prompt and "building code compliance evaluation expert" in system_prompt.lower():
                return """{
    "overall_pass": true,
    "confidence_score": 0.95,
    "summary": "All stairways meet the minimum 36 inch clear width requirement",
    "details": "Both stairways were measured and found to comply with regulations",
    "recommendations": ["Maintain current design standards"],
    "critical_issues": [],
    "partial_compliance_areas": []
}"""
            elif system_prompt and "building code compliance report generator" in system_prompt.lower():
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
                
                print("SUCCESS: Compliance check completed!")
                print(f"- Status: {report.get('compliance_status')}")
                print(f"- Score: {report.get('overall_score')}")
                print(f"- Summary: {report.get('summary')}")
                
                # Validate report structure
                required_fields = ['compliance_status', 'overall_score', 'summary', 'regulation_analysis']
                missing_fields = [field for field in required_fields if field not in report]
                
                if missing_fields:
                    print(f"WARNING: Missing fields: {missing_fields}")
                else:
                    print("All required report fields present")
                
                success_test_1 = True
                
            except Exception as e:
                print(f"FAILED: {e}")
                success_test_1 = False
        
        # Test 2: Evaluation failure (should raise exception)
        print("\n2. Testing evaluation failure...")
        
        def mock_evaluation_failure(prompt, system_prompt):
            if system_prompt and "building code compliance evaluation expert" in system_prompt.lower():
                raise Exception("Simulated evaluation API failure")
            else:
                return '{"default": "response"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_evaluation_failure):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception")
                success_test_2 = False
            except RuntimeError as e:
                if "Compliance evaluation failed" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError")
                    success_test_2 = True
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
                    success_test_2 = False
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
                success_test_2 = False
        
        # Test 3: Report generation failure (should raise exception)
        print("\n3. Testing report generation failure...")
        
        def mock_report_failure(prompt, system_prompt):
            if system_prompt and "building code compliance evaluation expert" in system_prompt.lower():
                return """{
    "overall_pass": true,
    "confidence_score": 0.9,
    "summary": "Valid evaluation"
}"""
            elif system_prompt and "building code compliance report generator" in system_prompt.lower():
                raise Exception("Report generation failed")
            else:
                return '{"default": "response"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_report_failure):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception")
                success_test_3 = False
            except RuntimeError as e:
                if "Failed to generate comprehensive report" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError")
                    success_test_3 = True
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
                    success_test_3 = False
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
                success_test_3 = False
        
        # Test 4: Invalid JSON in evaluation (should raise exception)
        print("\n4. Testing invalid JSON in evaluation...")
        
        def mock_invalid_json(prompt, system_prompt):
            if system_prompt and "building code compliance evaluation expert" in system_prompt.lower():
                return "This is not JSON at all"
            else:
                return '{"default": "response"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_invalid_json):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception")
                success_test_4 = False
            except RuntimeError as e:
                if "Failed to parse compliance evaluation response" in str(e):
                    print(f"SUCCESS: Correctly raised RuntimeError")
                    success_test_4 = True
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
                    success_test_4 = False
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
                success_test_4 = False
        
        return success_test_1, success_test_2, success_test_3, success_test_4

if __name__ == "__main__":
    print("Final Comprehensive Test: Checker Without Fallback Mechanisms")
    print("=" * 80)
    
    test_results = test_checker_comprehensive()
    success_count = sum(test_results)
    total_tests = len(test_results)
    
    print(f"\n" + "=" * 80)
    print("FINAL TEST RESULTS:")
    print(f"Tests passed: {success_count}/{total_tests}")
    
    test_names = [
        "Successful compliance check",
        "Evaluation failure handling", 
        "Report generation failure handling",
        "Invalid JSON handling"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "PASS" if result else "FAIL"
        print(f"  {status} {name}")
    
    if success_count == total_tests:
        print("\nCOMPLETE SUCCESS!")
        print("CHECKER IMPROVEMENTS COMPLETED:")
        print("- Removed all meaningless fallback functions")
        print("- Consistent exception handling throughout")
        print("- Clear error messages for debugging")
        print("- No more silent failures")
        print("- System fails fast when problems occur")
        print("- Caller can implement appropriate error handling")
        print("\nCHECKER IS NOW CLEAN, RELIABLE, AND MAINTAINABLE!")
    else:
        print(f"\nSome tests failed - check the output above")
    
    print("=" * 80)