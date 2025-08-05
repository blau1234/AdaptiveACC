"""
Test script to diagnose JSON parsing issues in analyze_regulation function
"""

import os
import sys
import json
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_analyze_regulation_with_real_api():
    """Test analyze_regulation with real API call to see actual response"""
    
    print("Testing analyze_regulation with Real API Call")
    print("=" * 60)
    
    try:
        # Set environment for testing
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'test_key'),
            'OPENAI_MODEL_NAME': 'gpt-4',
            'OPENAI_API_BASE': os.getenv('OPENAI_API_BASE', '')
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
            
            print("Calling analyze_regulation...")
            print("-" * 40)
            
            # Call the function and capture the response
            result = planner.analyze_regulation(regulation_text)
            
            print("-" * 40)
            print("Final result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Analyze the result
            print()
            print("Result Analysis:")
            print(f"- Type: {type(result)}")
            print(f"- Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            print(f"- Summary: {result.get('summary', 'N/A')}")
            print(f"- Requirements count: {len(result.get('requirements', []))}")
            
            if result.get('summary') == "Failed to parse regulation":
                print("❌ JSON parsing failed - fell back to default response")
                return False
            else:
                print("✅ JSON parsing succeeded")
                return True
                
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_mock_responses():
    """Test with different mock LLM responses to identify parsing issues"""
    
    print("\nTesting analyze_regulation with Mock Responses")
    print("=" * 60)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.planner import Planner
        
        planner = Planner()
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        
        # Test different response formats
        test_cases = [
            {
                "name": "Valid JSON Response",
                "response": """{
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
}""",
                "should_parse": True
            },
            {
                "name": "JSON with Extra Text",
                "response": """Here's the analysis:

{
    "summary": "Stairway width requirement",
    "requirements": [
        {
            "id": "req_1",
            "description": "Width requirement",
            "type": "accessibility",
            "measurable": true,
            "criteria": "Measure width"
        }
    ],
    "complexity": "low",
    "estimated_checks": 1
}

This analysis covers the main requirement.""",
                "should_parse": False
            },
            {
                "name": "Malformed JSON",
                "response": """{
    "summary": "Stairway requirement",
    "requirements": [
        {
            "id": "req_1",
            "description": "Width requirement",
            "type": "accessibility",
            "measurable": true,
            "criteria": "Measure width"
        }
    ],
    "complexity": "low",
    "estimated_checks": 1""",  # Missing closing brace
                "should_parse": False
            },
            {
                "name": "Non-JSON Response",
                "response": "The regulation requires stairways to have a minimum width of 36 inches. This is an accessibility requirement that can be measured.",
                "should_parse": False
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print("-" * 30)
            
            # Mock the LLM response
            with patch.object(planner.llm_client, 'generate_response', return_value=test_case['response']):
                result = planner.analyze_regulation(regulation_text)
                
                # Check if parsing succeeded or failed as expected
                parsing_succeeded = result.get('summary') != "Failed to parse regulation"
                expected_result = test_case['should_parse']
                
                print(f"Response preview: {test_case['response'][:100]}...")
                print(f"Expected to parse: {expected_result}")
                print(f"Actually parsed: {parsing_succeeded}")
                print(f"Result summary: {result.get('summary', 'N/A')}")
                
                if parsing_succeeded == expected_result:
                    print("✅ Test passed")
                else:
                    print("❌ Test failed")
                    if not parsing_succeeded and expected_result:
                        print("   JSON should have parsed but didn't")
                        # Try to identify the JSON parsing error
                        try:
                            json.loads(test_case['response'])
                            print("   Manual JSON parsing succeeded - check exception handling")
                        except json.JSONDecodeError as e:
                            print(f"   JSON parsing error: {e}")
                        except Exception as e:
                            print(f"   Other error: {e}")

def test_json_extraction():
    """Test if we can extract JSON from responses with extra text"""
    
    print("\nTesting JSON Extraction from Mixed Responses")
    print("=" * 60)
    
    import re
    
    def extract_json_from_response(response: str) -> str:
        """Try to extract JSON from a response that might contain extra text"""
        
        # Method 1: Look for JSON block between braces
        json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        if matches:
            # Take the largest match (most likely to be complete)
            largest_match = max(matches, key=len)
            return largest_match
        
        # Method 2: Look for lines that start and end with braces
        lines = response.strip().split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if line.strip().startswith('{'):
                in_json = True
                json_lines = [line]
            elif in_json:
                json_lines.append(line)
                if line.strip().endswith('}'):
                    break
        
        if json_lines:
            return '\n'.join(json_lines)
        
        return response  # Return original if no JSON found
    
    # Test cases
    test_responses = [
        """Here's my analysis of the regulation:

{
    "summary": "Test summary",
    "requirements": [],
    "complexity": "low",
    "estimated_checks": 1
}

Let me know if you need more details.""",
        
        """{
    "summary": "Direct JSON",
    "requirements": [],
    "complexity": "medium",
    "estimated_checks": 2
}""",
        
        """The regulation analysis is as follows:
        
{
    "summary": "Indented JSON",
    "requirements": [{"id": "req_1", "description": "test"}],
    "complexity": "high",
    "estimated_checks": 3
}

This covers all requirements."""
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\nTest {i}:")
        print("Original response:")
        print(f"'{response[:100]}...'")
        
        extracted = extract_json_from_response(response)
        print("Extracted JSON:")
        print(f"'{extracted}'")
        
        try:
            parsed = json.loads(extracted)
            print("✅ Parsing succeeded")
            print(f"Summary: {parsed.get('summary', 'N/A')}")
        except Exception as e:
            print(f"❌ Parsing failed: {e}")

if __name__ == "__main__":
    print("Analyzing JSON Parsing Issues in analyze_regulation")
    print("=" * 80)
    
    # Test with real API if available
    real_api_test = test_analyze_regulation_with_real_api()
    
    # Test with mock responses
    test_with_mock_responses()
    
    # Test JSON extraction techniques
    test_json_extraction()
    
    print("\n" + "=" * 80)
    print("Analysis complete. Check the output above for specific issues.")
    print("=" * 80)