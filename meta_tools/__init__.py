"""
Meta Tools Package - Tool Lifecycle Management

This package provides a comprehensive set of Meta Tools for managing the lifecycle
of domain-specific tools, from creation to execution.

Components:
- ToolSelector: Two-phase tool selection (semantic search + LLM selection)
- ToolExecutor: Intelligent tool execution with parameter preparation
- ToolRegistrar: Tool registration with validation and conflict detection
- ToolStorage: Unified tool storage (filesystem + vector database)
- ToolCreatorAgent: Dynamic tool creation system
- MetaToolManager: Unified interface coordinating all meta tools

Usage:
    from meta_tools import MetaToolManager
    
    manager = MetaToolManager(tool_registry, tool_vector_db)
    # Use as ReAct tools or directly
"""

from .tool_selection import ToolSelector
from .tool_execution import ToolExecutor
from .tool_registration import ToolRegistrar
from .tool_storage import ToolStorage
from .meta_tool_manager import MetaToolManager
from .tool_creation.tool_creator import ToolCreatorAgent

__version__ = "1.0.0"
__author__ = "Meta Tools System"

__all__ = [
    "ToolSelector",
    "ToolExecutor", 
    "ToolRegistrar",
    "ToolStorage",
    "MetaToolManager",
    "ToolCreatorAgent"
]