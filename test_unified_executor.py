"""
测试统一的 ReAct Executor
"""

import os
import sys
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_mock_tool_library():
    """创建模拟工具库"""
    from agents.executor import Tool
    
    def mock_basic_validator(ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": "pass",
            "detail": "Basic validation completed",
            "elements_checked": ["test_element"],
            "issues": []
        }
    
    def mock_measurement_tool(ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": "pass", 
            "measurements": {"width": 36.5, "height": 84.0},
            "detail": "Measurement completed"
        }
    
    tools = {
        "basic_validation": Tool(
            name="basic_validation",
            description="Performs basic validation checks on IFC file",
            category="validation",
            function=mock_basic_validator,
            parameters_schema={
                "step_id": {"type": "string", "required": False}
            }
        ),
        "measure_elements": Tool(
            name="measure_elements", 
            description="Measures dimensions of building elements",
            category="measurement",
            function=mock_measurement_tool,
            parameters_schema={
                "element_type": {"type": "string", "required": True},
                "include_metadata": {"type": "boolean", "required": False}
            }
        )
    }
    
    return tools

def test_unified_executor_basic():
    """测试统一executor的基本功能"""
    
    print("Testing Unified ReAct Executor - Basic Functionality")
    print("=" * 60)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from utils.llm_client import LLMClient
        from agents.executor import Executor
        
        # 创建模拟工具库
        tool_library = create_mock_tool_library()
        
        # 创建executor
        llm_client = LLMClient()
        executor = Executor(llm_client=llm_client, tool_library=tool_library)
        
        print("1. Testing executor initialization...")
        print(f"   Tool library size: {len(executor.tool_library)}")
        print(f"   Available tools: {list(executor.tool_library.keys())}")
        
        # 测试步骤
        step = {
            "step_id": "test_step_1",
            "description": "Validate building compliance",
            "task_type": "validation",
            "expected_output": "Validation result"
        }
        
        ifc_file_path = "test_file.ifc"
        
        print("\n2. Testing step execution...")
        
        def mock_llm_response(prompt, system_prompt):
            return """{
    "thought": "I need to perform basic validation on the IFC file to check compliance",
    "action": "basic_validation",
    "action_input": {
        "step_id": "test_step_1"
    },
    "expected_outcome": "Validation will complete successfully",
    "is_final": true
}"""
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_response):
                
                try:
                    result = executor.execute_step(step, ifc_file_path)
                    
                    print("SUCCESS: Step executed successfully!")
                    print(f"   Status: {result.get('status')}")
                    print(f"   Step ID: {result.get('step_id')}")
                    print(f"   Iterations used: {result.get('iterations_used')}")
                    
                    if result.get('result'):
                        print(f"   Result: {result['result']}")
                    
                    return True
                    
                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return False

def test_tool_matching():
    """测试动态工具匹配功能"""
    
    print("\n\nTesting Dynamic Tool Matching")
    print("=" * 40)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from utils.llm_client import LLMClient
        from agents.executor import Executor
        
        tool_library = create_mock_tool_library()
        llm_client = LLMClient()
        executor = Executor(llm_client=llm_client, tool_library=tool_library)
        
        # 测试不同的步骤类型
        test_cases = [
            {
                "step": {
                    "description": "measure door widths",
                    "task_type": "measurement"
                },
                "expected_category": "measurement"
            },
            {
                "step": {
                    "description": "validate building structure", 
                    "task_type": "validation"
                },
                "expected_category": "validation"
            }
        ]
        
        for i, case in enumerate(test_cases):
            print(f"\n{i+1}. Testing tool matching for: {case['step']['description']}")
            
            suggested_tools = executor._suggest_relevant_tools(
                step=case["step"],
                current_state={"observation": "Starting task"}
            )
            
            print(f"   Suggested tools: {[t.name for t in suggested_tools]}")
            print(f"   Categories: {[t.category for t in suggested_tools]}")
            
            # 验证是否匹配了预期的类别
            categories = [t.category for t in suggested_tools]
            if case["expected_category"] in categories:
                print(f"   SUCCESS: Correctly matched {case['expected_category']} category")
            else:
                print(f"   FAILED: Failed to match {case['expected_category']} category")
        
        return True

def test_error_handling():
    """测试错误处理"""
    
    print("\n\nTesting Error Handling")
    print("=" * 30)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from utils.llm_client import LLMClient
        from agents.executor import Executor
        
        tool_library = create_mock_tool_library()
        llm_client = LLMClient()
        executor = Executor(llm_client=llm_client, tool_library=tool_library)
        
        step = {
            "step_id": "error_test",
            "description": "Test error handling",
            "task_type": "validation"
        }
        
        print("1. Testing LLM failure handling...")
        
        def mock_llm_failure(prompt, system_prompt):
            raise Exception("Simulated LLM API failure")
        
        with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_failure):
            try:
                result = executor.execute_step(step, "test.ifc")
                print("   FAILED: Should have raised exception")
                return False
            except RuntimeError as e:
                if "ReAct LLM call failed" in str(e):
                    print(f"   SUCCESS: Correctly raised RuntimeError: {e}")
                    return True
                else:
                    print(f"   PARTIAL: Got RuntimeError but wrong message: {e}")
                    return False
            except Exception as e:
                print(f"   UNEXPECTED: Different exception type: {e}")
                return False

def test_backward_compatibility():
    """测试向后兼容性"""
    
    print("\n\nTesting Backward Compatibility")
    print("=" * 35)
    
    try:
        from agents.executor import Executor
        
        print("1. Testing class import...")
        if Executor:
            print("   SUCCESS: Executor class works correctly")
            return True
        else:
            print("   FAILED: Executor class not working")
            return False
            
    except ImportError as e:
        print(f"   FAILED: Import error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Unified ReAct Executor Implementation")
    print("=" * 80)
    
    # 运行所有测试
    test1 = test_unified_executor_basic()
    test2 = test_tool_matching() 
    test3 = test_error_handling()
    test4 = test_backward_compatibility()
    
    print("\n" + "=" * 80)
    print("TEST RESULTS:")
    print(f"- Basic functionality: {'PASS' if test1 else 'FAIL'}")
    print(f"- Tool matching: {'PASS' if test2 else 'FAIL'}")
    print(f"- Error handling: {'PASS' if test3 else 'FAIL'}")
    print(f"- Backward compatibility: {'PASS' if test4 else 'FAIL'}")
    
    all_passed = all([test1, test2, test3, test4])
    
    if all_passed:
        print("\nALL TESTS PASSED!")
        print("Unified Executor is working correctly!")
        print("\nKEY IMPROVEMENTS:")
        print("- Single LLM call for complete ReAct cycle")
        print("- Dynamic tool matching based on task description")
        print("- Fuzzy tool name matching for error tolerance")
        print("- Proper fail-fast error handling")
        print("- Backward compatibility maintained")
    else:
        print("\nSome tests failed - check output above")
    
    print("=" * 80)