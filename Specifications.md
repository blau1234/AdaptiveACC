Coordinator 负责管理多智能体间的流程控制与通信，协调任务执行、计划调整与结果整合。

规划阶段（由 Planner 完成）
    Coordinator → Planner：发送法规文本
    Planner 调用 LLM 分析法规，生成结构化的任务计划（structured plan）
    Planner → Coordinator：返回结构化计划

执行阶段（由 Executor 负责）
    Coordinator → Executor：发送结构化计划和 IFC 文件
    Executor 使用 ReAct 框架，逐步执行计划中的每一项任务：
        调用相应工具获取所需信息
        每完成一步：Executor → Coordinator：反馈执行结果
        若某一步出现异常、数据缺失或任务失败：
            Coordinator → Planner：发送反馈，请求重新规划
            Planner 基于反馈信息生成新的计划
            Planner → Coordinator：返回更新后的计划
            Coordinator → Executor：继续执行新计划

检查阶段（由 Checker 负责）
    Coordinator → Checker：统一发送以下内容：
        原始法规文本
        执行过程中所使用的计划（可为更新后的版本）
        所有执行结果（结构化记录）
    Checker 调用 LLM 判断执行结果是否符合规定
    Checker → Coordinator：返回检查结论与建议
