# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent building code compliance check system that uses three coordinated LLM-driven agents (Planner, Executor, Checker) to analyze building code text and check IFC file compliance. The system features step-by-step coordination, ReAct framework implementation, and comprehensive compliance reporting with real-time feedback loops.

## Common Development Tasks

### Running the Application

**Direct start:**
```bash
python main.py
```

**Run system tests:**
```bash
python test_system.py
```

### Development Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Testing with sample data:**
- Place regulation text in `test_regulation/` directory
- Use IFC test files from `test_ifc/` directory
- Run specific test files like `test_*.py` for component testing

### Configuration

**Required environment variables (.env file):**
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL_NAME=deepseek-chat  # or gpt-4, gpt-3.5-turbo
OPENAI_API_BASE=  # optional, for custom API endpoints
DEBUG=True
HOST=0.0.0.0
PORT=8000
MAX_FILE_SIZE=104857600  # 100MB
UPLOAD_DIR=./uploads
```

## System Architecture

### Core Components

**Multi-Agent Coordination System:**
- **Agent Coordinator** (`agents/coordinator.py`): Orchestrates step-by-step execution with feedback loops, manages communication between agents
- **Planner Agent** (`agents/planner.py`): Uses LLM to analyze regulation text and generate/modify structured execution plans
- **Executor Agent** (`agents/executor.py`): Implements ReAct framework for intelligent tool selection and execution
- **Checker Agent** (`agents/checker.py`): Evaluates execution results and generates comprehensive compliance reports

**Tool System** (`tool_library/tool_manager.py`):
- Dynamic tool loading and management system
- Tool dataclass with structured categories: validation, analysis, measurement, compliance, safety  
- Built-in tools: get_elements_by_type, extract_properties, basic_validation, dimension_measurement
- Tool Creator System (`agents/tool_creator/`): Automated tool generation with RAG, static checking, and testing

**Utilities:**
- **IFC Parser** (`tool_library/ifc_parser.py`): Parses IFC files using ifcopenshell, extracts building elements (walls, doors, windows, slabs)
- **LLM Client** (`utils/llm_client.py`): Handles OpenAI API communication with retry logic
- **Validation** (`utils/validation.py`): Input validation and error handling utilities
- **Vector Database** (`langchain_vectordb/`): LangChain/Chroma vector database for RAG retrieval in tool creation

**Data Models** (`models/`):
- **API Models** (`api_models.py`): FastAPI request/response models
- **Agent Models** (`agent_models.py`): Agent communication models  
- **Shared Models** (`shared_models.py`): Common data structures

### Data Flow

1. **Input Processing**: User provides regulation text + IFC file via FastAPI web interface
2. **Plan Generation**: Coordinator requests initial plan from Planner agent
3. **Step-by-Step Execution**: Coordinator executes plan steps one by one using Executor
4. **Real-Time Feedback**: Failed steps trigger plan modification requests to Planner
5. **Compliance Evaluation**: Checker analyzes all execution results against regulation requirements
6. **Report Generation**: System returns comprehensive compliance report with coordination details

### API Endpoints

- `POST /check`: Main compliance check endpoint (regulation text + IFC file upload)
- `POST /preview-ifc`: IFC file preview endpoint for 3D visualization
- `GET /health`: System health check with component status
- `GET /`: Web interface (HTML form)

## Key Implementation Details

### ReAct Framework in Executor

The Executor agent implements ReAct (Reasoning + Acting) with intelligent tool selection:

```python
# ReAct cycle for each step
1. **Thought**: LLM analyzes current situation and plans approach
2. **Action**: LLM selects appropriate tool and parameters  
3. **Observation**: Tool execution results are analyzed
4. **Decision**: Determine if task is complete or continue iteration
```

### Tool Structure

Tools follow structured dataclass format:
```python
@dataclass
class Tool:
    name: str
    description: str
    category: str  # validation, analysis, measurement, compliance, safety
    function: Callable
    parameters_schema: Dict[str, Any]

