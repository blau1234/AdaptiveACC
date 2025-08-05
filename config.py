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
    
    # System configuration
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # File upload configuration
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    
    @classmethod
    def validate(cls):
        """Validate if configuration is complete"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Create necessary directories
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        
        return True 