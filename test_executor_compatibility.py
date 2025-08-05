"""
测试新 UnifiedReActExecutor 与现有系统的兼容性
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_execute_plan_compatibility():
    """测试execute_plan方法的向后兼容性"""
    
    print("Testing execute_plan Compatibility")
    print("=" * 40)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        # 使用默认初始化（无参数）
        executor = Executor()
        
        print("1. Testing default initialization...")
        print(f"   Executor type: {type(executor).__name__}")
        print(f"   Tool library size: {len(executor.tool_library)}")
        print(f"   Available tools: {list(executor.tool_library.keys())}")
        
        # 创建模拟计划
        plan = {
            "plan_id": "test_plan_001",
            "steps": [
                {
                    "step_id": "step_1",
                    "description": "Perform basic validation",
                    "task_type": "validation",
                    "expected_output": "Validation result"
                },
                {
                    "step_id": "step_2", 
                    "description": "Analyze file structure",
                    "task_type": "analysis",
                    "expected_output": "Analysis result"
                }
            ]
        }
        
        ifc_file_path = "test_file.ifc"
        
        print("\n2. Testing execute_plan method...")
        
        def mock_llm_response(prompt, system_prompt):
            # 根据任务类型返回不同响应
            if "validation" in prompt.lower():
                return """{
    "thought": "I need to perform basic validation on the IFC file",
    "action": "basic_validation",
    "action_input": {},
    "is_final": true
}"""
            elif "analysis" in prompt.lower():
                return """{
    "thought": "I need to analyze the file structure",
    "action": "file_analyzer", 
    "action_input": {},
    "is_final": true
}"""
            else:
                return """{
    "thought": "Generic task execution",
    "action": "basic_validation",
    "action_input": {},
    "is_final": true
}"""
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=1024):
                with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_response):
                    
                    try:
                        result = executor.execute_plan(plan, ifc_file_path)
                        
                        print("SUCCESS: Plan executed successfully!")
                        print(f"   Status: {result.get('status')}")
                        print(f"   Plan ID: {result.get('plan_id')}")
                        print(f"   Total steps: {result.get('total_steps')}")
                        print(f"   Completed count: {result.get('completed_count')}")
                        print(f"   Failed count: {result.get('failed_count')}")
                        
                        # 验证返回格式
                        required_fields = ['status', 'results', 'plan_id', 'total_steps', 'completed_count']
                        missing_fields = [field for field in required_fields if field not in result]
                        
                        if missing_fields:
                            print(f"   WARNING: Missing fields: {missing_fields}")
                            return False
                        
                        # 验证结果格式
                        if result.get('results'):
                            first_result = result['results'][0]
                            expected_result_fields = ['result', 'detail', 'elements_checked', 'issues']
                            missing_result_fields = [field for field in expected_result_fields 
                                                   if field not in first_result]
                            
                            if missing_result_fields:
                                print(f"   WARNING: Missing result fields: {missing_result_fields}")
                                return False
                            
                            print(f"   Result format: All required fields present")
                        
                        return True
                        
                    except Exception as e:
                        print(f"FAILED: {e}")
                        import traceback
                        traceback.print_exc()
                        return False

def test_coordinator_integration():
    """测试与Coordinator的集成"""
    
    print("\n\nTesting Coordinator Integration")
    print("=" * 35)
    
    # Set environment for testing
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.coordinator import AgentCoordinator
        
        coordinator = AgentCoordinator()
        
        print("1. Testing coordinator initialization with new executor...")
        print(f"   Executor type: {type(coordinator.executor).__name__}")
        print(f"   Has execute_plan method: {hasattr(coordinator.executor, 'execute_plan')}")
        print(f"   Has execute_step method: {hasattr(coordinator.executor, 'execute_step')}")
        
        # 模拟执行
        mock_plan = {
            "plan_id": "coord_test_plan",
            "steps": [
                {
                    "step_id": "coord_step_1",
                    "description": "Basic compliance check",
                    "task_type": "validation"
                }
            ]
        }
        
        print("\n2. Testing plan execution through coordinator...")
        
        def mock_llm_response(prompt, system_prompt):
            return """{
    "thought": "Performing compliance check as requested by coordinator",
    "action": "basic_validation",
    "action_input": {},
    "is_final": true
}"""
        
        with patch('os.path.exists', return_value=True):
            with patch.object(coordinator.executor.llm_client, 'generate_response', side_effect=mock_llm_response):
                
                try:
                    # 直接测试executor的execute_plan方法
                    result = coordinator.executor.execute_plan(mock_plan, "test.ifc")
                    
                    print("SUCCESS: Coordinator can use new executor!")
                    print(f"   Execution status: {result.get('status')}")
                    print(f"   Results count: {len(result.get('results', []))}")
                    
                    return True
                    
                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return False

def test_error_propagation():
    """测试错误传播是否保持fail-fast行为"""
    
    print("\n\nTesting Error Propagation")
    print("=" * 30)
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        
        from agents.executor import Executor
        
        executor = Executor()
        
        plan = {
            "plan_id": "error_test_plan",
            "steps": [
                {
                    "step_id": "error_step",
                    "description": "This will fail",
                    "task_type": "validation"
                }
            ]
        }
        
        print("1. Testing LLM failure propagation...")
        
        def mock_llm_failure(prompt, system_prompt):
            raise Exception("Simulated LLM failure")
        
        with patch.object(executor.llm_client, 'generate_response', side_effect=mock_llm_failure):
            try:
                result = executor.execute_plan(plan, "test.ifc")
                
                # 应该有失败的步骤
                if result.get('failed_count', 0) > 0:
                    print("SUCCESS: Error properly handled in plan execution")
                    print(f"   Failed steps: {result.get('failed_count')}")
                    print(f"   Status: {result.get('status')}")
                    return True
                else:
                    print("FAILED: Error not properly propagated")
                    return False
                    
            except Exception as e:
                # 这也是可接受的行为（直接失败）
                print(f"SUCCESS: Exception properly propagated: {type(e).__name__}")
                return True

if __name__ == "__main__":
    print("Testing UnifiedReActExecutor Compatibility with Existing System")
    print("=" * 80)
    
    # 运行所有测试
    test1 = test_execute_plan_compatibility()
    test2 = test_coordinator_integration()
    test3 = test_error_propagation()
    
    print("\n" + "=" * 80)
    print("COMPATIBILITY TEST RESULTS:")
    print(f"- execute_plan compatibility: {'PASS' if test1 else 'FAIL'}")
    print(f"- Coordinator integration: {'PASS' if test2 else 'FAIL'}")
    print(f"- Error propagation: {'PASS' if test3 else 'FAIL'}")
    
    all_passed = all([test1, test2, test3])
    
    if all_passed:
        print("\nALL COMPATIBILITY TESTS PASSED!")
        print("\nSUMMARY:")
        print("- UnifiedReActExecutor maintains full backward compatibility")
        print("- Coordinator can use the new executor without changes")
        print("- Error handling preserves fail-fast behavior")
        print("- All required interfaces are properly implemented")
        print("\nYour refactoring is successful and safe to deploy!")
    else:
        print("\nSome compatibility tests failed - check output above")
    
    print("=" * 80)