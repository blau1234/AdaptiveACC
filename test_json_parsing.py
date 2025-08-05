"""
Direct test for _analyze_regulation JSON parsing issues
"""

import os
import sys
import json
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_analyze_regulation_json_parsing():
    """Test the _analyze_regulation method directly"""
    
    print("Testing _analyze_regulation JSON Parsing")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.planner import Planner
        
        planner = Planner()
        regulation_text = "The minimum clear width of stairways shall be 36 inches."
        
        print(f"Regulation text: '{regulation_text}'")
        print()
        
        # Test cases with different LLM responses
        test_cases = [
            {
                "name": "Perfect JSON Response",
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
                "expected_to_parse": True
            },
            {
                "name": "JSON with Extra Text Before",
                "response": """Based on the regulation analysis, here is the extracted information:

{
    "summary": "Stairway width requirement",
    "requirements": [
        {
            "id": "req_1",
            "description": "Width requirement for stairways",
            "type": "accessibility", 
            "measurable": true,
            "criteria": "Measure width"
        }
    ],
    "complexity": "low",
    "estimated_checks": 1
}""",
                "expected_to_parse": False  # Current implementation can't handle extra text
            },
            {
                "name": "JSON with Extra Text After",
                "response": """{
    "summary": "Stairway width requirement",
    "requirements": [
        {
            "id": "req_1",
            "description": "Width requirement",
            "type": "accessibility",
            "measurable": true,
            "criteria": "Width measurement"
        }
    ],
    "complexity": "low",
    "estimated_checks": 1
}

This analysis covers the main requirement for stairway width.""",
                "expected_to_parse": False  # Current implementation can't handle extra text
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
                "expected_to_parse": False
            },
            {
                "name": "Non-JSON Response",
                "response": "The regulation requires stairways to have a minimum clear width of 36 inches. This is an accessibility requirement that can be measured by checking the narrowest point of each stairway.",
                "expected_to_parse": False
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. Testing: {test_case['name']}")
            print("-" * 40)
            
            # Mock the LLM response
            with patch.object(planner.llm_client, 'generate_response', return_value=test_case['response']):
                # Call the private method directly
                result = planner._analyze_regulation(regulation_text)
                
                # Check if parsing succeeded or failed
                parsing_succeeded = result.get('summary') != "Failed to parse regulation"
                expected = test_case['expected_to_parse']
                
                print(f"Response preview: {test_case['response'][:100]}...")
                print(f"Expected to parse: {expected}")
                print(f"Actually parsed: {parsing_succeeded}")
                print(f"Result summary: {result.get('summary', 'N/A')}")
                
                # Store result for analysis
                results.append({
                    'name': test_case['name'],
                    'expected': expected,
                    'actual': parsing_succeeded,
                    'passed': expected == parsing_succeeded,
                    'result': result
                })
                
                if expected == parsing_succeeded:
                    print("PASS Test PASSED")
                else:
                    print("FAIL Test FAILED")
                    
                    # If it should have parsed but didn't, try to diagnose
                    if expected and not parsing_succeeded:
                        print("   Diagnosing JSON parsing failure...")
                        try:
                            manual_parse = json.loads(test_case['response'])
                            print("   Manual JSON parsing succeeded - issue in exception handling")
                        except json.JSONDecodeError as e:
                            print(f"   JSON parsing error: {e}")
                            print(f"   Error at position: {e.pos}")
                            print(f"   Problem area: '{test_case['response'][max(0, e.pos-10):e.pos+10]}'")
                
                print()
        
        # Summary
        print("=" * 50)
        print("SUMMARY:")
        passed_count = sum(1 for r in results if r['passed'])
        total_count = len(results)
        
        print(f"Tests passed: {passed_count}/{total_count}")
        
        for result in results:
            status = "PASS" if result['passed'] else "FAIL"
            print(f"  {status} {result['name']}")
        
        if passed_count == total_count:
            print("\nAll tests passed!")
        else:
            print(f"\n{total_count - passed_count} test(s) failed")
            
        return results

def test_json_extraction_improvement():
    """Test improved JSON extraction from mixed responses"""
    
    print("\nTesting Improved JSON Extraction")
    print("=" * 50)
    
    import re
    
    def extract_json_from_response(response: str) -> str:
        """Extract JSON from response that may contain extra text"""
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        # If it starts and ends with braces, try as-is first
        if response.startswith('{') and response.endswith('}'):
            return response
        
        # Look for JSON block between braces
        json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        if matches:
            # Take the largest match (most likely to be complete)
            largest_match = max(matches, key=len)
            return largest_match
        
        return response  # Return original if no JSON found
    
    test_responses = [
        """Here's the analysis:

{
    "summary": "Test summary",
    "requirements": [],
    "complexity": "low",
    "estimated_checks": 1
}

Hope this helps!""",
        
        """{
    "summary": "Direct JSON",
    "requirements": [],
    "complexity": "medium", 
    "estimated_checks": 2
}""",
        
        """Based on my analysis:
        
    {
        "summary": "Indented JSON",
        "requirements": [{"id": "req_1", "description": "test"}],
        "complexity": "high",
        "estimated_checks": 3
    }

That covers everything."""
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"Test {i}:")
        print(f"Original: {response[:50]}...")
        
        extracted = extract_json_from_response(response)
        print(f"Extracted: {extracted[:50]}...")
        
        try:
            parsed = json.loads(extracted)
            print("PASS Extraction and parsing succeeded")
            print(f"   Summary: {parsed.get('summary', 'N/A')}")
        except Exception as e:
            print(f"FAIL Extraction failed: {e}")
        print()

if __name__ == "__main__":
    print("JSON Parsing Diagnostic for _analyze_regulation")
    print("=" * 70)
    
    # Test current implementation
    results = test_analyze_regulation_json_parsing()
    
    # Test improved extraction
    test_json_extraction_improvement()
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    
    # Determine main issues
    failed_tests = [r for r in results if not r['passed']]
    if failed_tests:
        print(f"\nISSUES FOUND: {len(failed_tests)} test(s) failed")
        for test in failed_tests:
            if test['expected'] and not test['actual']:
                print(f"- {test['name']}: Should parse but doesn't (likely needs better JSON extraction)")
            elif not test['expected'] and test['actual']:
                print(f"- {test['name']}: Shouldn't parse but does")
    else:
        print("\nNo issues found with current implementation")
    
    print("=" * 70)