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

**Tool System** (`tools/default_tool_library.py`):
- Default tool library with structured Tool dataclass
- Categories: validation, analysis, measurement, compliance, safety
- Built-in tools: basic_validation, file_analyzer, element_checker, dimension_measurement, accessibility_checker, safety_compliance

**Utilities:**
- **IFC Parser** (`utils/ifc_parser.py`): Parses IFC files using ifcopenshell, extracts building elements (walls, doors, windows, slabs)
- **LLM Client** (`utils/llm_client.py`): Handles OpenAI API communication with retry logic
- **Validation** (`utils/validation.py`): Input validation and error handling utilities

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
│   └── checker.py       # Compliance evaluation
├── tools/           # Tool library system
│   └── default_tool_library.py  # Built-in tools
├── utils/           # Utility modules
│   ├── ifc_parser.py    # IFC file processing
│   ├── llm_client.py    # OpenAI API client
│   └── validation.py    # Input validation
├── models/          # Data models
│   ├── api_models.py    # FastAPI models
│   ├── agent_models.py  # Agent communication
│   └── shared_models.py # Common structures
├── templates/       # Web interface templates
├── test_ifc/        # Test IFC files
├── test_regulation/ # Test regulation texts
├── main.py          # FastAPI application
├── config.py        # Configuration management
└── test_system.py   # System tests
```

## Development Guidelines

### Adding New Tools

1. Define tool function with standard signature in `tools/default_tool_library.py`
2. Create Tool dataclass with proper category and parameter schema
3. Add to `create_default_tool_library()` function
4. Test tool functionality independently

### Extending Agents

- Modify system prompts in agent classes to adjust behavior
- Agent communication uses structured message format
- Add new agent methods following existing patterns
- Update coordination logic in `coordinator.py` if needed

### IFC Processing

- Always use `utils.ifc_parser.IFCParser` for consistent file handling
- Extract standard building elements: walls, doors, windows, slabs
- Handle file loading errors gracefully

### Testing

Run comprehensive tests before changes:
```bash
python test_system.py  # Full system test
python test_*.py       # Individual component tests
```

The test suite includes mocking for external dependencies and covers all major system components.