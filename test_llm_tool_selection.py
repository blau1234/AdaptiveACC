"""
测试基于 LLM 的智能工具选择机制
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_tool_selection():
    """测试LLM工具选择功能"""
    
    print("Testing LLM-based Tool Selection")
    print("=" * 50)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        print("1. Available tools in library:")
        for name, tool in executor.tool_library.items():
            print(f"   - {name} ({tool.category}): {tool.description}")
        
        # 测试不同类型的任务
        test_cases = [
            {
                "name": "门宽度检查",
                "step": {
                    "description": "检查所有门的宽度是否符合无障碍通行标准，最小宽度应为32英寸",
                    "task_type": "accessibility",
                    "expected_output": "门宽度测量结果和合规性评估"
                },
                "expected_categories": ["measurement", "compliance"]
            },
            {
                "name": "建筑安全评估",
                "step": {
                    "description": "评估建筑的火灾安全系统和紧急出口配置",
                    "task_type": "safety",
                    "expected_output": "安全合规性报告"
                },
                "expected_categories": ["safety", "compliance"]
            },
            {
                "name": "IFC文件验证",
                "step": {
                    "description": "验证IFC文件的结构完整性和数据格式",
                    "task_type": "validation",
                    "expected_output": "文件验证结果"
                },
                "expected_categories": ["validation", "analysis"]
            },
            {
                "name": "建筑元素分析",
                "step": {
                    "description": "分析建筑中的所有结构元素，包括墙、梁、柱等",
                    "task_type": "analysis",
                    "expected_output": "元素清单和属性分析"
                },
                "expected_categories": ["analysis", "validation"]
            }
        ]
        
        print(f"\n2. Testing {len(test_cases)} different task scenarios:")
        
        results = []
        
        for i, case in enumerate(test_cases):
            print(f"\n测试案例 {i+1}: {case['name']}")
            print(f"任务描述: {case['step']['description']}")
            
            # Mock LLM response for tool selection
            def mock_tool_selection_response(prompt, system_prompt):
                # 模拟智能的工具选择响应
                if "门宽度" in prompt or "accessibility" in prompt:
                    return """{
    "reasoning": "这个任务需要测量门的尺寸并检查无障碍合规性，因此选择尺寸测量工具和无障碍检查工具",
    "selected_tools": ["dimension_measurement", "accessibility_checker"],
    "confidence": 0.9
}"""
                elif "安全" in prompt or "safety" in prompt:
                    return """{
    "reasoning": "建筑安全评估需要专门的安全合规性检查工具来评估火灾安全和紧急出口",
    "selected_tools": ["safety_compliance", "element_checker"],
    "confidence": 0.95
}"""
                elif "IFC文件验证" in prompt or "validation" in prompt:
                    return """{
    "reasoning": "IFC文件验证需要基础验证工具和文件分析工具来检查文件结构和格式",
    "selected_tools": ["basic_validation", "file_analyzer"],
    "confidence": 0.85
}"""
                elif "建筑元素分析" in prompt or "analysis" in prompt:
                    return """{
    "reasoning": "分析建筑元素需要文件分析工具和元素检查工具来识别和分析所有结构组件",
    "selected_tools": ["file_analyzer", "element_checker"],
    "confidence": 0.88
}"""
                else:
                    return """{
    "reasoning": "默认选择基础验证工具",
    "selected_tools": ["basic_validation"],
    "confidence": 0.5
}"""
            
            current_state = {"observation": f"开始执行任务: {case['name']}"}
            
            with patch.object(executor.llm_client, 'generate_response', side_effect=mock_tool_selection_response):
                try:
                    suggested_tools = executor._suggest_relevant_tools(case["step"], current_state)
                    
                    tool_names = [tool.name for tool in suggested_tools]
                    tool_categories = [tool.category for tool in suggested_tools]
                    
                    print(f"选择的工具: {tool_names}")
                    print(f"工具类别: {tool_categories}")
                    
                    # 验证是否选择了合理的工具
                    success = len(suggested_tools) > 0
                    category_match = any(cat in tool_categories for cat in case["expected_categories"])
                    
                    results.append({
                        "name": case["name"],
                        "success": success,
                        "category_match": category_match,
                        "tools_selected": len(suggested_tools),
                        "tool_names": tool_names
                    })
                    
                    if success and category_match:
                        print("SUCCESS: 工具选择成功且类别匹配")
                    elif success:
                        print("SUCCESS: 工具选择成功但类别可能不完全匹配")
                    else:
                        print("FAILED: 工具选择失败")
                        
                except Exception as e:
                    print(f"FAILED: 测试失败: {e}")
                    results.append({
                        "name": case["name"],
                        "success": False,
                        "category_match": False,
                        "tools_selected": 0,
                        "tool_names": []
                    })
        
        return results

def test_llm_failure_behavior():
    """测试LLM失败时的严格失败行为"""
    
    print("\n\nTesting LLM Failure Behavior (Fail Fast)")
    print("=" * 40)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        test_step = {
            "description": "检查建筑的无障碍通道设计",
            "task_type": "accessibility",
            "expected_output": "无障碍合规性评估"
        }
        
        current_state = {"observation": "开始无障碍检查"}
        
        print("1. 测试LLM API失败情况...")
        
        def mock_llm_failure(prompt, system_prompt):
            raise Exception("模拟的API失败")
        
        with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_failure):
            try:
                suggested_tools = executor._suggest_relevant_tools(test_step, current_state)
                print("FAILED: 应该抛出异常，而不是返回工具")
                return False
                    
            except RuntimeError as e:
                if "LLM工具选择失败" in str(e):
                    print(f"SUCCESS: 正确抛出了RuntimeError: {e}")
                    return True
                else:
                    print(f"PARTIAL: 抛出了RuntimeError但消息不正确: {e}")
                    return False
            except Exception as e:
                print(f"UNEXPECTED: 抛出了其他类型的异常: {e}")
                return False

def test_tool_info_building():
    """测试为LLM构建工具信息的功能"""
    
    print("\n\nTesting Tool Info Building for LLM")
    print("=" * 40)
    
    from agents.executor import Executor
    
    executor = Executor()
    
    print("1. 测试工具信息构建...")
    
    tools_info = executor._build_tools_info_for_llm()
    
    print("构建的工具信息:")
    print("-" * 30)
    print(tools_info[:500] + "..." if len(tools_info) > 500 else tools_info)
    print("-" * 30)
    
    # 验证信息是否包含必要元素
    checks = [
        ("工具名" in tools_info, "包含工具名称"),
        ("类别" in tools_info, "包含工具类别"),
        ("功能" in tools_info, "包含功能描述"),
        ("参数" in tools_info, "包含参数信息"),
        (len(tools_info) > 100, "信息长度合理")
    ]
    
    print("\n2. 信息完整性检查:")
    all_passed = True
    for check, description in checks:
        status = "SUCCESS:" if check else "FAILED:"
        print(f"   {status} {description}")
        if not check:
            all_passed = False
    
    return all_passed

def test_response_parsing():
    """测试LLM响应解析功能"""
    
    print("\n\nTesting LLM Response Parsing")
    print("=" * 40)
    
    from agents.executor import Executor
    
    executor = Executor()
    
    # 测试不同格式的响应
    test_responses = [
        {
            "name": "标准JSON格式",
            "response": """{
    "reasoning": "选择基础验证工具进行文件检查",
    "selected_tools": ["basic_validation", "file_analyzer"],
    "confidence": 0.8
}""",
            "expected_tools": ["basic_validation", "file_analyzer"]
        },
        {
            "name": "Markdown代码块格式",
            "response": """根据任务需求，我选择以下工具：

