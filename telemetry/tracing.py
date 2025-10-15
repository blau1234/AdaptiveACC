
import os
import functools
from typing import Optional, Callable
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.trace import get_tracer_provider, Status, StatusCode
from opentelemetry import trace

from config import Config

# Global tracer instance
_tracer = None


def init_tracing() -> Optional[object]:
    """Initialize Phoenix tracing if configured"""
    global _tracer

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

        # Initialize global tracer
        _tracer = tracer_provider.get_tracer("acc_system")

        print(f"Phoenix tracing initialized successfully for project: {project_name}")
        return tracer_provider

    except Exception as e:
        print(f"Phoenix tracing initialization failed: {e}")
        print("Continuing without Phoenix tracing...")
        return None


def trace_method(span_name: Optional[str] = None):
    """Decorator to trace method execution with Phoenix"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If tracing is not initialized, execute the original function directly
            if not _tracer:
                return func(*args, **kwargs)

            # Generate span name
            name = span_name or f"{func.__name__}"

            # Create tracing span
            with _tracer.start_as_current_span(name) as span:
                try:
                    # Add basic attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    # Execute original function
                    result = func(*args, **kwargs)

                    # Set span status to OK
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("function.success", True)
                    return result

                except Exception as e:
                    # Set span status to ERROR
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator