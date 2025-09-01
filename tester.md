我想让requirement agent 在被触发后从blackboard获取current step和execution history的内容，输出的内容包括ToolRequiremnt, ifc denpendencies 和 test parameters, test parameters是从execution history 分析得到的前面步骤的结果，ToolRequiremnt 用于生成代码，ifc denpendencies 用于数据可用性检查，test parameters 用于生成测试代码，你觉得这样可行吗

# Requirement Agent
    input：
    - current step
    - Execution history
    
    output：
    - ToolRequirement  -> Code generator
    - IFC dependencies -> _check_data_availability
    - Test parameters -> _create_test_execution_code
    
# Code generator agent
    Input: 
    - ToolRequirement
    - Relevant docs
    
    Output:
    - Tool code

# Dynamic tester
    Input:
    - Tool code
    - IFC dependencies
    - Test parameters
    
    Output:
    - Test result