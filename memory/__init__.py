"""
Memory system - Rule storage and retrieval
"""

from .ai_memory import AIMemory

# Rule est optionnel : ne doit JAMAIS bloquer le démarrage du service
try:
    from .ai_memory import Rule
    __all__ = ["AIMemory", "Rule"]
except Exception:
    __all__ = ["AIMemory"]