def tool_function(ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "result": "pass|fail", 
        "detail": "description",
        "elements_checked": [],
        "issues": []
    }
```

### Agent Coordination

The system uses message-based communication between agents:
- Structured request/response messages with timestamps
- Communication logging for debugging and analysis
- Feedback rounds with maximum iteration limits
- Step-by-step execution with immediate feedback

### Tool Creator System

The automated tool generation system includes:
- **RAG Retriever**: Uses LangChain/Chroma vector database to find relevant documentation
- **Code Generator**: LLM-powered code generation with contextual assistance
- **Static Checker**: Validates generated code syntax and basic structure  
- **Unit Tester**: Dynamically tests generated functions with example inputs
- **IFC Generator**: Creates realistic test data for IFC-related tools
- **Safe Executor**: Isolated execution environment for testing generated code

### Error Handling

- **Agent Communication**: Structured error messages and fallback mechanisms
- **Tool Execution**: Comprehensive error catching with detailed failure reporting
- **LLM API Failures**: Retry logic with exponential backoff
- **File Processing**: Validation before processing with clear error messages

## File Organization

```
├── agents/           # Multi-agent system
│   ├── coordinator.py    # Main coordination logic
│   ├── planner.py       # Plan generation and modification
│   ├── executor.py      # ReAct-based execution engine  
│   ├── checker.py       # Compliance evaluation
│   └── tool_creator/    # Automated tool generation system
│       ├── data_models.py      # Tool creation data structures
│       ├── too_creator.py      # Main code generator agent
│       ├── rag_retriever.py    # RAG document retrieval
│       ├── static_checker.py   # Static code analysis
│       ├── unit_tester.py      # Dynamic testing
│       └── executor.py         # Safe code execution
├── tool_library/     # Tool management system
│   ├── tool_manager.py  # Dynamic tool loading
│   └── ifc_parser.py    # IFC file processing
├── utils/           # Utility modules
│   ├── llm_client.py    # OpenAI API client
│   └── validation.py    # Input validation
├── models/          # Data models
│   ├── api_models.py    # FastAPI models
│   ├── agent_models.py  # Agent communication
│   └── shared_models.py # Common structures
├── langchain_vectordb/ # Vector database for RAG
├── templates/       # Web interface templates
├── test_ifc/        # Test IFC files
├── test_regulation/ # Test regulation texts
├── uploads/         # Temporary file storage
├── main.py          # FastAPI application
├── config.py        # Configuration management
└── test.py          # Development testing
```

## Development Guidelines

### Adding New Tools

**Manual Method:**
1. Define tool function with standard signature in `tool_library/tool_manager.py` 
2. Create Tool dataclass with proper category and parameter schema
3. Add to `_load_basic_tools()` method in ToolManager
4. Test tool functionality independently

**Automated Method (Tool Creator System):**
1. Define ToolRequirement with description, parameters, and examples
2. Use CodeGeneratorAgent to generate tool automatically with RAG assistance
3. System includes static checking, unit testing, and IFC test data generation
4. Generated tools are validated and can be integrated into the tool library

### Extending Agents

- Modify system prompts in agent classes to adjust behavior
- Agent communication uses structured message format
- Add new agent methods following existing patterns
- Update coordination logic in `coordinator.py` if needed

### IFC Processing

- Always use `tool_library.ifc_parser.IFCParser` for consistent file handling
- Extract standard building elements: walls, doors, windows, slabs, beams, columns
- Handle file loading errors gracefully
- Use `get_elements_by_type()` method for element extraction
- Use `extract_properties()` method for property information

### Testing

Run comprehensive tests before changes:
```bash
python test.py          # Development testing with sample data
python test_system.py   # Full system test (if available)
```

**Testing with sample data:**
- Place regulation texts in `test_regulation/` directory (1.txt, 2.txt)
- Use IFC test files from `test_ifc/` directory (AC20.ifc) 
- Test individual components by importing and running them in `test.py`

**Tool Creator Testing:**
The system includes automated testing for generated tools with IFC test data generation and validation.