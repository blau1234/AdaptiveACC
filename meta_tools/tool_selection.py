import json
from typing import Dict, List, Any, Optional
from utils.llm_client import LLMClient
from utils.rag_tool import ToolVectorManager
from toolregistry import ToolRegistry


class ToolSelector:
    """
    Meta Tool for intelligent tool selection using two-phase approach:
    1. Semantic search to find top K candidate tools
    2. LLM generative selection to pick the best one
    """
    
    def __init__(self, tool_registry: ToolRegistry, tool_vector_db=None):
        self.tool_registry = tool_registry
        # Use ToolVectorManager for tool vector operations, fallback to passed tool_vector_db
        if tool_vector_db is None:
            try:
                self.tool_vector_db = ToolVectorManager(vectordb_path="vectordb/tools", collection_name="tool_vectors")
            except Exception as e:
                print(f"Warning: Could not initialize tool vector database: {e}")
                self.tool_vector_db = None
        else:
            self.tool_vector_db = tool_vector_db
        
        self.llm_client = LLMClient()
    
    # executor interface
    def tool_selection(self, step_description: str, execution_context: str = "") -> str:
        """
        Executor interface for tool selection using two-phase approach
        
        Args:
            step_description: Description of the step to find tools for
            execution_context: JSON string of current execution context
            
        Returns:
            JSON string with selected tool information or error
        """
        try:
            # Parse execution context if provided
            context = {}
            if execution_context:
                try:
                    context = json.loads(execution_context)
                except:
                    context = {"context_parse_error": True}
            
            print(f"ToolSelector: Starting tool selection for '{step_description[:50]}...'")
            
            # Execute two-phase selection
            selection_result = self.select_best_tool(
                step_description=step_description,
                step_context=context,
                k=5
            )
            
            if selection_result:
                return json.dumps({
                    "success": True,
                    "tool": selection_result["tool_schema"]
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": "No suitable tool found for the given step"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool selection failed: {str(e)}",
                "step_description": step_description
            })

    def semantic_search_tools(self, step_description: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Phase 1: Semantic search to find top K relevant tools
        
        Args:
            step_description: Description of the step to find tools for
            k: Number of top tools to return
            
        Returns:
            List of tool metadata dictionaries
        """
        if self.tool_vector_db is None:
            print("Warning: Tool vector database not available, returning empty list")
            return []
        
        try:
            # Execute semantic search
            relevant_tools = self.tool_vector_db.search_tools(step_description, k=k)
            print(f"Found {len(relevant_tools)} relevant tools for: '{step_description[:50]}...'")
            
            return relevant_tools
        except Exception as e:
            print(f"Error in semantic tool search: {e}")
            return []
    
    def get_focused_tools_schema(self, relevant_tool_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get complete tool schemas for the semantically relevant tools
        
        Args:
            relevant_tool_metadata: List of tool metadata from semantic search
            
        Returns:
            List of complete tool schemas with parameters
        """
        focused_tools = []
        
        # Get all tools' complete schema
        all_tools_schema = self.tool_registry.get_tools_json()
        
        # Create mapping from tool name to schema
        tools_by_name = {}
        for tool_schema in all_tools_schema:
            if 'function' in tool_schema and 'name' in tool_schema['function']:
                tools_by_name[tool_schema['function']['name']] = tool_schema
        
        # Filter schemas based on relevant tool metadata
        for metadata in relevant_tool_metadata:
            tool_name = metadata.get('tool_name')
            
            # Try exact match first
            if tool_name in tools_by_name:
                focused_tools.append(tools_by_name[tool_name])
                print(f"Added {tool_name} to focused tools schema")
            else:
                # Try to find with namespace prefix (e.g., builtin_tools-tool_name)
                for schema_tool_name, schema in tools_by_name.items():
                    if schema_tool_name.endswith(f"-{tool_name}") or schema_tool_name.endswith(f"_{tool_name}"):
                        focused_tools.append(schema)
                        print(f"Added {schema_tool_name} (matched {tool_name}) to focused tools schema")
                        break
        
        return focused_tools
    
    def generative_tool_selection(self, step_description: str, candidate_tools: List[Dict[str, Any]], 
                                step_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Phase 2: LLM-based generative selection to pick the best tool
        
        Args:
            step_description: Description of the step to execute
            candidate_tools: List of candidate tool schemas from semantic search
            step_context: Additional context about the current execution state
            
        Returns:
            Selected tool schema with reasoning, or None if no suitable tool
        """
        if not candidate_tools:
            return None
        
        # Build detailed prompt with tool information
        tools_info = self._format_tools_for_selection(candidate_tools)
        context_info = self._format_context_for_selection(step_context) if step_context else ""
        
        prompt = f"""
You are an intelligent tool selection agent. Select the most appropriate tool for the given step.

## Step to Execute
{step_description}

{context_info}

## Available Tools
{tools_info}

## Selection Criteria
1. **Relevance**: How well does the tool match the step requirements?
2. **Parameters**: Does the tool have the right parameters for the task?
3. **Output**: Will the tool produce the expected output for next steps?
4. **Context**: Does the tool fit the current execution context?

Return only the exact tool name from the list above. If no tool is suitable, return "null".
"""
        
        try:
            response = self.llm_client.generate_response(prompt, timeout=30, max_tokens=100)
            
            # Clean and extract tool name
            selected_tool_name = response.strip().strip('"').strip()
            
            if selected_tool_name and selected_tool_name.lower() != "null":
                # Find the selected tool schema
                for tool_schema in candidate_tools:
                    if tool_schema.get('function', {}).get('name') == selected_tool_name:
                        return {"tool_schema": tool_schema}
            
            print(f"LLM could not select a suitable tool or returned: {selected_tool_name}")
            return None
            
        except Exception as e:
            print(f"Error in generative tool selection: {e}")
            return None
    
    def select_best_tool(self, step_description: str, step_context: Optional[Dict[str, Any]] = None, 
                        k: int = 5) -> Optional[Dict[str, Any]]:
        """
        Complete two-phase tool selection process
        
        Args:
            step_description: Description of the step to find tools for
            step_context: Additional context about the current execution state
            k: Number of candidates to get from semantic search
            
        Returns:
            Best selected tool with schema and reasoning, or None
        """
        print(f"Starting two-phase tool selection for: {step_description[:100]}...")
        
        # Phase 1: Semantic search
        relevant_tools_metadata = self.semantic_search_tools(step_description, k=k)
        if not relevant_tools_metadata:
            print("No tools found in semantic search")
            return None
        
        # Get detailed schemas for candidates
        candidate_tools_schema = self.get_focused_tools_schema(relevant_tools_metadata)
        if not candidate_tools_schema:
            print("No tool schemas found for semantic search results")
            return None
        
        print(f"Phase 1 complete: {len(candidate_tools_schema)} candidate tools")
        
        # Phase 2: LLM generative selection
        selected_tool = self.generative_tool_selection(step_description, candidate_tools_schema, step_context)
        
        if selected_tool:
            tool_name = selected_tool['tool_schema']['function']['name']
            print(f"Phase 2 complete: Selected '{tool_name}'")
            return selected_tool
        else:
            print("Phase 2 complete: No suitable tool selected")
            return None
    
    def _format_tools_for_selection(self, tools: List[Dict[str, Any]]) -> str:
        """Format tool schemas for LLM selection prompt"""
        formatted_tools = []
        
        for i, tool in enumerate(tools, 1):
            function_info = tool.get('function', {})
            name = function_info.get('name', 'unknown')
            description = function_info.get('description', 'No description')
            parameters = function_info.get('parameters', {})
            
            # Format parameters
            params_info = []
            if 'properties' in parameters:
                for param_name, param_info in parameters['properties'].items():
                    param_type = param_info.get('type', 'unknown')
                    param_desc = param_info.get('description', 'No description')
                    required = param_name in parameters.get('required', [])
                    req_str = " (required)" if required else " (optional)"
                    params_info.append(f"  - {param_name}: {param_type}{req_str} - {param_desc}")
            
            params_str = "\n".join(params_info) if params_info else "  No parameters"
            
            formatted_tools.append(f"""
                {i}. **{name}**
                Description: {description}
                Parameters:
                {params_str}""")
        
        return "\n".join(formatted_tools)
    
    def _format_context_for_selection(self, context: Dict[str, Any]) -> str:
        """Format execution context for LLM prompt"""
        context_parts = []
        
        if context.get('ifc_file_path'):
            context_parts.append(f"- IFC File: {context['ifc_file_path']}")
        
        if context.get('previous_results'):
            context_parts.append(f"- Previous Results Available: {len(context['previous_results'])} items")
        
        if context.get('current_step_index'):
            context_parts.append(f"- Current Step: {context['current_step_index']}")
        
        if context.get('execution_history'):
            context_parts.append(f"- Execution History: {len(context['execution_history'])} previous steps")
        
        if context_parts:
            return f"\n## Current Context\n" + "\n".join(context_parts) + "\n"
        else:
            return ""

    