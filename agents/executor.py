
import json
from typing import Dict, List, Any
import uuid
from utils.llm_client import LLMClient
from toolregistry import ToolRegistry
from meta_tools.meta_tool_manager import MetaToolManager
from data_models.shared_models import ReActResponse
from shared_context import SharedContext
    

class Executor:
   
    def __init__(self, llm_client=None, shared_context: SharedContext = None):
        self.llm_client = llm_client or LLMClient()
        self.shared_context = shared_context
        # Remove execution_history as it's now in shared context
        
        # Pure meta tool architecture - only meta tools registry
        self.meta_tool_registry = ToolRegistry()
        
        print(f"Executor: Initialized with {len(self.meta_tool_registry.get_available_tools())} meta tools")
    
    
    
    def _build_react_system_prompt(self, context_info: Dict[str, Any] = None) -> str:
        """Build ReAct system prompt with meta tools and context information"""
        
        # Get meta tools formatted for prompt
        tools_section = MetaToolManager.get_meta_tools_description()
        
        # Include context information if available
        context_section = ""
        if context_info:
            session_info = context_info.get("session_info", {})
            current_state = context_info.get("current_state", {})
            relevant_history = context_info.get("relevant_history", [])
            
            context_section = f"""
        ## Current Context
        - Session ID: {session_info.get('session_id', 'unknown')}
        - Current Step: {current_state.get('current_step_description', 'unknown')}
        - Step Index: {current_state.get('step_index', 0)}
        - IFC File: {session_info.get('ifc_file_path', 'unknown')}
        
        ## Recent Execution History (for context):
        {json.dumps(relevant_history[:3], indent=2) if relevant_history else "No previous execution history"}
        """
        
        return f"""
        You are an intelligent building compliance checker using the ReAct (Reasoning and Acting) framework.
        {context_section}
        
        ## ReAct Framework Process
        For each task, follow this iterative cycle until completion:

        1. **Thought**: Analyze the current situation and plan your next step
        2. **Action**: Choose which meta tool to use
        3. **Action Input**: Specify the input parameters for the meta tool
        4. **Observation**: [System will provide actual tool results]
        5. **Continue or Finish**: Determine if you need another cycle or task is complete

        ## Available Meta Tools
        {tools_section}

        ## Task Execution Guidelines

        **Meta Tool Selection Strategy:**
        - Use `tool_selection` to find appropriate domain tools for your task
        - Use `tool_creation` when no existing domain tool can handle your requirements
        - Use `tool_execution` to run specific domain tools you've identified
        - Use `tool_registration` to register newly created tools
        - Use `tool_storage` to persistently store tools for future use

        **Error Handling:**
        - If a meta tool fails, analyze the error and try alternative approaches
        - Consider simpler alternatives or different parameters if complex operations fail
        - Always explain your reasoning clearly in your thought process

        **Efficiency Guidelines:**
        - Complete tasks in minimum steps while being thorough
        - Combine related operations when possible through meta tools
        - Be specific about requirements when using tool creation or selection meta tools
        - Focus on systematic approach: search → select/create → execute → store (if new)

        **Task Completion:**
        - Mark the task as final when all required information has been gathered or processed
        - Provide clear summary of accomplishments in final responses
        
        """.format(tools_section=tools_section)
            
    
    def execute_step(self, 
                    step: Dict[str, Any], 
                    ifc_file_path: str,
                    max_iterations: int = 5) -> Dict[str, Any]:
       
        # Get context information from shared context
        context_info = None
        if self.shared_context:
            context_info = self.shared_context.get_context_for_agent("executor")
       
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
                context=context,
                context_info=context_info
            )
            
            # 2. Check if completed first (Pydantic handles validation automatically)
            if react_response.is_final:
                # Record final thinking process
                context["history"].append({
                    "iteration": iteration + 1,
                    "thought": react_response.thought,
                    "action": "completed"
                })
                return self._create_success_result(
                    step_id=step.get("step_id"),
                    result=react_response.action_input or {"message": "Task completed successfully"},
                    history=context["history"],
                    iterations_used=iteration + 1,
                    tool_results=tool_execution_results
                )
            
            # 3. Record thinking process for non-final responses
            context["history"].append({
                "iteration": iteration + 1,
                "thought": react_response.thought,
                "action": react_response.action
            })
            
            # 4. Execute action
            action_result = self._execute_action(
                action_name=react_response.action,
                action_input=react_response.action_input or {},
                context=context
            )
            
            # Save tool execution result if successful
            if action_result.get("success") and "result" in action_result:
                tool_execution_results.append(action_result["result"])
            
            # 5. Update state
            current_state = {
                "observation": self._format_observation(action_result),
                "last_action": react_response.action,
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
                           context: Dict[str, Any],
                           context_info: Dict[str, Any] = None) -> ReActResponse:
        
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
        
        IMPORTANT: 
        - If the task is complete, set is_final=True and omit action/action_input fields
        - Otherwise, provide thought, action (exact tool name), and action_input (tool parameters)
        """
                
        try:
            # Build system prompt with context information
            system_prompt = self._build_react_system_prompt(context_info)
            
            response = self.llm_client.generate_response(
                prompt, 
                system_prompt, 
                response_model=ReActResponse
            )
            return response
        except Exception as e:
            print(f"LLM call failed: {e}")
            raise RuntimeError(f"ReAct LLM call failed: {e}") from e
    
    
    def _execute_action(self, 
                       action_name: str, 
                       action_input: Dict[str, Any],
                       context: Dict[str, Any]) -> Dict[str, Any]:
        
        if action_name == "final_answer":
            return {"success": True, "result": action_input, "is_final": True}
        
        try:
            # Prepare parameters for meta tool
            tool_params = action_input.copy()
            # Add context for meta tools that may need it
            if "ifc_file_path" in context:
                tool_params["execution_context"] = json.dumps({"ifc_file_path": context["ifc_file_path"]})
            
            # Execute meta tool using ToolRegistry native API
            tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
            tool_call = {
                "id": tool_call_id,
                "type": "function",
                "function": {"name": action_name, "arguments": json.dumps(tool_params)}
            }
            
            tool_responses = self.meta_tool_registry.execute_tool_calls([tool_call])
            result = tool_responses.get(tool_call_id)
            
            if result is None:
                return {"success": False, "error": f"No result from meta tool {action_name}", "tool_name": action_name}
            
            # Meta tools return JSON strings - parse them
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    return {
                        "success": parsed_result.get("success", False),
                        "result": parsed_result,
                        "tool_name": action_name,
                        "is_meta_tool": True
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "result": result,
                        "tool_name": action_name,
                        "error": "Failed to parse meta tool JSON response"
                    }
            
            return {
                "success": True,
                "tool_name": action_name,
                "result": result,
                "is_meta_tool": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Meta tool execution failed: {str(e)}",
                "tool_name": action_name,
                "critical_failure": "critical" in str(e).lower()
            }
    
    
    
    
    def _format_observation(self, action_result: Dict[str, Any]) -> str:
        """Format action result as observation description"""
        if action_result.get("success"):
            tool_name = action_result.get("tool_name", "unknown tool")
            result = action_result.get("result", {})
            
            # Generate result summary
            if isinstance(result, dict):
                if "summary" in result:
                    result_summary = result["summary"]
                else:
                    # Extract key information
                    key_info = []
                    for k, v in result.items():
                        if k in ["status", "count", "value", "measurement", "compliant"]:
                            key_info.append(f"{k}={v}")
                    result_summary = ", ".join(key_info) if key_info else str(result)[:100]
            else:
                result_summary = str(result)[:100]
                
            return f"Successfully executed {tool_name}. Result: {result_summary}"
        else:
            error = action_result.get("error", "Unknown error")
            return f"Action failed: {error}"
    
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
        Execute single step using ReAct loop - delegates tool selection to ReAct
        
        Args:
            step: Single step from plan
            ifc_file_path: Path to IFC file
            step_id: Id of step in plan

        Returns:
            Dict: Step execution result with step_status field
        """
        step_description = step.get('description', 'Unknown')
        print(f"Executor: Executing single step {step_id}: {step_description}")
        
        try:
            # Execute with ReAct loop - let LLM decide which meta tools to use
            result = self.execute_step(step, ifc_file_path)
            return self._map_execution_result(result, step_id, "react_execution")
            
        except Exception as e:
            print(f"Executor: Single step execution failed with exception: {e}")
            return {
                "step_status": "failed",
                "failure_reason": "exception", 
                "error_message": str(e),
                "status": "error"
            }
    
    
    
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get execution context from shared context"""
        if self.shared_context:
            return self.shared_context.get_context_for_agent("executor")
        return {}

    def _map_execution_result(self, result: Dict[str, Any], step_id: int, execution_type: str) -> Dict[str, Any]:
        """Map execution result to coordinator-compatible format"""
        mapped_result = result.copy()
        mapped_result["execution_type"] = execution_type
        
        if result.get("status") == "success":
            mapped_result["step_status"] = "success"
            mapped_result["step_result"] = result.get("result", {})
        elif result.get("status") == "timeout":
            mapped_result["step_status"] = "failed"
            mapped_result["failure_reason"] = "timeout"
            mapped_result["error_message"] = result.get("error", "Step execution timeout")
        else:
            mapped_result["step_status"] = "failed" 
            mapped_result["failure_reason"] = "execution_failure"
            mapped_result["error_message"] = result.get("error", "Step execution failed")
        
        return mapped_result
    

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get execution history for compatibility with coordinator
        
        Returns:
            List: Execution history records
        """
        return self.execution_history.copy()