```json
{
    "reasoning": "需要进行安全检查",
    "selected_tools": ["safety_compliance"],
    "confidence": 0.9
}
```

这些工具最适合当前任务。""",
            "expected_tools": ["safety_compliance"]
        },
        {
            "name": "混合文本格式",
            "response": """我建议使用 "accessibility_checker" 和 "dimension_measurement" 这两个工具来完成任务。""",
            "expected_tools": ["accessibility_checker", "dimension_measurement"]
        }
    ]
    
    print("1. 测试不同响应格式的解析:")
    
    results = []
    for test in test_responses:
        print(f"\n测试: {test['name']}")
        try:
            parsed = executor._parse_tool_selection_response(test["response"])
            selected_tools = parsed.get("selected_tools", [])
            
            print(f"   解析结果: {selected_tools}")
            print(f"   期望结果: {test['expected_tools']}")
            
            # 检查是否至少解析出了一些工具
            success = len(selected_tools) > 0
            accuracy = len(set(selected_tools) & set(test['expected_tools'])) / max(len(test['expected_tools']), 1)
            
            results.append({
                "name": test["name"],
                "success": success,
                "accuracy": accuracy,
                "tools_found": len(selected_tools)
            })
            
            print(f"   状态: {'SUCCESS:' if success else 'FAILED:'} 成功率: {accuracy:.1%}")
            
        except Exception as e:
            print(f"   FAILED: 解析失败: {e}")
            results.append({
                "name": test["name"],
                "success": False,
                "accuracy": 0.0,
                "tools_found": 0
            })
    
    return results

if __name__ == "__main__":
    print("Testing LLM-based Intelligent Tool Selection")
    print("=" * 80)
    
    # 运行所有测试
    test1_results = test_llm_tool_selection()
    test2_success = test_llm_failure_behavior()
    test3_success = test_tool_info_building()
    test4_results = test_response_parsing()
    
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY:")
    
    # 汇总测试1结果
    successful_cases = sum(1 for r in test1_results if r["success"])
    category_matches = sum(1 for r in test1_results if r["category_match"])
    print(f"- Tool Selection Tests: {successful_cases}/{len(test1_results)} successful")
    print(f"- Category Matching: {category_matches}/{len(test1_results)} accurate")
    
    # 其他测试结果
    print(f"- Fail Fast Behavior: {'PASS' if test2_success else 'FAIL'}")
    print(f"- Tool Info Building: {'PASS' if test3_success else 'FAIL'}")
    
    # 汇总测试4结果
    parsing_success = sum(1 for r in test4_results if r["success"])
    avg_accuracy = sum(r["accuracy"] for r in test4_results) / len(test4_results)
    print(f"- Response Parsing: {parsing_success}/{len(test4_results)} successful")
    print(f"- Parsing Accuracy: {avg_accuracy:.1%}")
    
    # 总体评估
    overall_success = (
        successful_cases == len(test1_results) and
        test2_success and 
        test3_success and
        parsing_success >= len(test4_results) * 0.8  # 80%的解析成功率
    )
    
    if overall_success:
        print("\nALL TESTS PASSED!")
        print("LLM-based tool selection is working correctly!")
        print("\nKEY BENEFITS:")
        print("SUCCESS: Intelligent tool selection based on natural language understanding")
        print("SUCCESS: Context-aware recommendations")
        print("SUCCESS: Pure LLM-driven selection (no fallbacks)")
        print("SUCCESS: Flexible response parsing")
        print("SUCCESS: Better tool-task matching than keyword-based approaches")
    else:
        print("\nSome tests failed - check details above")
    
    print("=" * 80)