import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """System configuration class"""
    
    # OpenAI API configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "deepseek-chat")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
    
    # Embedding API configuration (can be same as main API or different)
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", os.getenv("OPENAI_API_KEY"))
    EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", os.getenv("OPENAI_API_BASE"))
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002")

    # Tavily Search API configuration
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # System configuration
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # File upload configuration
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Phoenix tracing configuration
    PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY")
    PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "https://app.phoenix.arize.com/v1/traces")
    PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "ACC")
    PHOENIX_ENABLED = os.getenv("PHOENIX_ENABLED", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate if configuration is complete"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Create necessary directories
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        
        return True 