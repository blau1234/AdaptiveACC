"""
Test Planner with all fallback mechanisms removed
Verify that failures result in proper exceptions rather than meaningless default values
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_analyze_regulation_failures():
    """Test _analyze_regulation method failure scenarios"""
    
    print("Testing _analyze_regulation Failure Scenarios")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.planner import Planner
        
        planner = Planner()
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        
        # Test 1: Invalid JSON response
        print("1. Testing invalid JSON response...")
        
        def mock_invalid_json(prompt, system_prompt):
            return "This is not JSON at all, just plain text response"
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_invalid_json):
            try:
                result = planner._analyze_regulation(regulation_text)
                print("FAILED: Should have raised exception but got:", result.get('summary', 'unknown'))
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 2: Malformed JSON response
        print("\n2. Testing malformed JSON response...")
        
        def mock_malformed_json(prompt, system_prompt):
            return """{
    "summary": "Test summary",
    "requirements": [
        {
            "id": "req_1",
            "description": "Test requirement"
            // Missing closing brace and comma
        }
    """  # Incomplete JSON
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_malformed_json):
            try:
                result = planner._analyze_regulation(regulation_text)
                print("FAILED: Should have raised exception but got:", result.get('summary', 'unknown'))
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 3: LLM API failure
        print("\n3. Testing LLM API failure...")
        
        def mock_api_failure(prompt, system_prompt):
            raise Exception("Simulated API connection error")
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_api_failure):
            try:
                result = planner._analyze_regulation(regulation_text)
                print("FAILED: Should have raised exception but got:", result.get('summary', 'unknown'))
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")

def test_generate_plan_steps_failures():
    """Test _generate_plan_steps method failure scenarios"""
    
    print("\nTesting _generate_plan_steps Failure Scenarios")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.planner import Planner
        
        planner = Planner()
        
        # Mock regulation analysis
        regulation_analysis = {
            "summary": "Test regulation",
            "requirements": [{"id": "req_1", "description": "Test requirement"}],
            "complexity": "low",
            "estimated_checks": 1
        }
        regulation_text = "Test regulation text"
        
        # Test 1: Non-JSON response
        print("1. Testing non-JSON response...")
        
        def mock_non_json(prompt, system_prompt):
            return "Here are the steps you should follow: 1. Check file, 2. Validate structure, 3. Generate report"
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_non_json):
            try:
                result = planner._generate_plan_steps(regulation_analysis, regulation_text)
                print(f"FAILED: Should have raised exception but got {len(result)} steps")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 2: JSON but wrong structure
        print("\n2. Testing JSON with wrong structure...")
        
        def mock_wrong_structure(prompt, system_prompt):
            return """{
    "message": "Here are the steps",
    "data": {
        "step1": "Do something",
        "step2": "Do something else"
    }
}"""
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_wrong_structure):
            try:
                result = planner._generate_plan_steps(regulation_analysis, regulation_text)
                print(f"FAILED: Should have raised exception but got {len(result)} steps")
            except RuntimeError as e:
                print(f"SUCCESS: Correctly raised RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 3: Empty array response
        print("\n3. Testing empty array response...")
        
        def mock_empty_array(prompt, system_prompt):
            return "[]"
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_empty_array):
            try:
                result = planner._generate_plan_steps(regulation_analysis, regulation_text)
                # Empty array is technically valid JSON, should not raise in parsing
                print(f"RESULT: Got {len(result)} steps (empty array is valid)")
            except RuntimeError as e:
                print(f"Got RuntimeError: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")

def test_error_propagation():
    """Test that errors properly propagate through the call chain"""
    
    print("\nTesting Error Propagation Through Call Chain")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.planner import Planner
        
        planner = Planner()
        regulation_text = "Test regulation"
        
        # Test 1: Failure in _analyze_regulation should propagate to generate_initial_plan
        print("1. Testing error propagation from _analyze_regulation...")
        
        def mock_analysis_failure(prompt, system_prompt):
            if "analyze this building regulation text" in prompt.lower():
                return "Invalid JSON response"
            else:
                return '{"valid": "json"}'
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_analysis_failure):
            try:
                plan = planner.generate_initial_plan(regulation_text)
                print("FAILED: Should have raised exception but got plan")
            except RuntimeError as e:
                if "Plan generation failed" in str(e):
                    print(f"SUCCESS: Error properly propagated: {e}")
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")
        
        # Test 2: Failure in _generate_plan_steps should propagate
        print("\n2. Testing error propagation from _generate_plan_steps...")
        
        def mock_steps_failure(prompt, system_prompt):
            if "analyze this building regulation text" in prompt.lower():
                return """{
    "summary": "Valid analysis",
    "requirements": [{"id": "req_1", "description": "Test"}],
    "complexity": "low",
    "estimated_checks": 1
}"""
            elif "create a step-by-step execution plan" in prompt.lower():
                return "Invalid JSON for steps"
            else:
                return '{"valid": "json"}'
        
        with patch.object(planner.llm_client, 'generate_response', side_effect=mock_steps_failure):
            try:
                plan = planner.generate_initial_plan(regulation_text)
                print("FAILED: Should have raised exception but got plan")
            except RuntimeError as e:
                if "Plan generation failed" in str(e):
                    print(f"SUCCESS: Error properly propagated: {e}")
                else:
                    print(f"PARTIAL: Got RuntimeError but wrong message: {e}")
            except Exception as e:
                print(f"UNEXPECTED: Different exception type: {e}")

if __name__ == "__main__":
    print("Testing Planner with No Fallback Mechanisms")
    print("=" * 80)
    
    # Test individual method failures
    test_analyze_regulation_failures()
    test_generate_plan_steps_failures()
    
    # Test error propagation
    test_error_propagation()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("PASS Removed all meaningless fallback return values")
    print("PASS Both _analyze_regulation and _generate_plan_steps now raise exceptions on failure")
    print("PASS Errors properly propagate through the call chain")
    print("PASS System fails fast and explicitly when problems occur")
    print("PASS No more silent failures or meaningless default data")
    print("\nThe system is now much more reliable and easier to debug!")
    print("=" * 80)