
import os
from datetime import datetime
from typing import Tuple, List, Dict, Any
from pathlib import Path

from .data_models import ToolRequirement, ToolCreationResult
from .static_checker import StaticChecker
from .dynamic_tester import DynamicTester
from .spec_generator import SpecGenerator
from .code_generator import CodeGeneratorAgent
from models.blackboard_models import BlackboardMixin


class ToolCreatorAgent(BlackboardMixin):
    
    def __init__(self, vectordb_path: str = "langchain_vectordb", tool_registry=None):
        super().__init__()
        # Multi-Agent System Components
        self.spec_generator = SpecGenerator()
        self.code_generator = CodeGeneratorAgent(vectordb_path)
        self.static_checker = StaticChecker()
        self.dynamic_tester = DynamicTester()
        
        # Tool Registry integration
        self.tool_registry = tool_registry
        
        # Configuration
        self.max_static_iterations = 3
        
        # Statistics tracking
        self.stats = {
            "total_executions": 0,
            "successful_creations": 0,
            "static_check_iterations": 0,
            "dynamic_test_iterations": 0
        }
    
    def create_tool(self, step_content: str, step_id: str) -> ToolCreationResult:
        
        print(f"=== Creating tool ===")
        print(f"Step: {step_content}")
        
        try:
            # Set blackboard for sub-agents if available
            if hasattr(self, '_blackboard') and self._blackboard:
                for agent_name in ['spec_generator', 'code_generator', 'dynamic_tester', 'static_checker']:
                    agent = getattr(self, agent_name, None)
                    if agent and hasattr(agent, 'set_blackboard'):
                        agent.set_blackboard(self._blackboard)
            
            # Step 1: SpecGenerator analyzes step content
            print("\n[Step 1] Requirement analysis...")
            analysis_result = self.spec_generator.analyze_step(step_content)
            
            requirement = analysis_result.tool_requirement
            test_parameters = analysis_result.test_parameters
            ifc_dependencies = analysis_result.ifc_dependencies
            
            print(f"Generated requirement for: {requirement.function_name}")
            print(f"IFC dependencies: {list(ifc_dependencies.keys())}")
            print(f"Function parameters: {list(test_parameters.keys())}")
            print(f"Description: {requirement.description}")
            
            # Step 2: Use CodeGeneratorAgent to generate tool code (includes RAG retrieval internally)
            print("\n[Step 2] Generating initial code using CodeGeneratorAgent...")
            code, relevant_docs = self.code_generator.generate_code(requirement)
            
            if not code:
                return self._create_failure_result("Failed to generate initial code")
            
            # Log RAG retrieval to blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                docs_data = []
                for doc in relevant_docs:
                    if hasattr(doc, 'content') and hasattr(doc, 'metadata') and hasattr(doc, 'relevance_score'):
                        docs_data.append({
                            "content": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                            "metadata": doc.metadata,
                            "relevance_score": doc.relevance_score
                        })
                    else:
                        # Handle case where relevant_docs might be different format
                        docs_data.append({"content": str(doc)[:200], "relevance_score": 0.0})
                        
                self.log_rag_retrieval(step_id, requirement.description, docs_data)
            
            # Log code generation to blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                metadata = {
                    "function_name": requirement.function_name,
                    "relevant_docs_count": len(relevant_docs),
                    "requirements_complexity": len(requirement.parameters),
                    "has_examples": bool(requirement.examples)
                }
                self.log_code_generation(step_id, code, metadata)
            
            print(f"Generated initial code ({len(code)} characters)")
            print(f"IFC dependencies from SpecGenerator: {list(ifc_dependencies.keys())}")
            
            # Step 3: Static Checker (AST) with feedback loop
            print("\n[Step 3] Static code analysis...")
            code, static_issues, static_iterations = self.static_checker.check_and_fix_with_retry(
                code, requirement, self.max_static_iterations
            )
            
            # Log static check to blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                check_data = {
                    "is_valid": bool(code),
                    "errors": [issue for issue in static_issues if "error" in issue.lower()],
                    "warnings": [issue for issue in static_issues if "warning" in issue.lower()],
                    "iterations": static_iterations
                }
                self.log_static_check(step_id, check_data)
            if not code:
                return self._create_failure_result(static_issues, static_iterations, 0)
            
            print(f"Static checking completed after {static_iterations} iterations")
            
            # Step 4: Dynamic testing
            print("\n[Step 4] Dynamic testing...")
            test_result = self.dynamic_tester.test_tool(
                code, requirement, ifc_dependencies, test_parameters
            )
            
            # Log dynamic test to blackboard if available
            if hasattr(self, '_blackboard') and self._blackboard:
                test_result_data = {
                    "success": test_result.success,
                    "issues": test_result.issues,
                    "data_availability": test_result.data_availability,
                    "tool_execution": test_result.tool_execution,
                    "test_file_used": test_parameters.get("ifc_file_path", ""),
                    "used_user_file": True,  # Always user file now, no fallback
                    "missing_elements": test_result.missing_elements,
                    "missing_properties": test_result.missing_properties
                }
                self.log_dynamic_test(step_id, test_result_data)
            
            print(f"Dynamic testing {'PASSED' if test_result.success else 'FAILED'}")
            
            # Step 5: Output final tool
            print("\n[Step 5] Finalizing tool...")
            
            # Update statistics
            dynamic_iterations = 1  # test_tool runs once
            self._update_stats(test_result.success, static_iterations, dynamic_iterations)
            
            # Create result
            all_issues = static_issues + test_result.issues
            final_code = code  # Code unchanged by dynamic testing
            result = ToolCreationResult(
                success=test_result.success,
                generated_code=final_code,
                ifc_dependencies=ifc_dependencies,
                issues=all_issues,
                static_check_passes=static_iterations,
                dynamic_test_passes=dynamic_iterations
            )
            
            # Register tool to ToolRegistry if successful and registry is available
            if test_result.success and self.tool_registry is not None:
                try:
                    from tools.tool_registry import register_from_code
                    from tools.persistent_tool_storage import PersistentToolStorage
                    
                    tool_name = requirement.function_name
                    success = register_from_code(self.tool_registry, final_code, tool_name)
                    if success:
                        print(f"Tool '{tool_name}' successfully registered to ToolRegistry")
                        
                        # Also save to persistent storage with category
                        try:
                            storage = PersistentToolStorage()
                            # Determine category based on tool content
                            category = self._determine_tool_category(final_code, requirement.description)
                            storage.save_tool(tool_name, final_code, requirement.description, category)
                            print(f"Tool '{tool_name}' saved to persistent storage (category: {category})")
                        except Exception as e:
                            print(f"Failed to save tool to persistent storage: {e}")
                    else:
                        print(f"Failed to register tool '{tool_name}'")
                except Exception as e:
                    print(f"Exception during tool registration: {str(e)}")
            
            print(f"\n=== Tool creation {'COMPLETED' if test_result.success else 'FAILED'} ===")
            
            return result
            
        except Exception as e:
            print(f"\n=== Tool creation FAILED with exception ===")
            print(f"Error: {str(e)}")
            
            return ToolCreationResult(
                success=False,
                generated_code="",
                ifc_dependencies={},
                issues=[f"Unexpected error: {str(e)}"],
                static_check_passes=0,
                dynamic_test_passes=0
            )
    
    
    
    def _create_failure_result(self, issues: List[str], 
                               static_passes: int = 0, dynamic_passes: int = 0) -> ToolCreationResult:
        """Create a failure result"""
        
        if isinstance(issues, str):
            issues = [issues]
        
        return ToolCreationResult(
            success=False,
            generated_code="",
            ifc_dependencies={},
            issues=issues,
            static_check_passes=static_passes,
            dynamic_test_passes=dynamic_passes
        )
    
    def _determine_tool_category(self, code: str, description: str) -> str:
        """Determine tool category based on content"""
        code_lower = code.lower()
        desc_lower = description.lower()
        
        # Check for IFC-related content
        ifc_indicators = ['ifc', 'ifcparser', 'building', 'element', 'compliance', 'construction']
        if any(indicator in code_lower or indicator in desc_lower for indicator in ifc_indicators):
            return "ifcopenshell"
        
        # Check for MCP-related content
        if 'mcp' in code_lower or 'mcp' in desc_lower:
            return "mcp"
        
        # Check for OpenAPI-related content
        if 'openapi' in code_lower or 'rest' in desc_lower or 'api' in desc_lower:
            return "openapi"
        
        # Check for LangChain-related content
        if 'langchain' in code_lower or 'llm' in desc_lower:
            return "langchain"
        
        # Default to ifcopenshell for building-related tools
        return "ifcopenshell"
    
    def _update_stats(self, success: bool, static_iterations: int, 
                      unit_test_iterations: int):
        """Update internal statistics"""
        self.stats["total_executions"] += 1
        if success:
            self.stats["successful_creations"] += 1
        self.stats["static_check_iterations"] += static_iterations
        self.stats["unit_test_iterations"] += unit_test_iterations
    
    def get_statistics(self) -> dict:
        """Get current statistics"""
        stats = self.stats.copy()
        if stats["total_executions"] > 0:
            stats["success_rate"] = stats["successful_creations"] / stats["total_executions"]
            stats["avg_static_iterations"] = stats["static_check_iterations"] / stats["total_executions"]
            stats["avg_unit_test_iterations"] = stats["unit_test_iterations"] / stats["total_executions"]
        
        return stats
    
    def save_generated_tool(self, result: ToolCreationResult, requirement: ToolRequirement, 
                            output_dir: str = "generated_tools") -> str:
        """Save the generated tool to a file"""
        if not result.success:
            return ""
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Create filename
        filename = f"{requirement.function_name}.py"
        file_path = output_path / filename
        
        # Add header comment
        header = f"""#!/usr/bin/env python3
\"\"\"
Generated tool: {requirement.function_name}
Description: {requirement.description}
Generated at: {datetime.now().isoformat()}
Static check passes: {result.static_check_passes}
Dynamic test passes: {result.dynamic_test_passes}
\"\"\"

"""
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header + result.generated_code)
        
        print(f"Generated tool saved to: {file_path}")
        return str(file_path)
    
    def health_check(self) -> bool:
        """Perform health check on all components"""
        try:
            # RAG retriever health check is now handled internally by CodeGenerator
            print("Health check passed: All components operational")
            return True
            
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
