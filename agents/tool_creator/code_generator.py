import json
from typing import List, Tuple

from utils.llm_client import LLMClient
from .data_models import ToolRequirement, RetrievedDocument
from .rag_retriever import RAGRetriever
from models.blackboard_models import BlackboardMixin


class CodeGeneratorAgent(BlackboardMixin):
    
    def __init__(self, vectordb_path: str = "langchain_vectordb"):
        super().__init__()
        self.llm_client = LLMClient()
        self.rag_retriever = RAGRetriever(vectordb_path)
    
    def generate_code(self, requirement: ToolRequirement) -> Tuple[str, List[RetrievedDocument]]:
       
        try:
            print(f"CodeGenerator: Generating code for {requirement.function_name}")
            
            # Step 1: Retrieve relevant documentation
            print(f"CodeGenerator: Retrieving relevant documentation...")
            relevant_docs = self.rag_retriever.retrieve_relevant_docs(
                requirement.description, k=5
            )
            print(f"CodeGenerator: Retrieved {len(relevant_docs)} relevant documents")
            
            
            # Step 2: Build context for code generation
            context = self._build_generation_context(requirement, relevant_docs)
            
            # Step 3: Generate code using LLM
            code = self._llm_generate_code(context, requirement)
            
            # Step 4: Clean up generated code
            code = self._clean_generated_code(code)
            
            
            print(f"CodeGenerator: Generated {len(code)} characters of code")
            return code, relevant_docs
            
        except Exception as e:
            print(f"CodeGenerator: Code generation failed - {e}")
            return "", []
    
    def _build_generation_context(self, requirement: ToolRequirement, 
                                relevant_docs: List[RetrievedDocument]) -> str:
        
        context = "=== CODE GENERATION CONTEXT ===\n\n"
        
        # Tool requirement details
        context += f"TOOL REQUIREMENT:\n"
        context += f"Function name: {requirement.function_name}\n"
        context += f"Description: {requirement.description}\n"
        context += f"Parameters: {requirement.parameters}\n"
        context += f"Return type: {requirement.return_type}\n\n"
        
        # Examples if provided
        if requirement.examples:
            context += "USAGE EXAMPLES:\n"
            for example in requirement.examples:
                context += f"- {example}\n"
            context += "\n"
        
        # Retrieved documentation
        if relevant_docs:
            context += "RELEVANT DOCUMENTATION:\n"
            for i, doc in enumerate(relevant_docs, 1):
                context += f"Document {i} (relevance: {doc.relevance_score:.3f}):\n"
                context += f"{doc.content[:500]}...\n\n"
        else:
            context += "RELEVANT DOCUMENTATION: None provided\n\n"
        
        return context
    
    def _llm_generate_code(self, context: str, requirement: ToolRequirement) -> str:
        
        prompt = f"""
        You are an expert Python developer specializing in IFC file processing.
        Generate a complete, production-ready Python function based on the requirements and context.
        
        {context}
        
        CODE GENERATION REQUIREMENTS:
        - Function must be complete and runnable
        - Include proper error handling with try-catch blocks
        - Use appropriate APIs based on the documentation provided
        - Include comprehensive type hints for all parameters and return values
        - Include detailed docstring with parameter descriptions and examples
        - Follow Python best practices and PEP 8 style guidelines
        - Handle edge cases and validate input parameters
        - All comments and docstrings must be in English
        - Include proper imports at the top
        - Return meaningful data structures (usually Dict[str, Any])
        
        IMPORTANT: Return ONLY the Python code, no JSON wrapper, no explanations.
        The code should be ready to execute as-is.
        
        Example format:
        ```python
        import ifcopenshell
        from typing import Dict, Any
        
        def {requirement.function_name}({', '.join([p['name'] + ': ' + p['type'] for p in requirement.parameters])}) -> {requirement.return_type}:
            \"\"\"
            {requirement.description}
            
            Args:
                param1: Description
                param2: Description
                
            Returns:
                Result dictionary with analysis data
            \"\"\"
            try:
                # Implementation here
                return {{"result": "success", "data": []}}
            except Exception as e:
                raise RuntimeError(f"Error in {requirement.function_name}: {{e}}")
        ```
        """
        
        try:
            code = self.llm_client.generate_response(
                prompt,
                timeout=120,  # 2 minutes for code generation
                max_tokens=3000
            )
            return code
            
        except Exception as e:
            print(f"LLM code generation failed: {e}")
            return ""
    
    def _clean_generated_code(self, code: str) -> str:
        """Clean up generated code by removing markdown formatting"""
        if not code:
            return ""
        
        # Remove markdown code blocks
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
        elif "```" in code:
            parts = code.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        return code
    
    

