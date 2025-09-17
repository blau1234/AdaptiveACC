"""
Phoenix tracing configuration for building compliance check system
"""

import os
from typing import Optional
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.trace import get_tracer_provider

from config import Config


def init_tracing() -> Optional[object]:
    """
    Initialize Phoenix tracing with configuration from Config class
        
    Returns:
        TracerProvider instance or None if initialization fails
    """
    try:
        # Get configuration from Config class
        api_key = Config.PHOENIX_API_KEY
        endpoint = Config.PHOENIX_ENDPOINT
        project_name = Config.PHOENIX_PROJECT_NAME
        
        # Configure Phoenix client headers if API key is provided
        if api_key:
            os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={api_key}"
            print("Phoenix API key configured successfully")
        else:
            print("Warning: No API key provided - may not be able to connect to Phoenix cloud")

        # Register Phoenix tracer provider
        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            auto_instrument=True  # Enable automatic instrumentation
        )
        # Instrument OpenAI SDK for tracing
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        
        print(f"Phoenix tracing initialized successfully for project: {project_name}")
        return tracer_provider
        
    except Exception as e:
        print(f"Phoenix tracing initialization failed: {e}")
        print("Continuing without Phoenix tracing...")
        return None


def get_tracer(name: str = __name__):
    """Get tracer instance"""
    try:
        return get_tracer_provider().get_tracer(name)
    except Exception:
        # Return a no-op tracer if initialization failed
        return None