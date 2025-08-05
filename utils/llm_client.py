import openai
from config import Config

class LLMClient:
    """LLM client for interacting with OpenAI API"""
    
    def __init__(self):
        """Initialize LLM client"""
        client_kwargs = {"api_key": Config.OPENAI_API_KEY}
        if Config.OPENAI_API_BASE:
            client_kwargs["base_url"] = Config.OPENAI_API_BASE
        self.client = openai.OpenAI(**client_kwargs)
        self.model_name = Config.OPENAI_MODEL_NAME
    
    def generate_response(self, prompt: str, system_prompt: str = None, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
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

    
