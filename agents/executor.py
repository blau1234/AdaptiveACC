import json
from typing import Dict, List, Any
import uuid
from utils.llm_client import LLMClient
from meta_tools.meta_tool_registry import MetaToolRegistry
from meta_tools.tool_selection import ToolSelection
from meta_tools.tool_execution import ToolExecution
from meta_tools.tool_storage import ToolStorage
from meta_tools.tool_creation_and_fix.tool_fix import ToolFix
from meta_tools.tool_creation_and_fix.tool_creation import ToolCreation
from models.common_models import ReActResponse, ExecutionState, StepExecutionResult, MetaToolResult
from models.shared_context import SharedContext


class Executor:
    """Executor agent implementing ReAct framework with local state management"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()
        self.meta_tool_registry = MetaToolRegistry.get_instance()

        # Register meta tools
        self._register_required_tools()
        print(f"Executor: Initialized with {len(self.meta_tool_registry.get_available_tools())} meta tools")

    def _register_required_tools(self):
        tools_to_register = [
            ToolSelection().select_best_tool,
            ToolCreation().tool_creation,
            ToolExecution().tool_execution,
            ToolStorage().tool_storage,
            ToolFix().tool_fix
        ]

        for tool_func in tools_to_register:
            try:
                self.meta_tool_registry.register(tool_func)
            except Exception as e:
                print(f"Failed to register meta tool {tool_func.__name__}: {e}")


    # === Main Interface ===

    def execute_step(self, max_iterations: int = 5) -> StepExecutionResult:
        """Execute a single step using ReAct framework with local state management"""

        # 1. Initialize execution state
        execution_state = self._initialize_execution_state()

        # 2. Run ReAct loop
        for iteration in range(max_iterations):
            print(f"\n=== ReAct Iteration {iteration + 1}/{max_iterations} ===")

            result = self._run_react_iteration(execution_state, iteration)
            if result:  # Task completed or failed
                return result

        # 3. Handle timeout
        return self._create_result("timeout", execution_state,
                                   error=f"Exceeded maximum iterations ({max_iterations})")

    # === Core ReAct Logic ===

    def _initialize_execution_state(self) -> ExecutionState:
        """Initialize execution state from SharedContext"""
        step_index = self.shared_context.current_task.get("step_index")
        step = self.shared_context.current_task.get("step")

        print(f"Executor: Executing step {step_index}: {step['description']}")

        return ExecutionState(
            step=step,
            step_index=step_index,
            last_observation=f"Starting task: {step['description']}"
        )


    def _run_react_iteration(self, execution_state: ExecutionState, iteration: int) -> StepExecutionResult | None:
        """Run a single ReAct iteration. Returns result if completed/failed, None if should continue"""

        # 1. Get LLM's thought and action plan (with previous action result for observation)
        previous_action_result = getattr(execution_state, 'last_action_result', None) if iteration > 0 else None
        react_response = self._get_react_response(execution_state, iteration, previous_action_result)

        # 2. Record thinking process and observation
        action_name = "completed" if react_response.is_final else react_response.action
        execution_state.add_iteration(iteration + 1, react_response.thought, action_name)

        # Update observation if provided by LLM
        if react_response.observation:
            execution_state.update_observation(react_response.observation)

        # 3. Handle completion
        if react_response.is_final:
            final_result = react_response.action_input or {"message": "Task completed successfully"}
            execution_state.add_tool_result(final_result)
            return self._create_result("success", execution_state, iterations_used=iteration + 1)

        # 4. Execute action and store result for next iteration
        action_result: MetaToolResult = self._execute_action(react_response.action, react_response.action_input or {}, execution_state)
        execution_state.add_tool_result(action_result.result)

        # Store action result for next iteration's observation generation (convert to dict for serialization)
        execution_state.last_action_result = action_result.model_dump()

        # 5. Check for critical failure
        if not action_result.success:
            return self._create_result("failed", execution_state, error=action_result.error or "Action execution failed")

        return None  # Continue iterations

    def _get_react_response(self, execution_state: ExecutionState, iteration: int, previous_action_result: Dict[str, Any] = None) -> ReActResponse:
        """Get LLM's ReAct response for current iteration"""

        recent_trace = self.shared_context.process_trace[-3:]
        context_section = f"""## Recent Execution History {json.dumps(recent_trace, indent=2)}"""
        tools_section = self.meta_tools_description()

        system_prompt = f"""
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

        **Observation Generation:**
        - After each action execution, analyze the result and generate an observation
        - Focus on what was accomplished, what data was gathered, and its significance for the task
        - Connect the observation to the overall task objective
        - Be specific about success/failure and next steps implications

        **Task Completion:**
        - Set is_final=True when all required information has been gathered or processed
        - When not final: provide thought, action (exact tool name), and action_input (tool parameters)
        - When action result is available: also provide observation analyzing the result
        - In final responses: provide clear summary of accomplishments
        """

        # Include previous action result for observation generation
        action_result_section = ""
        if previous_action_result:
            action_result_section = f"""
        Previous Action Result: {json.dumps(previous_action_result, indent=2)}
        """

        prompt = f"""
        Current Task: {execution_state.step['description']}
        Task Type: {execution_state.step['task_type']}
        Expected Outcome: {execution_state.step['expected_output']}
        Current Observation: {execution_state.last_observation}
        Iteration: {iteration + 1}/5
        {action_result_section}
        Based on the current situation, what should be the next action?
        Remember to think step by step and choose the most appropriate tool from the available tools.
        """

        try:
            response = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=ReActResponse
            )
            return response
        except Exception as e:
            print(f"LLM call failed: {e}")
            raise RuntimeError(f"ReAct LLM call failed: {e}") from e


    def _execute_action(self, action_name: str, action_input: Dict[str, Any]) -> MetaToolResult:
        """Execute the selected meta tool"""

        try:
            # Prepare parameters for meta tool
            tool_params = action_input.copy()

            # Special handling for tools that get context from SharedContext
            if action_name == "select_best_tool":
                # select_best_tool doesn't need any parameters - it gets everything from SharedContext
                tool_params = {}
            else:
                # Add execution context for other meta tools
                ifc_file_path = self.shared_context.session_info.get("ifc_file_path", "")
                tool_params["execution_context"] = json.dumps({"ifc_file_path": ifc_file_path})

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
                return MetaToolResult(
                    success=False,
                    tool_name=action_name,
                    error=f"No result from meta tool {action_name}"
                )

            # Return MetaToolResult directly
            if isinstance(result, MetaToolResult):
                return result

        except Exception as e:
            return MetaToolResult(
                success=False,
                tool_name=action_name,
                error=f"Meta tool execution failed: {str(e)}"
            )

    # === Result Handling ===

    def _create_result(self, status: str, execution_state: ExecutionState, **kwargs) -> StepExecutionResult:
        """Unified result creation that returns typed result format"""

        return StepExecutionResult(
            status=status,
            step_index=execution_state.step_index,
            execution_history=execution_state.history,
            iterations_used=kwargs.get("iterations_used"),
            tool_results=execution_state.tool_results,
            error=kwargs.get("error")
        )


    # === Utility Methods ===

    @staticmethod
    def meta_tools_description() -> str:
        """Get meta tools description for ReAct system prompt"""
        return """Available meta tools:

        ### tool_selection
        - **Description**: Search and select the best domain tool for a given task using semantic search and LLM reasoning
        - **Parameters**:
        - step_description (string) (required): Clear description of the task or step that needs a domain tool
        - execution_context (string) (optional): JSON context containing execution details like ifc_file_path

        ### tool_creation
        - **Description**: Create a new domain tool when no existing tool can handle the current task
        - **Parameters**:
        - step_description (string) (required): Detailed description of what the new tool should accomplish
        - step_id (string) (optional): Identifier for the step, defaults to "auto_generated"

        ### tool_execution
        - **Description**: Execute a domain tool with specified execution mode
        - **Parameters**:
        - tool_name (string) (required): Name of the domain tool to execute
        - parameters (string) (required): JSON string of all parameters required by the tool
        - execution_mode (string) (optional): "safe" for existing tools (default), "sandbox" for newly created tools


        ### tool_storage
        - **Description**: Store a validated tool from SharedContext for future use with filesystem and vector database persistence
        - **Parameters**:
        - tool_name (string) (required): Name of the tool to store from recent creation/fix results

        """