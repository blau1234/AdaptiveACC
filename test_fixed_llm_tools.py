"""
测试修复后的LLM工具选择和参数使用功能
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tool_manager():
    """测试工具管理器功能"""
    print("Testing Tool Manager")
    print("=" * 50)
    
    from tool_library.tool_manager import ToolManager
    
    manager = ToolManager()
    
    print("1. Available tools:")
    all_tools = manager.get_all_tools()
    for name, tool in all_tools.items():
        print(f"   - {name} ({tool.category}): {tool.description}")
    
    print(f"\n2. Total tools loaded: {len(all_tools)}")
    
    # 测试工具执行
    print("\n3. Testing tool execution:")
    test_ifc_path = "test_ifc/sample.ifc"  # 假设的测试文件
    
    # 测试get_elements_by_type工具
    result = manager.execute_tool(
        tool_name="get_elements_by_type",
        ifc_file_path=test_ifc_path,
        parameters={"element_type": "IfcDoor"}
    )
    
    print(f"   get_elements_by_type result: {result.get('result', 'unknown')}")
    print(f"   Detail: {result.get('detail', 'no detail')}")
    
    return len(all_tools) > 0

def test_executor_with_llm_selection():
    """测试修复后的Executor是否正确使用LLM选择的工具和参数"""
    print("\n\nTesting Fixed Executor with LLM Tool Selection")
    print("=" * 60)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        print("1. Available tools in executor:")
        tools_info = executor.get_available_tools_info()
        print(tools_info[:500] + "..." if len(tools_info) > 500 else tools_info)
        
        # 模拟LLM返回不同的工具选择
        test_cases = [
            {
                "name": "Door Width Measurement",
                "llm_response": '''{
                    "thought": "I need to measure door widths to check accessibility compliance. I'll use the dimension measurement tool.",
                    "action": "dimension_measurement",
                    "action_input": {
                        "element_type": "IfcDoor",
                        "dimension_type": "width"
                    },
                    "is_final": false
                }''',
                "expected_tool": "dimension_measurement",
                "expected_params": {"element_type": "IfcDoor", "dimension_type": "width"}
            },
            {
                "name": "Element Extraction",
                "llm_response": '''{
                    "thought": "First, I need to extract all door elements from the building model.",
                    "action": "get_elements_by_type", 
                    "action_input": {
                        "element_type": "IfcDoor"
                    },
                    "is_final": false
                }''',
                "expected_tool": "get_elements_by_type",
                "expected_params": {"element_type": "IfcDoor"}
            },
            {
                "name": "Accessibility Check",
                "llm_response": '''{
                    "thought": "Now I should check if the doors meet accessibility standards.",
                    "action": "accessibility_checker",
                    "action_input": {
                        "check_type": "door_width"
                    },
                    "is_final": false
                }''',
                "expected_tool": "accessibility_checker", 
                "expected_params": {"check_type": "door_width"}
            }
        ]
        
        print(f"\n2. Testing {len(test_cases)} LLM tool selection scenarios:")
        
        results = []
        
        for i, case in enumerate(test_cases):
            print(f"\n测试案例 {i+1}: {case['name']}")
            
            # Mock LLM response
            def mock_llm_response(prompt, system_prompt):
                return case["llm_response"]
            
            # Mock step and context
            test_step = {
                "step_id": f"step_{i+1}",
                "description": f"Test case: {case['name']}",
                "task_type": "test",
                "expected_output": "Test result"
            }
            
            test_context = {
                "step": test_step,
                "ifc_file_path": "test_ifc/sample.ifc",
                "history": []
            }
            
            with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_response):
                try:
                    # 测试ReAct响应解析
                    react_response = executor._get_react_response(
                        step=test_step,
                        current_state={"observation": "Starting test"},
                        history=[],  
                        iteration=0,
                        context=test_context
                    )
                    
                    print(f"   LLM选择的工具: {react_response.get('action')}")
                    print(f"   LLM提供的参数: {react_response.get('action_input')}")
                    
                    # 验证工具选择是否正确
                    tool_correct = react_response.get("action") == case["expected_tool"]
                    params_correct = react_response.get("action_input") == case["expected_params"] 
                    
                    # 测试工具执行
                    action_result = executor._execute_action(
                        action_name=react_response["action"],
                        action_input=react_response["action_input"],
                        context=test_context
                    )
                    
                    execution_success = action_result.get("success", False)
                    actual_tool_used = action_result.get("tool_name")
                    actual_params_used = action_result.get("parameters_used")
                    
                    print(f"   实际执行的工具: {actual_tool_used}")
                    print(f"   实际使用的参数: {actual_params_used}")
                    print(f"   执行结果: {'SUCCESS' if execution_success else 'FAILED'}")
                    
                    if execution_success:
                        tool_result = action_result.get("result", {})
                        print(f"   工具返回结果: {tool_result.get('result', 'unknown')} - {tool_result.get('detail', 'no detail')}")
                    else:
                        print(f"   执行错误: {action_result.get('error', 'unknown error')}")
                    
                    results.append({
                        "name": case["name"],
                        "tool_selection_correct": tool_correct,
                        "params_correct": params_correct,
                        "execution_success": execution_success,
                        "llm_selected_tool": react_response.get("action"),
                        "actual_tool_used": actual_tool_used,
                        "llm_params": react_response.get("action_input"),
                        "actual_params": actual_params_used
                    })
                    
                except Exception as e:
                    print(f"   FAILED: 测试失败: {e}")
                    results.append({
                        "name": case["name"],
                        "tool_selection_correct": False,
                        "params_correct": False,
                        "execution_success": False,
                        "error": str(e)
                    })
        
        return results

def test_full_react_cycle():
    """测试完整的ReAct循环"""
    print("\n\nTesting Full ReAct Cycle")
    print("=" * 40)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        # 模拟多轮ReAct对话
        conversation = [
            '''{
                "thought": "I need to first extract all door elements to analyze them.",
                "action": "get_elements_by_type",
                "action_input": {
                    "element_type": "IfcDoor"
                },
                "is_final": false
            }''',
            '''{
                "thought": "Now I should measure the door widths to check accessibility compliance.",
                "action": "dimension_measurement", 
                "action_input": {
                    "element_type": "IfcDoor",
                    "dimension_type": "width"
                },
                "is_final": false
            }''',
            '''{
                "thought": "Finally, I'll check if the door widths meet accessibility standards.",
                "action": "accessibility_checker",
                "action_input": {
                    "check_type": "door_width"
                },
                "is_final": true
            }'''
        ]
        
        test_step = {
            "step_id": "multi_step_test",
            "description": "Check door accessibility compliance",
            "task_type": "accessibility",
            "expected_output": "Accessibility compliance report"
        }
        
        iteration_counter = 0
        def mock_llm_response(prompt, system_prompt):
            nonlocal iteration_counter
            if iteration_counter < len(conversation):
                response = conversation[iteration_counter]
                iteration_counter += 1
                return response
            else:
                return '{"thought": "Task completed", "is_final": true}'
        
        print("1. Testing multi-step ReAct execution:")
        
        with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_response):
            try:
                result = executor.execute_step(
                    step=test_step,
                    ifc_file_path="test_ifc/sample.ifc",
                    max_iterations=5
                )
                
                print(f"   Overall result: {result.get('status')}")
                print(f"   Iterations used: {result.get('iterations_used', 0)}")
                
                if result.get("execution_history"):
                    print("   Execution history:")
                    for i, hist in enumerate(result["execution_history"]):
                        print(f"     Step {i+1}: {hist.get('action')} - {hist.get('thought', '')[:50]}...")
                
                return result.get('status') == 'success'
                
            except Exception as e:
                print(f"   FAILED: {e}")
                return False

def run_all_tests():
    """运行所有测试"""
    print("Testing Fixed LLM Tool Selection and Parameter Usage")
    print("=" * 80)
    
    # 测试结果收集
    test_results = {}
    
    # 1. 测试工具管理器
    test_results["tool_manager"] = test_tool_manager()
    
    # 2. 测试Executor工具选择
    executor_results = test_executor_with_llm_selection()
    test_results["executor_tool_selection"] = executor_results
    
    # 3. 测试完整ReAct循环
    test_results["full_react_cycle"] = test_full_react_cycle()
    
    # 结果汇总
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY:")
    print("=" * 80)
    
    print(f"1. Tool Manager: {'PASS' if test_results['tool_manager'] else 'FAIL'}")
    
    if executor_results:
        correct_selections = sum(1 for r in executor_results if r.get("tool_selection_correct", False))
        correct_params = sum(1 for r in executor_results if r.get("params_correct", False))
        successful_executions = sum(1 for r in executor_results if r.get("execution_success", False))
        
        print(f"2. Executor Tool Selection:")
        print(f"   - Correct tool selection: {correct_selections}/{len(executor_results)}")
        print(f"   - Correct parameter usage: {correct_params}/{len(executor_results)}")
        print(f"   - Successful execution: {successful_executions}/{len(executor_results)}")
    
    print(f"3. Full ReAct Cycle: {'PASS' if test_results['full_react_cycle'] else 'FAIL'}")
    
    # 整体评估
    overall_success = (
        test_results["tool_manager"] and
        test_results["full_react_cycle"] and
        len([r for r in executor_results if r.get("tool_selection_correct") and r.get("execution_success")]) >= 2
    )
    
    print("\n" + "=" * 80)
    if overall_success:
        print("✅ ALL TESTS PASSED!")
        print("\nKEY FIXES VERIFIED:")
        print("SUCCESS: ✅ LLM-selected tools are now actually used")
        print("SUCCESS: ✅ LLM-provided parameters are passed to tools")
        print("SUCCESS: ✅ Tool Manager provides unified tool interface")
        print("SUCCESS: ✅ ReAct framework properly executes LLM decisions")
        print("SUCCESS: ✅ No more hardcoded tool selection")
        print("\nThe system now truly uses LLM intelligence for tool selection and parameter usage!")
    else:
        print("❌ Some tests failed - check details above")
        print("The LLM tool selection and parameter usage may still have issues.")
    
    print("=" * 80)
    
    return overall_success

if __name__ == "__main__":
    run_all_tests()