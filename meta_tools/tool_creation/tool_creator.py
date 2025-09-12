
from typing import Tuple, List, Dict, Any
from pathlib import Path
from data_models.shared_models import ToolCreationResult
from .static_checker import StaticChecker
from .spec_generator import SpecGenerator
from .code_generator import CodeGenerator


class ToolCreatorAgent:

    def __init__(self, vectordb_path: str = "vectordb/docs", tool_vector_db=None):

        # Multi-Agent System Components
        self.spec_generator = SpecGenerator()
        self.code_generator = CodeGenerator(vectordb_path)
        self.static_checker = StaticChecker()
        
        self.tool_vector_db = tool_vector_db  
        self.max_static_iterations = 3
        
    
    # Executor Interface
    def tool_creation(self, step_content: str, step_id: str) -> ToolCreationResult:

        print(f"=== Creating tool ===")
        
        try:
            
            # Step 1: SpecGenerator analyzes step content
            print("\n[Step 1] Requirement analysis...")

            analysis_result = self.spec_generator.analyze_step(step_content)
            requirement = analysis_result.tool_requirement
            
            print(f"Generated requirement for: {requirement.function_name}")
            print(f"Description: {requirement.description}")

            # Step 2: Use CodeGeneratorAgent to generate tool code 
            print("\n[Step 2] Generating initial code using CodeGenerator...")
            code = self.code_generator.generate_code(requirement)
            
            if not code:
                return self._create_failure_result("Failed to generate initial code")
            
            print(f"Generated initial code ({len(code)} characters)")
            
            # Step 3: Static Checker (AST) with feedback loop
            print("\n[Step 3] Static code analysis...")
            code, static_issues, static_iterations = self.static_checker.check_and_fix_with_retry(
                code, requirement, self.max_static_iterations
            )
            
            if not code:
                return self._create_failure_result(static_issues, static_iterations)
            
            print(f"Static checking completed after {static_iterations} iterations")
            

            # Step 5: Output final tool
            print("\n[Step 5] Finalizing tool...")
            
            # Create result
            all_issues = static_issues
            final_code = code
            result = ToolCreationResult(
                success=True,
                generated_code=final_code,
                ifc_dependencies={},
                issues=all_issues,
                static_check_passes=static_iterations
            )
            
            return result
            
        except Exception as e:
            print(f"\n=== Tool creation FAILED with exception ===")
            print(f"Error: {str(e)}")
            
            return ToolCreationResult(
                success=False,
                generated_code="",
                ifc_dependencies={},
                issues=[f"Unexpected error: {str(e)}"],
                static_check_passes=0
            )
    
    
    def _create_failure_result(self, issues: List[str], 
                               static_passes: int = 0) -> ToolCreationResult:
        """Create a failure result"""
        
        if isinstance(issues, str):
            issues = [issues]
        
        return ToolCreationResult(
            success=False,
            generated_code="",
            ifc_dependencies={},
            issues=issues,
            static_check_passes=static_passes
        )
       
        

    