"""
Memory system - Rule storage and retrieval
"""

from .ai_memory import AIMemory

# Rule est optionnel : on ne doit JAMAIS faire crasher l'import du package
try:
    from .ai_memory import Rule
    __all__ = ["AIMemory", "Rule"]
except Exception:
    __all__ = ["AIMemory"]
