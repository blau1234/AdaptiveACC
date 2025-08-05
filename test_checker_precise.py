"""
Precise test for Checker to identify where exceptions should be raised
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_checker_step_by_step():
    """Test each step of checker individually"""
    
    print("Testing Checker Step by Step")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.checker import Checker
        
        checker = Checker()
        
        # Mock data
        execution_results = [{"result": "pass", "detail": "Test"}]
        regulation_text = "Test regulation"
        plan = {"plan_id": "test", "steps": []}
        
        print("1. Testing _analyze_execution_results (this should work)...")
        try:
            analysis = checker._analyze_execution_results(execution_results, plan)
            print(f"SUCCESS: Analysis completed with {analysis['total_steps']} steps")
        except Exception as e:
            print(f"FAILED: Analysis failed: {e}")
            return
        
        print("\n2. Testing _evaluate_compliance with valid response...")
        
        def mock_valid_evaluation(prompt, system_prompt):
            return """{
    "overall_pass": true,
    "confidence_score": 0.9,
    "summary": "Test passed"
}"""
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_valid_evaluation):
            try:
                evaluation = checker._evaluate_compliance(analysis, regulation_text, plan)
                print(f"SUCCESS: Evaluation completed: {evaluation.get('summary')}")
            except Exception as e:
                print(f"FAILED: Evaluation failed: {e}")
                return
        
        print("\n3. Testing _evaluate_compliance with invalid JSON (should fail)...")
        
        def mock_invalid_evaluation(prompt, system_prompt):
            return "This is not JSON"
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_invalid_evaluation):
            try:
                evaluation = checker._evaluate_compliance(analysis, regulation_text, plan)
                print("FAILED: Should have raised exception but didn't")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception: {e}")
        
        print("\n4. Testing _evaluate_compliance with API failure (should fail)...")
        
        def mock_api_failure(prompt, system_prompt):
            raise Exception("Simulated API failure")
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_api_failure):
            try:
                evaluation = checker._evaluate_compliance(analysis, regulation_text, plan)
                print("FAILED: Should have raised exception but didn't")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception: {e}")
        
        print("\n5. Testing _generate_comprehensive_report with valid evaluation...")
        
        valid_evaluation = {
            "overall_pass": True,
            "confidence_score": 0.9, 
            "summary": "Test evaluation"
        }
        
        def mock_valid_report(prompt, system_prompt):
            return """{
    "compliance_status": "pass",
    "overall_score": 0.9,
    "summary": "Test report"
}"""
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_valid_report):
            try:
                report = checker._generate_comprehensive_report(analysis, valid_evaluation, regulation_text, plan)
                print(f"SUCCESS: Report generated: {report.get('summary')}")
            except Exception as e:
                print(f"FAILED: Report generation failed: {e}")
        
        print("\n6. Testing _generate_comprehensive_report with API failure (should fail)...")
        
        def mock_report_failure(prompt, system_prompt):
            raise Exception("Report generation API failure")
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_report_failure):
            try:
                report = checker._generate_comprehensive_report(analysis, valid_evaluation, regulation_text, plan)
                print("FAILED: Should have raised exception but didn't")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception: {e}")

def test_full_check_method():
    """Test the full check method with controlled failures"""
    
    print("\nTesting Full Check Method")
    print("=" * 30)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.checker import Checker
        
        checker = Checker()
        
        execution_results = [{"result": "pass", "detail": "Test"}]
        regulation_text = "Test regulation"
        plan = {"plan_id": "test", "steps": []}
        
        print("1. Testing with evaluation failure...")
        
        def mock_evaluation_failure(prompt, system_prompt):
            print(f"Mock called with prompt containing: {prompt[:50]}...")
            print(f"System prompt contains: {system_prompt[:50] if system_prompt else 'None'}...")
            if system_prompt and "building code compliance evaluation expert" in system_prompt.lower():
                print("Triggering evaluation failure...")
                raise Exception("Evaluation failed")
            else:
                print("Returning default response...")
                return '{"default": "response"}'
        
        with patch.object(checker.llm_client, 'generate_response', side_effect=mock_evaluation_failure):
            try:
                report = checker.check(execution_results, regulation_text, plan)
                print("FAILED: Should have raised exception")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception: {e}")

if __name__ == "__main__":
    print("Precise Checker Testing")
    print("=" * 60)
    
    test_checker_step_by_step()
    test_full_check_method()
    
    print("\n" + "=" * 60)
    print("This test helps identify exactly where exceptions should be raised")
    print("=" * 60)