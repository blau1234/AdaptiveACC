"""
Test the simplified Checker implementation
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simplified_checker():
    """Test the simplified Checker functionality"""
    
    print("Testing Simplified Checker")
    print("=" * 40)
    
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
                "detail": "Stairway width check passed",
                "elements_checked": ["stairway_1", "stairway_2"],
                "issues": []
            },
            {
                "result": "fail",
                "detail": "One stairway too narrow",
                "elements_checked": ["stairway_3"],
                "issues": ["Width only 32 inches, requires 36 inches"]
            }
        ]
        
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        plan = {"plan_id": "test_plan"}
        
        print("1. Testing check_and_report method...")
        
        def mock_successful_response(prompt, system_prompt):
            return """{
    "compliant": false,
    "confidence": 0.9,
    "summary": "One stairway fails to meet minimum width requirement",
    "violations": [
        {
            "requirement": "Minimum 36 inch clear width",
            "severity": "critical",
            "details": "Stairway_3 measured only 32 inches wide"
        }
    ],
    "passed_checks": [
        "Stairway_1 and Stairway_2 meet width requirements"
    ],
    "recommendations": [
        "Widen stairway_3 to meet minimum 36 inch requirement",
        "Review construction plans for compliance"
    ]
}"""
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_successful_response):
            try:
                report = checker.check_and_report(execution_results, regulation_text, plan)
                
                print("SUCCESS: Report generated!")
                print(f"- Report ID: {report.get('report_id')}")
                print(f"- Status: {report['executive_summary']['status']}")
                print(f"- Confidence: {report['executive_summary']['confidence']}")
                print(f"- Critical Issues: {report['executive_summary']['critical_issues']}")
                print(f"- Violations: {len(report['compliance_details']['violations'])}")
                print(f"- Recommendations: {len(report['recommendations']['immediate_actions']) + len(report['recommendations']['long_term_improvements'])}")
                
                # Test export functionality
                json_export = checker.export_report(report, "json")
                print(f"- JSON Export Length: {len(json_export)} characters")
                
                return True
                
            except Exception as e:
                print(f"FAILED: {e}")
                import traceback
                traceback.print_exc()
                return False

def test_error_handling():
    """Test error handling in simplified checker"""
    
    print("\n2. Testing error handling...")
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.checker import Checker
        
        checker = Checker()
        
        execution_results = [{"result": "pass", "detail": "Test"}]
        regulation_text = "Test regulation"
        
        # Test LLM failure (should raise exception)
        def mock_failure(prompt, system_prompt):
            raise Exception("Simulated API failure")
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_failure):
            try:
                evaluation = checker.evaluate_compliance(execution_results, regulation_text)
                print("FAILED: Should have raised exception")
                return False
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
                return True
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
                return False

def test_export_formats():
    """Test export functionality"""
    
    print("\n3. Testing export formats...")
    
    from agents.checker import Checker
    
    checker = Checker()
    
    # Mock report
    report = {
        "report_id": "test_report",
        "executive_summary": {"status": "COMPLIANT"},
        "compliance_details": {"violations": []},
        "recommendations": {"immediate_actions": []}
    }
    
    # Test JSON export (should work)
    try:
        json_result = checker.export_report(report, "json")
        print("SUCCESS: JSON export works")
        json_test = True
    except Exception as e:
        print(f"FAILED: JSON export failed: {e}")
        json_test = False
    
    # Test unsupported format (should raise exception)
    try:
        html_result = checker.export_report(report, "html")
        print("FAILED: Should have raised exception for HTML")
        format_test = False
    except ValueError as e:
        print(f"SUCCESS: Correctly rejected unsupported format: {e}")
        format_test = True
    except Exception as e:
        print(f"UNEXPECTED: Different exception: {e}")
        format_test = False
    
    return json_test and format_test

if __name__ == "__main__":
    print("Testing Simplified Checker Implementation")
    print("=" * 60)
    
    # Run tests
    test1 = test_simplified_checker()
    test2 = test_error_handling()
    test3 = test_export_formats()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print(f"- Basic functionality: {'PASS' if test1 else 'FAIL'}")
    print(f"- Error handling: {'PASS' if test2 else 'FAIL'}")
    print(f"- Export formats: {'PASS' if test3 else 'FAIL'}")
    
    if all([test1, test2, test3]):
        print("\nALL TESTS PASSED!")
        print("Simplified Checker is working correctly!")
    else:
        print("\nSome tests failed - check output above")
    
    print("=" * 60)