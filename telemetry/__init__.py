"""
Telemetry package for building compliance check system
Provides tracing and observability capabilities using Phoenix
"""

from .tracing import init_tracing

__version__ = "1.0.0"
__all__ = ["init_tracing"]