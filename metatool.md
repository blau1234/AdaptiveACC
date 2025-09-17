# Meta-Tool-Enabled Adaptive Multi-Agent System for BIM-Based Automated Code Compliance Checking

# Meta Tool
负责生成、注册、管理、更新其他 tool 的工具
    • 普通工具（Tool）：解决具体任务，比如 check_wall_thickness、parse_ifc_file。
    • 元工具（Meta Tool）：不直接解决业务问题，而是生成/修改/组织其他工具

## Task Layer - 处理任务（规划、执行、检查）
    Roles, Workflow
    - Coordinator
        - Planner
            Generate initial plan
            Plan modfication
            任务分解的粒度：每步使用一个工具
        - Executor
            Execute each step: ReAct loop
            Executor通过ReAct循环动态选择调用哪个meta tool
        - Checker
    
## Meta Tool Layer - Tool 的“生命周期管理器”
两条路径：
    - 现有工具：tool selection -> tool execution 
    - 新工具：Tool Creation → 新工具 → tool registration -> tool execution -> tool storage

    在 meta_tools 文件夹里
    - Tool Creation
        • Spec Generator: current step -> ToolRequirement
        • Code generator: ToolRequirement -> Tool code
        • Static checker
    - Tool Registration
        • Register generated tool to ToolRegistry
    - Tool storage - for future use
        • Persistant Storage: code + metadata
        • Compute embedding: metadata
        • add to tools vectordb
    - Tool Selection
        • semantic tool selection -> top K tools
        • Schema Retrieval from ToolRegistry
        •  构建包含详细参数信息的 LLM prompt
        • generative tool selection 通过调用大模型生成式地选择最合适的一个tool
    - Tool Execution
        • Parameter Preparation
        • Tool Execution (ToolRegistry)
    
## Domain Tool Layer - 具体的合规检查与辅助函数
    在 domain tools 文件夹里