
import json
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
import re
from utils.llm_client import LLMClient
from tool_library.tool_manager import ToolManager

@dataclass
class ReActStep:
    """ReAct step result"""
    thought: str
    action: str
    action_input: Dict[str, Any]
    should_continue: bool
    
class Executor:
   
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClient()
        self.execution_history = []
        self.tool_manager = ToolManager()
        
        # Build ReAct system prompt
        self.system_prompt = self._build_react_system_prompt()
    
    def _build_react_system_prompt(self) -> str:
        """Build ReAct system prompt with dynamic tool information"""
        
        # Get available tool information
        available_tools = self._get_available_tools()
        tools_section = self._format_tools_for_prompt(available_tools)
        
        return """
        You are an intelligent building compliance checker using the ReAct (Reasoning and Acting) framework.

        ## ReAct Framework Process
        For each task, follow this iterative cycle until completion:

        1. **Thought**: Analyze the current situation and plan your next step
        2. **Action**: Choose which tool to use
        3. **Action Input**: Specify the input parameters for the tool
        4. **Observation**: [This will be filled by the system with actual tool results]
        5. **Continue or Finish**: Determine if you need another cycle

        ## Available Tools
        {tools_section}

        ## Response Format
        You must respond with ONLY the following JSON structure:

        ```json
        {{
            "thought": "Your reasoning about what needs to be done next",
            "action": "exact_tool_name_from_available_tools",
            "action_input": {{
                "parameter_name": "parameter_value"
            }},
            "is_final": false
        }}

        When the task is complete, set "is_final": true and omit the action fields.
        
        IMPORTANT: The "action" field must contain the exact tool name from the available tools list above.
        The "action_input" must contain the parameters required by the selected tool.

        ## Guidelines
        -Tool Selection Strategy
        Identify requirements: What specific elements or data do you need?
        Choose appropriate tools: Select tools that match your current needs
        Extract systematically: Use multiple calls if needed for different element types
        Focus on data extraction: Your role is to gather information, not perform compliance checks

        -Error Handling
        If a tool fails, analyze the error and try alternative approaches
        Use simpler tools or different parameters if complex ones fail
        Always explain your reasoning in the "thought" field

        -Efficiency Tips
        Complete tasks in minimum steps while being thorough
        Combine related operations when possible
        Be specific about element types and parameters

        ## Example Responses
        
        Example 1 - Element extraction:
        ```json
        {{
            "thought": "I need to extract all door elements first to analyze their dimensions. I'll start by getting all IfcDoor elements from the building model.",
            "action": "get_elements_by_type",
            "action_input": {{
                "element_type": "IfcDoor"
            }},
            "is_final": false
        }}
        ```
        
        """.format(tools_section=tools_section)
    
    def _get_available_tools(self) -> Dict[str, Dict[str, str]]:
        """Get available tools from tool manager"""
        tools_info = {}
        
        for tool_name, tool in self.tool_manager.get_all_tools().items():
            # 构建参数描述
            params_desc = []
            for param_name, param_info in tool.parameters_schema.items():
                required = "(required)" if param_info.get("required", False) else "(optional)"
                params_desc.append(f"{param_name} {required}: {param_info.get('description', 'No description')}")
            
            tools_info[tool_name] = {
                "description": tool.description,
                "category": tool.category,
                "parameters": "; ".join(params_desc) if params_desc else "No parameters required",
                "usage": f"Use this tool for {tool.category} tasks",
                "example": f'{{"parameter": "value"}} - {tool.description}'
            }
        
        return tools_info
    
    def _format_tools_for_prompt(self, tools: Dict[str, Dict[str, str]]) -> str:
        """Format tool information for prompt format"""
        tools_text = "Available tools for building compliance checking:\n\n"
        
        for tool_name, info in tools.items():
            tools_text += f"""
            ### {tool_name} ({info.get('category', 'general')})
            - **Description**: {info['description']}
            - **Usage**: {info['usage']} 
            - **Parameters**: {info['parameters']}
            - **Example**: {info['example']}

            """
        return tools_text
            
    
    def execute_step(self, 
                    step: Dict[str, Any], 
                    ifc_file_path: str,
                    max_iterations: int = 5) -> Dict[str, Any]:
       
        # Initialize execution context
        context = {
            "step": step,
            "ifc_file_path": ifc_file_path,
            "history": [],
        }
        
        # Initial state
        current_state = {
            "observation": f"Starting task: {step.get('description', 'Unknown task')}",
            "completed": False,
            "result": None
        }
        
        # Keep track of tool execution results
        tool_execution_results = []
        
        # ReAct loop
        for iteration in range(max_iterations):
            print(f"\n=== ReAct Iteration {iteration + 1}/{max_iterations} ===")
            
            # 1. Get LLM's thought and action plan (single call)
            react_response = self._get_react_response(
                step=step,
                current_state=current_state,
                history=context["history"],
                iteration=iteration,
                context=context
            )
            
            # 2. Validate and parse response
            if not self._validate_react_response(react_response):
                return self._create_error_result(
                    step_id=step.get("step_id"),
                    error="Invalid ReAct response format"
                )
            
            # 3. Check if completed first
            if react_response.get("is_final", False):
                # Record final thinking process
                context["history"].append({
                    "iteration": iteration + 1,
                    "thought": react_response["thought"],
                    "action": "completed"
                })
                return self._create_success_result(
                    step_id=step.get("step_id"),
                    result=react_response.get("action_input", {"message": "Task completed successfully"}),
                    history=context["history"],
                    iterations_used=iteration + 1,
                    tool_results=tool_execution_results
                )
            
            # 4. Record thinking process for non-final responses
            context["history"].append({
                "iteration": iteration + 1,
                "thought": react_response["thought"],
                "action": react_response["action"]
            })
            
            # 5. Execute action
            action_result = self._execute_action(
                action_name=react_response["action"],
                action_input=react_response["action_input"],
                context=context
            )
            
            # Save tool execution result if successful
            if action_result.get("success") and "result" in action_result:
                tool_execution_results.append(action_result["result"])
            
            # 6. Update state
            current_state = {
                "observation": self._format_observation(action_result),
                "last_action": react_response["action"],
                "last_result": action_result
            }
            
            # 7. Check if early termination needed
            if action_result.get("critical_failure", False):
                return self._create_error_result(
                    step_id=step.get("step_id"),
                    error=action_result.get("error", "Critical failure"),
                    history=context["history"],
                    status="failed"
                )
        
        # Reached maximum iterations
        return self._create_timeout_result(
            step_id=step.get("step_id"),
            history=context["history"],
            max_iterations=max_iterations
        )
    
    def _get_react_response(self, 
                           step: Dict[str, Any],
                           current_state: Dict[str, Any],
                           history: List[Dict[str, Any]],
                           iteration: int,
                           context: Dict[str, Any]) -> Dict[str, Any]:
        
        # Build history summary
        history_summary = self._build_history_summary(history)
        
        prompt = f"""
        Current Task: {step.get('description', 'Unknown')}
        Task Type: {step.get('task_type', 'general')}
        Expected Outcome: {step.get('expected_output', 'Complete the task successfully')}
        Current Observation: {current_state.get('observation', 'No observation yet')}
        Iteration: {iteration + 1}/5
        Previous Actions Summary: {history_summary if history_summary else "This is the first action."}
        IFC File Path: {context['ifc_file_path']}

        Based on the current situation, what should be the next action? 
        Remember to think step by step and choose the most appropriate tool from the available tools.
        """
                
        try:
            response = self.llm_client.generate_response(prompt, self.system_prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            print(f"LLM call failed: {e}")
            raise RuntimeError(f"ReAct LLM call failed: {e}") from e
    
    
    def _execute_action(self, 
                       action_name: str, 
                       action_input: Dict[str, Any],
                       context: Dict[str, Any]) -> Dict[str, Any]:
        
        # Special action: final answer
        if action_name == "final_answer":
            return {
                "success": True,
                "result": action_input,
                "is_final": True
            }
        
        # Use LLM-selected tool name directly
        selected_tool = action_name
        
        # Check if tool exists
        if not self.tool_manager.get_tool(selected_tool):
            return {
                "success": False,
                "error": f"Tool '{selected_tool}' not found in tool library",
                "tool_name": selected_tool,
                "available_tools": list(self.tool_manager.get_all_tools().keys()),
                "critical_failure": False
            }
        
        # Execute the LLM-selected tool with LLM-provided parameters
        try:
            result = self.tool_manager.execute_tool(
                tool_name=selected_tool,
                ifc_file_path=context["ifc_file_path"],
                parameters=action_input
            )
            
            return {
                "success": True,
                "tool_name": selected_tool,
                "parameters_used": action_input,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": selected_tool,
                "parameters_used": action_input,
                "critical_failure": "critical" in str(e).lower()
            }
    
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:    
        # Try direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try extracting JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try extracting content between braces
        brace_match = re.search(r'\{.*\}', response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except:
                pass
        
        # If all fail, try extracting information from text
        return self._extract_from_text(response)
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract information from unstructured text"""
        # This is the last fallback option
        thought_match = re.search(r'thought[:\s]+(.*?)(?:action|$)', text, re.IGNORECASE | re.DOTALL)
        action_match = re.search(r'action[:\s]+(.*?)(?:action_input|$)', text, re.IGNORECASE | re.DOTALL)
        
        return {
            "thought": thought_match.group(1).strip() if thought_match else "Unable to parse thought",
            "action": action_match.group(1).strip() if action_match else "basic_validation",
            "action_input": {},
            "is_final": False
        }
    
    def _validate_react_response(self, response: Dict[str, Any]) -> bool:
        """Validate ReAct response format"""
        # Check if response has thought
        if "thought" not in response:
            return False
        
        # If it's a final response, only thought and is_final are required
        if response.get("is_final", False):
            return True
            
        # For non-final responses, action and action_input are required
        required_fields = ["thought", "action", "action_input"]
        return all(field in response for field in required_fields)
    
    def _format_observation(self, action_result: Dict[str, Any]) -> str:
        """Format action result as observation description"""
        if action_result.get("success"):
            tool_name = action_result.get("tool_name", "unknown tool")
            result_summary = self._summarize_result(action_result.get("result", {}))
            return f"Successfully executed {tool_name}. Result: {result_summary}"
        else:
            error = action_result.get("error", "Unknown error")
            return f"Action failed: {error}"
    
    def _summarize_result(self, result: Any) -> str:
        """Generate result summary"""
        if isinstance(result, dict):
            if "summary" in result:
                return result["summary"]
            # Extract key information
            key_info = []
            for k, v in result.items():
                if k in ["status", "count", "value", "measurement", "compliant"]:
                    key_info.append(f"{k}={v}")
            return ", ".join(key_info) if key_info else str(result)
        else:
            return str(result)
    
    def _build_history_summary(self, history: List[Dict[str, Any]]) -> str:
        """Build history summary"""
        if not history:
            return ""
        
        summaries = []
        for h in history[-3:]:  # Only show last 3 actions
            summaries.append(
                f"Step {h['iteration']}: {h['action']} - {h['thought'][:100]}..."
            )
        
        return "\n".join(summaries)
    
    def get_available_tools_info(self) -> str:
        """Get formatted information about available tools for external use"""
        tools_info = "Available Tools:\n"
        tools_info += "=" * 50 + "\n"
        
        for tool_name, tool in self.tool_manager.get_all_tools().items():
            tools_info += f"\n**{tool_name}** ({tool.category})\n"
            tools_info += f"Description: {tool.description}\n"
            
            if tool.parameters_schema:
                tools_info += "Parameters:\n"
                for param_name, param_info in tool.parameters_schema.items():
                    required = "(required)" if param_info.get("required", False) else "(optional)"
                    tools_info += f"  - {param_name} {required}: {param_info.get('description', 'No description')}\n"
            else:
                tools_info += "Parameters: None\n"
            
            tools_info += "-" * 30 + "\n"
        
        return tools_info
    
    # === Result creation methods ===
    
    def _create_success_result(self, step_id: str, result: Any, history: List, iterations_used: int, tool_results: List = None) -> Dict[str, Any]:
        success_result = {
            "status": "success",
            "step_id": step_id,
            "result": result,
            "iterations_used": iterations_used,
            "execution_history": history
        }
        
        # Add tool execution results if available
        if tool_results:
            success_result["tool_results"] = tool_results
            # If we have tool results, use the last one as primary result for backward compatibility
            if tool_results:
                success_result["primary_tool_result"] = tool_results[-1]
        
        return success_result
    
    def _create_error_result(self, step_id: str, error: str, history: List = None, status: str = "error") -> Dict[str, Any]:
        """Create error/failure result"""
        result = {
            "status": status,
            "step_id": step_id,
            "error": error
        }
        
        # Add execution history if provided
        if history is not None:
            result["execution_history"] = history
            
        return result
    
    def _create_timeout_result(self, step_id: str, history: List, max_iterations: int) -> Dict[str, Any]:
        """Create timeout result"""
        return {
            "status": "timeout",
            "step_id": step_id,
            "error": f"Exceeded maximum iterations ({max_iterations})",
            "execution_history": history
        }
    
    def execute_single_step(self, step: Dict[str, Any], ifc_file_path: str, step_id: int) -> Dict[str, Any]:
        """
        Execute single step - this is the primary interface for Coordinator
        
        This method wraps execute_step with additional context and status mapping
        for better integration with the Coordinator.
        
        Args:
            step: Single step from plan
            ifc_file_path: Path to IFC file
            step_id: Id of step in plan

        Returns:
            Dict: Step execution result with step_status field
        """
        print(f"Executor: Executing single step {step_id}: {step.get('description', 'Unknown')}")
        
        try:
            # Execute step using ReAct framework
            result = self.execute_step(step, ifc_file_path)
            
            # Map result status to step_status for coordinator compatibility
            if result.get("status") == "success":
                result["step_status"] = "success"
                result["step_result"] = result.get("result", {})
            elif result.get("status") == "timeout":
                result["step_status"] = "failed"
                result["failure_reason"] = "timeout"
                result["error_message"] = result.get("error", "Step execution timeout")
            else:
                result["step_status"] = "failed" 
                result["failure_reason"] = "execution_failure"
                result["error_message"] = result.get("error", "Step execution failed")
            
            return result
            
        except Exception as e:
            print(f"Executor: Single step execution failed with exception: {e}")
            return {
                "step_status": "failed",
                "failure_reason": "exception",
                "error_message": str(e),
                "status": "error"
            }
    

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get execution history for compatibility with coordinator
        
        Returns:
            List: Execution history records
        """
        return self.execution_history.copy()

