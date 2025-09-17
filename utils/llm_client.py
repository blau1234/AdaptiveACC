import openai
from config import Config
import instructor
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """LLM client for interacting with OpenAI API with Instructor integration"""
    
    def __init__(self):
        """Initialize LLM client with Instructor"""
        client_kwargs = {"api_key": Config.OPENAI_API_KEY}
        if Config.OPENAI_API_BASE:
            client_kwargs["base_url"] = Config.OPENAI_API_BASE
        
        # Create OpenAI client and wrap with Instructor
        openai_client = openai.OpenAI(**client_kwargs)
        self.client = instructor.from_openai(openai_client)
        self.model_name = Config.OPENAI_MODEL_NAME
    
    def generate_response(self, 
                         prompt: str, 
                         system_prompt: str = None, 
                         response_model: Optional[Type[T]] = None,
                         max_retries: int = 3) -> str | T:
        """
        Generate response with optional structured output
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            response_model: Optional Pydantic model for structured output
            max_retries: Maximum retry attempts
            
        Returns:
            str: Plain text response if no response_model
            T: Structured response if response_model is provided
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if response_model:
            # Use Instructor for structured output
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_model=response_model,
                messages=messages,
                temperature=0,
                max_tokens=2000,
                max_retries=max_retries
            )
            return response
        else:
            try:
                # Fallback to regular OpenAI client for plain text
                for attempt in range(max_retries):
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            temperature=0,
                            max_tokens=2000,
                            timeout=30
                        )
                        
                        content = response.choices[0].message.content
                        if content is None or content.strip() == "":
                            raise ValueError("Empty response from LLM")
                        
                        return content
                        
                    except Exception as e:
                        print(f"LLM API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                        if attempt == max_retries - 1:
                            return f"API call failed after {max_retries} attempts: {e}"
                        continue
                
                return "API call failed: Maximum retries exceeded"
                
            except Exception as e:
                print(f"Plain text API call failed: {e}")
                return f"API call failed: {e}"

    
