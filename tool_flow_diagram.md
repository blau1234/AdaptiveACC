# 工具注册检索加载流程图

## 整体架构流程

```mermaid
graph TD
    A[系统启动] --> B[创建 ToolRegistry]
    B --> C[register_builtin_tools]
    C --> D[加载 tools/builtin/ 目录]
    D --> E[PersistentToolStorage.load_all_tools]
    E --> F[扫描所有分类目录]
    
    G[用户请求] --> H[SpecGenerator 分析]
    H --> I[LLM 判断库依赖]
    I --> J[生成 ToolRequirement 含 library 字段]
    J --> K[CodeGeneratorAgent.create_tool]
    K --> L[生成工具代码]
    L --> M[register_from_code]
    M --> N[注册到 ToolRegistry]
    N --> O[PersistentToolStorage.save_tool]
    O --> P[保存到 tools/library 目录]
    
    Q[Executor 需要工具] --> R[registry.get_available_tools]
    R --> S[按命名空间访问工具]
    S --> T[执行工具函数]
    
    classDef startup fill:#e1f5fe
    classDef creation fill:#f3e5f5
    classDef execution fill:#e8f5e8
    classDef storage fill:#fff3e0
    
    class A,B,C,D,E,F startup
    class G,H,I,J,K,L,M,N creation
    class Q,R,S,T execution
    class O,P storage
```

## 详细组件关系图

```mermaid
graph TB
    subgraph CoreComponents["Core Components"]
        TR[ToolRegistry]
        PTS[PersistentToolStorage]
        TReg[domain_tool_registry.py]
    end
    
    subgraph ToolCreation["Tool Creation System"]
        SG[SpecGenerator]
        CGA[CodeGeneratorAgent]
        RAG[RAG Retriever]
    end
    
    subgraph FileSystem["File System"]
        builtin[tools/builtin/]
        ifcopen[tools/ifcopenshell/]
        pandas[tools/pandas/]
        numpy[tools/numpy/]
        other[tools/dynamic/]
    end
    
    subgraph ExecutionSystem["Execution System"]
        EX[Executor Agent]
        CO[Coordinator Agent]
    end
    
    TR --> PTS
    PTS --> builtin
    PTS --> ifcopen
    PTS --> pandas
    PTS --> numpy
    PTS --> other
    
    SG --> CGA
    CGA --> RAG
    CGA --> TR
    CGA --> PTS
    
    EX --> TR
    CO --> EX
    
    TReg --> TR
    TReg --> PTS
```

## 数据流详细图

```mermaid
sequenceDiagram
    participant U as User
    participant C as Coordinator
    participant SG as SpecGenerator
    participant LLM as LLM Client
    participant CGA as CodeGeneratorAgent
    participant TR as ToolRegistry
    participant PTS as PersistentToolStorage
    participant FS as File System
    
    %% 系统启动
    Note over TR,FS: 系统启动阶段
    TR->>PTS: load_all_tools()
    PTS->>FS: 扫描 tools/* 目录
    FS-->>PTS: 返回所有工具文件
    PTS-->>TR: 注册已保存的工具
    
    %% 工具创建
    Note over U,FS: 动态工具创建阶段
    U->>C: 执行计划请求
    C->>SG: analyze_step(step_content)
    SG->>LLM: 分析步骤 + 库选择
    LLM-->>SG: 返回 ToolRequirement (含 library)
    SG-->>C: AnalysisResult
    C->>CGA: create_tool(requirement)
    CGA->>LLM: 生成代码
    LLM-->>CGA: Python 代码
    CGA->>TR: register_from_code()
    CGA->>PTS: save_tool(name, code, desc, library)
    PTS->>FS: 创建/写入 tools/{library}/{name}.py
    
    %% 工具执行
    Note over C,TR: 工具执行阶段
    C->>TR: get_available_tools()
    TR-->>C: 工具列表 (带命名空间)
    C->>TR: 调用工具 ({namespace}-{tool_name})
    TR-->>C: 工具执行结果
```

## 工具命名空间组织

```mermaid
graph TD
    subgraph "ToolRegistry 命名空间"
        A[builtin_tools-get_elements_by_type]
        B[builtin_tools-extract_properties]
        C[ifcopenshell_tools-check_wall_thickness]
        D[ifcopenshell_tools-validate_door_size]
        E[pandas_tools-analyze_data]
        F[numpy_tools-calculate_metrics]
        G[requests_tools-fetch_api_data]
    end
    
    subgraph "文件系统映射"
        A --> A1[tools/builtin/get_elements_by_type.py]
        B --> B1[tools/builtin/extract_properties.py]
        C --> C1[tools/ifcopenshell/check_wall_thickness.py]
        D --> D1[tools/ifcopenshell/validate_door_size.py]
        E --> E1[tools/pandas/analyze_data.py]
        F --> F1[tools/numpy/calculate_metrics.py]
        G --> G1[tools/requests/fetch_api_data.py]
    end
```

## 关键改进点

### 🔄 **动态分类系统**
- **之前**: 固定分类列表 + 关键词匹配
- **现在**: LLM 智能判断 + 动态目录创建

### 📚 **库依赖管理**
- **ToolRequirement.library**: 明确指定主要库
- **自动目录创建**: tools/{library}/ 按需创建
- **命名空间**: {library}_tools-{function_name}

### 🔍 **工具检索**
- **启动时**: 扫描所有现有目录
- **运行时**: 通过 ToolRegistry 统一访问
- **命名空间**: 防止工具名称冲突

### 💾 **持久化策略**
- **分类存储**: 按库分目录存放
- **元数据跟踪**: metadata.json 记录所有工具信息
- **动态加载**: 支持新增库目录

这个流程确保了工具的智能分类、持久化存储和高效检索！