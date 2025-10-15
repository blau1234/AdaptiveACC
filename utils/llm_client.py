import openai
from config import Config
import instructor
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """LLM client for interacting with OpenAI API with Instructor integration"""
    
    def __init__(self):
        """Initialize LLM client with both raw and instructor clients"""
        client_kwargs = {"api_key": Config.OPENAI_API_KEY}
        if Config.OPENAI_API_BASE:
            client_kwargs["base_url"] = Config.OPENAI_API_BASE

        # Create raw OpenAI client for plain text responses
        self.raw_client = openai.OpenAI(**client_kwargs)

        # Create instructor-wrapped client for structured output
        self.instructor_client = instructor.from_openai(openai.OpenAI(**client_kwargs))

        self.model_name = Config.OPENAI_MODEL_NAME
    
    def generate_response(self,
                         prompt: str,
                         system_prompt: str = None,
                         response_model: Optional[Type[T]] = None,
                         max_retries: int = 3) -> str | T:
       
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if response_model:
            # Use Instructor client for structured output
            try:
                response = self.instructor_client.chat.completions.create(
                    model=self.model_name,
                    response_model=response_model,
                    messages=messages,
                    temperature=0,
                    max_tokens=8000,
                    max_retries=max_retries
                )
                return response
            except Exception as e:
                print(f"Instructor API call failed: {e}")
                return None  # Return None instead of error string
        else:
            # Use raw OpenAI client for plain text responses
            try:
                for attempt in range(max_retries):
                    try:
                        response = self.raw_client.chat.completions.create(
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

    def generate_response_with_tools(self,
                                   prompt: str,
                                   system_prompt: str,
                                   tools: list) -> dict:
        
        messages = [] 
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        call_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4000,
            "timeout": 30,
            "tools": tools,
            "tool_choice": "auto"
        }

        # Direct call using raw_client
        response = self.raw_client.chat.completions.create(**call_kwargs)

        # Return structured response with original tool_calls preserved
        result = {
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls or []  # Keep original objects
        }

        return result


