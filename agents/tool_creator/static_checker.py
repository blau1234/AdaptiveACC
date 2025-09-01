import ast
import subprocess
import tempfile
import os
from typing import List, Tuple
from .data_models import StaticCheckResult, ToolRequirement
from models.blackboard_models import BlackboardMixin
from utils.llm_client import LLMClient


class StaticChecker(BlackboardMixin):
    
    def __init__(self, max_line_length: int = 100, max_complexity: int = 10, 
                 enable_security_checks: bool = True):
        super().__init__()
        self.enable_security_checks = enable_security_checks
        self.llm_client = LLMClient()
        
        # flake8 configuration
        self.flake8_config = [
            f'--max-line-length={max_line_length}',
            f'--max-complexity={max_complexity}',
            '--ignore=E203,W503',  # Ignore some common issues
            '--extend-ignore=E501'  # Ignore line too long for generated code
        ]
    
    def check_code(self, code: str) -> StaticCheckResult:
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Run flake8 checks
            flake8_errors, flake8_warnings = self._run_flake8_check(code)
            errors.extend(flake8_errors)
            warnings.extend(flake8_warnings)
            
            # Parse the code into AST for custom checks
            tree = ast.parse(code)
            
            # Perform all custom checks in a single AST walk
            self._perform_ast_checks(tree, errors, warnings, suggestions)
            
            is_valid = len(errors) == 0
            
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            is_valid = False
        except Exception as e:
            errors.append(f"Analysis error: {e}")
            is_valid = False
        
        return StaticCheckResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _run_flake8_check(self, code: str) -> Tuple[List[str], List[str]]:
        """Run flake8 on the provided code and return errors and warnings"""
        errors = []
        warnings = []
        
        try:
            # Create a temporary file with the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            # Run flake8 on the temporary file
            cmd = ['flake8'] + self.flake8_config + [temp_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if result.returncode != 0:
                # Parse flake8 output
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # flake8 format: filename:line:column: code message
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            error_code = parts[3].strip().split()[0]
                            message = parts[3].strip()
                            
                            # Categorize by error code
                            if error_code.startswith('E9') or error_code.startswith('F'):
                                # Syntax errors and undefined names
                                errors.append(f"Line {parts[1]}: {message}")
                            else:
                                # Style and other warnings
                                warnings.append(f"Line {parts[1]}: {message}")
                                
        except FileNotFoundError:
            warnings.append("flake8 not installed - skipping style checks")
        except Exception as e:
            warnings.append(f"flake8 check failed: {e}")
        
        return errors, warnings
    
    def _perform_ast_checks(self, tree: ast.AST, errors: List[str], warnings: List[str], suggestions: List[str]):
        """Perform all custom checks in a single AST walk for better performance"""
        try_blocks = []
        file_operations = []
        dangerous_functions = set()
        
        # Single walk through the AST
        for node in ast.walk(tree):
            # Function quality checks
            if isinstance(node, ast.FunctionDef):
                # Check for missing docstring
                if not ast.get_docstring(node):
                    warnings.append(f"Function '{node.name}' missing docstring")
                
                # Check for parameter validation
                if not self._has_parameter_validation(node):
                    suggestions.append(f"Consider adding parameter validation in function '{node.name}'")
                
                # Check for overly long functions
                if len(node.body) > 20:
                    suggestions.append(f"Function '{node.name}' is quite long ({len(node.body)} statements), consider breaking it up")
            
            # Error handling checks
            elif isinstance(node, ast.Try):
                try_blocks.append(node)
                
                # Check for bare except clauses
                for handler in node.handlers:
                    if handler.type is None:
                        warnings.append("Avoid bare except clauses, specify exception types")
                    
                    # Check for empty except blocks
                    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                        warnings.append("Empty except block found, consider proper error handling")
            
            # Function call checks (security and file operations)
            elif isinstance(node, ast.Call):
                # File operations
                if isinstance(node.func, ast.Name) and node.func.id == 'open':
                    file_operations.append(node)
                elif isinstance(node.func, ast.Attribute) and node.func.attr in ['read', 'write', 'close']:
                    file_operations.append(node)
                
                # Security checks (if enabled)
                if self.enable_security_checks:
                    # Check for dangerous functions
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec']:
                            errors.append(f"Dangerous function '{node.func.id}' detected, avoid dynamic code execution")
                            dangerous_functions.add(node.func.id)
                        elif node.func.id == 'input' and 'eval' in dangerous_functions:
                            warnings.append("Using input() with eval() can be dangerous")
                    
                    # Check for os.system and subprocess calls
                    elif isinstance(node.func, ast.Attribute):
                        if (isinstance(node.func.value, ast.Name) and 
                            node.func.value.id == 'os' and 
                            node.func.attr == 'system'):
                            warnings.append("os.system call detected, consider using subprocess instead")
                            
                        # Check for shell=True in subprocess calls
                        elif (isinstance(node.func.value, ast.Name) and 
                              node.func.value.id == 'subprocess'):
                            for keyword in node.keywords:
                                if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                                    warnings.append("subprocess with shell=True can be dangerous, validate inputs carefully")
        
        # Post-walk analysis
        # Suggest error handling for file operations if no try blocks
        if file_operations and not try_blocks:
            suggestions.append("Consider adding error handling for file operations")
    
        
    def _has_parameter_validation(self, func_node: ast.FunctionDef) -> bool:
        """Check if function has parameter validation"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.If):
                # Look for parameter checks
                for child in ast.walk(node.test):
                    if isinstance(child, ast.Name) and child.id in [arg.arg for arg in func_node.args.args]:
                        return True
        return False

    def fix_issues(self, code: str, check_result: StaticCheckResult, requirement: ToolRequirement) -> str:
        """Fix static issues using LLM"""
        if check_result.is_valid:
            return code  # No issues to fix
            
        issues_text = "\n".join(check_result.errors + check_result.warnings[:5])  # Limit issues
        
        prompt = f"""
        Fix the following issues in the Python code while maintaining the original functionality:
        
        ISSUES TO FIX:
        {issues_text}
        
        CURRENT CODE:
        {code}
        
        REQUIREMENTS:
        - Maintain the original function signature and behavior
        - Fix all syntax and structural issues
        - Improve code quality and follow best practices
        - Keep all existing functionality intact
        - Comments in English only
        
        Return the corrected code only, no explanation.
        """
        
        try:
            # Use longer timeout for code fixing
            fixed_code = self.llm_client.generate_response(
                prompt, 
                timeout=90,  # 1.5 minutes for code fixing
                max_tokens=3000
            )
            fixed_code = self._clean_generated_code(fixed_code)
            
            return fixed_code
            
        except Exception as e:
            print(f"Error fixing static issues: {e}")
            return ""

    def _clean_generated_code(self, code: str) -> str:
        """Clean generated code by removing markdown formatting and extra whitespace"""
        if not code:
            return ""
        
        # Remove markdown code blocks
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        # Remove extra whitespace but preserve indentation
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            # Keep the line as is, just strip trailing whitespace
            cleaned_lines.append(line.rstrip())
        
        # Remove leading/trailing empty lines
        while cleaned_lines and not cleaned_lines[0]:
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)

    def check_and_fix_with_retry(self, code: str, requirement: ToolRequirement, 
                                max_iterations: int = 3) -> Tuple[str, List[str], int]:
        """
        Complete static checking with automatic fixing and retry loop.
        This method replaces the _static_checking_loop from ToolCreator.
        
        Returns:
            - Fixed code (empty string if failed)
            - List of issues encountered
            - Number of iterations performed
        """
        issues = []
        iteration = 0
        
        print("  Starting static analysis with auto-fix loop...")
        
        for iteration in range(1, max_iterations + 1):
            print(f"  Static check iteration {iteration}/{max_iterations}")
            
            check_result = self.check_code(code)
            
            # Static check completed - external logging handled by ToolCreator
            
            if check_result.is_valid:
                print(f"  Static analysis PASSED after {iteration} iterations")
                return code, issues, iteration
            
            # Collect issues
            current_issues = check_result.errors + check_result.warnings
            issues.extend(current_issues)
            
            print(f"  Found {len(current_issues)} issues")
            for issue in current_issues[:3]:  # Show first 3 issues
                print(f"    - {issue}")
            
            # Try to fix issues if not the last iteration
            if iteration < max_iterations:
                print(f"  Attempting to fix issues...")
                fixed_code = self.fix_issues(code, check_result, requirement)
                if fixed_code and fixed_code != code:
                    code = fixed_code
                    print(f"  Code updated, retrying analysis...")
                else:
                    print(f"  Could not fix issues automatically")
                    break
        
        print(f"  Static analysis FAILED after {iteration} iterations")
        return "", issues, iteration
