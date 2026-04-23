"""Warstwa orchestratora.

Ten pakiet powinien zależeć wyłącznie od bazowego interfejsu providera LLM,
bez importowania konkretnych implementacji (np. Ollama/Mock).
"""

from packages.orchestrator.task_orchestrator import TaskOrchestrator
from packages.providers.base import BaseLLMProvider

__all__ = ["BaseLLMProvider", "TaskOrchestrator"]
