import json
from typing import Dict, List, Any, Optional
from utils.llm_client import LLMClient
from models.common_models import MetaToolResult
from models.shared_context import SharedContext
from domain_tools.domain_tool_registry import DomainToolRegistry

class ToolSelection:
    """Meta tool to select the best tool for a given step using two-phase approach"""

    def __init__(self):
        self.domain_registry = DomainToolRegistry.get_instance()
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()
    
    # executor Interface
    def select_best_tool(self) -> MetaToolResult:
        """Two-phase tool selection: semantic search followed by LLM selection"""

        try:
            # Get current step and context from SharedContext
            current_step = self.shared_context.current_task.get("step", {})
            step_description = current_step.get("description", "")

            print(f"ToolSelector: Starting tool selection for '{step_description[:50]}...'")

            # Phase 1: Semantic search
            relevant_tools_metadata = self.semantic_search_tools(step_description, k=5)
            if not relevant_tools_metadata:
                print("No tools found in semantic search")
                return MetaToolResult(
                    success=False,
                    meta_tool_name="tool_selection",
                    error="No tools found in semantic search"
                )

            print(f"Phase 1 complete: {len(relevant_tools_metadata)} candidate tools")

            # Phase 2: LLM generative selection using metadata directly
            selected_tool = self.generative_tool_selection(step_description, relevant_tools_metadata, current_step)

            if selected_tool:
                tool_name = selected_tool.get('tool_name', 'unknown')
                print(f"Phase 2 complete: Selected '{tool_name}'")
                return MetaToolResult(
                    success=True,
                    meta_tool_name="tool_selection",
                    result={"tool": selected_tool}
                )
            else:
                print("Phase 2 complete: No suitable tool selected")
                return MetaToolResult(
                    success=False,
                    meta_tool_name="tool_selection",
                    error="No suitable tool found for the given step"
                )

        except Exception as e:
            return MetaToolResult(
                success=False,
                meta_tool_name="tool_selection",
                error=f"Tool selection failed: {str(e)}"
            )
 

    def semantic_search_tools(self, step_description: str, k: int = 5) -> List[Dict[str, Any]]:
        
        try:
            # Get singleton vector database instance
            from utils.rag_tool import ToolVectorManager
            tool_vector_db = ToolVectorManager.get_instance()
            
            if not tool_vector_db.is_available():
                print("Warning: Tool vector database not available, returning empty list")
                return []
            
            # Execute semantic search
            relevant_tools = tool_vector_db.search_tools(step_description, k=k)
            print(f"Found {len(relevant_tools)} relevant tools for: '{step_description[:50]}...'")
            
            return relevant_tools
        except Exception as e:
            print(f"Error in semantic tool search: {e}")
            return []
    
    
    def generative_tool_selection(self, step_description: str, candidate_tools: List[Dict[str, Any]], 
                                current_step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use LLM to select the best tool from candidates based on step description and context"""

        if not candidate_tools:
            return None
        
        # Build detailed prompt with tool information
        tools_info = self._format_tools_for_selection(candidate_tools)
        context_info = self._format_context_for_selection(current_step)

        # System prompt: role and rules
        system_prompt = """You are an intelligent tool selection agent specialized in building compliance checking workflows.

        Your task is to select the most appropriate tool for executing a given step based on:
        1. **Relevance**: How well does the tool match the step requirements?
        2. **Parameters**: Does the tool have the right parameters for the task?
        3. **Output**: Will the tool produce the expected output?
        4. **Context**: Does the tool fit the current execution context?

        IMPORTANT: Return only the exact tool name from the available tools list. If no tool is suitable, return "null"."""

        # User prompt: specific data
        user_prompt = f"""
        ## Step to Execute
        {step_description}
        
        ## Execution Context
        {context_info}

        ## Available Tools
        {tools_info}

        Select the best tool:"""

        try:
            response = self.llm_client.generate_response(user_prompt, system_prompt=system_prompt)
            
            # Clean and extract tool name
            selected_tool_name = response.strip().strip('"').strip()
            
            if selected_tool_name and selected_tool_name.lower() != "null":
                # Find the selected tool metadata
                for tool_metadata in candidate_tools:
                    if tool_metadata.get('tool_name') == selected_tool_name:
                        return tool_metadata
            
            print(f"LLM could not select a suitable tool or returned: {selected_tool_name}")
            return None
            
        except Exception as e:
            print(f"Error in generative tool selection: {e}")
            return None
    
   
    def _format_tools_for_selection(self, tools: List[Dict[str, Any]]) -> str:
        """Format tool metadata for LLM selection prompt"""
        formatted_tools = []

        for i, tool in enumerate(tools, 1):
            name = tool.get('tool_name', 'unknown')
            description = tool.get('description', 'No description')
            parameters = tool.get('parameters', '')
            category = tool.get('category', 'unknown')

            # Format parameters (already a string from metadata)
            params_str = f"  Parameters: {parameters}" if parameters else "  No parameters"

            formatted_tools.append(f"""
                {i}. **{name}** (Category: {category})
                Description: {description}
                {params_str}""")

        return "\n".join(formatted_tools)

    def _format_context_for_selection(self, current_step: Dict[str, Any]) -> str:
        """Format execution context for LLM prompt with specific content details"""
        
        context_parts = []

        # Step information
        step_index = self.shared_context.current_task.get("step_index")
        if step_index is not None:
            context_parts.append(f"- Current Step: {step_index}")

        # Task type
        task_type = current_step.get("task_type", "")
        if task_type:
            context_parts.append(f"- Task Type: {task_type}")

        # Step inputs with specific content
        step_inputs = current_step.get("inputs", {})
        if step_inputs:
            inputs_str = ", ".join([f"{k}: {v}" for k, v in step_inputs.items()])
            context_parts.append(f"- Step Inputs: {inputs_str}")

        # All execution history with specific content
        recent_results = self.shared_context.process_trace
        if recent_results:
            context_parts.append(f"- Execution History ({len(recent_results)} steps):")
            for i, result in enumerate(recent_results):  # Show all results
                if isinstance(result, dict):
                    summary = result.get('summary', 'No summary')
                    agent = result.get('agent', 'unknown')
                    status = result.get('status', 'unknown')
                    context_parts.append(f"  * {agent}: {summary} ({status})")
                else:
                    context_parts.append(f"  * Result {i}: {str(result)[:100]}...")

        if context_parts:
            return f"\n## Current Context\n" + "\n".join(context_parts) + "\n"
        else:
            return ""

