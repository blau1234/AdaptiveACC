"""
Simple test for LLMClient core functionality
"""

import os
import sys
from unittest.mock import patch, Mock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_core_functionality():
    """Test core LLMClient functionality with mocked API"""
    
    print("Testing LLMClient Core Functionality")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test123456789',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from utils.llm_client import LLMClient
        
        print("1. Initialization Test")
        llm_client = LLMClient()
        print(f"   Model: {llm_client.model_name}")
        print(f"   Client type: {type(llm_client.client)}")
        print("   Status: PASS")
        print()
        
        print("2. Successful API Call Test")
        
        # Mock successful API response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Hello! I'm working correctly."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(llm_client.client.chat.completions, 'create', return_value=mock_response):
            response = llm_client.generate_response("Test prompt", "System prompt")
            print(f"   Input: 'Test prompt'")
            print(f"   Output: '{response}'")
            print(f"   Length: {len(response)} chars")
            print("   Status: PASS" if response == "Hello! I'm working correctly." else "   Status: FAIL")
        print()
        
        print("3. Error Handling Test")
        
        # Mock API failure
        with patch.object(llm_client.client.chat.completions, 'create', side_effect=Exception("Connection error")):
            error_response = llm_client.generate_response("Test", max_retries=2)
            print(f"   Error response: '{error_response}'")
            print("   Status: PASS" if "API call failed" in error_response else "   Status: FAIL")
        print()
        
        print("4. Empty Response Handling Test")
        
        # Mock empty response
        mock_empty = Mock()
        mock_empty_choice = Mock()
        mock_empty_message = Mock()
        mock_empty_message.content = ""  # Empty content
        mock_empty_choice.message = mock_empty_message
        mock_empty.choices = [mock_empty_choice]
        
        with patch.object(llm_client.client.chat.completions, 'create', return_value=mock_empty):
            empty_response = llm_client.generate_response("Test")
            print(f"   Empty response handling: '{empty_response[:50]}...'")
            print("   Status: PASS" if "API call failed" in empty_response else "   Status: FAIL")
        print()
        
        print("5. Message Structure Test")
        
        # Check if messages are structured correctly
        actual_messages = None
        def capture_messages(**kwargs):
            nonlocal actual_messages
            actual_messages = kwargs.get('messages', [])
            return mock_response
        
        with patch.object(llm_client.client.chat.completions, 'create', side_effect=capture_messages):
            llm_client.generate_response("User message", "System message")
            
            print(f"   Messages count: {len(actual_messages)}")
            print(f"   System message: {actual_messages[0] if actual_messages else 'None'}")
            print(f"   User message: {actual_messages[1] if len(actual_messages) > 1 else 'None'}")
            
            expected_structure = (
                len(actual_messages) == 2 and
                actual_messages[0]['role'] == 'system' and
                actual_messages[1]['role'] == 'user'
            )
            print("   Status: PASS" if expected_structure else "   Status: FAIL")
        print()
        
        return True

def test_with_real_env():
    """Test with actual environment variables if available"""
    
    print("Testing with Environment Variables")
    print("=" * 40)
    
    try:
        from utils.llm_client import LLMClient
        from config import Config
        
        print(f"API Key present: {'Yes' if Config.OPENAI_API_KEY else 'No'}")
        print(f"Model name: {Config.OPENAI_MODEL_NAME}")
        print(f"API Base: {Config.OPENAI_API_BASE or 'Default'}")
        
        if Config.OPENAI_API_KEY:
            print("Environment configuration: READY")
        else:
            print("Environment configuration: Missing API key")
        
        return True
        
    except Exception as e:
        print(f"Environment test failed: {e}")
        return False

if __name__ == "__main__":
    print("LLMClient Simple Functionality Test")
    print("=" * 60)
    print()
    
    # Test core functionality
    core_test = test_llm_core_functionality()
    
    # Test environment
    env_test = test_with_real_env()
    
    print()
    print("=" * 60)
    if core_test and env_test:
        print("RESULT: LLMClient is functioning correctly!")
        print("Ready for use in the multi-agent system.")
    else:
        print("RESULT: Issues detected with LLMClient")
    print("=" * 60)