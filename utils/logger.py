"""Logger configuration for OCR Engine

Rôle:
- Fournir un logger standard (stdout) compatible Cloud Run
- Offrir une fonction log_ocr_decision ULTRA tolérante (compat multi-signatures)
  afin de ne jamais casser le pipeline OCR (niveaux 1/2/3)

Compatibilité log_ocr_decision:
- Signature historique: (logger, document_id, level, decision)
- Signature enrichie:  (logger, document_id, level, decision, details)
- Signature métriques: (logger, document_id, level, decision, confidence, needs_next_level)
- Toute variante supplémentaire est tolérée via *args/**kwargs (safe)
"""

import json
import logging
import sys
from typing import Any, Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Configure un logger pour le système OCR.

    - Sortie console (stdout) compatible Cloud Run
    - Anti-duplication des handlers (reload Cloud Run)
    - Niveau paramétrable (DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger(name)

    # Évite la duplication de handlers en cas de reload Cloud Run
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = False
    return logger


def log_ocr_decision(
    logger: logging.Logger,
    document_id: str,
    level: int,
    decision: str,
    details: Optional[Any] = None,
    confidence: Optional[float] = None,
    needs_next_level: Optional[bool] = None,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Log une décision OCR de manière structurée, sans jamais casser le pipeline.

    Cette fonction est volontairement tolérante:
    - accepte plusieurs signatures historiques / enrichies
    - accepte des arguments supplémentaires (ignorés ou intégrés en détails)

    Args:
        logger: Logger à utiliser
        document_id: ID du document
        level: Niveau OCR (1, 2, 3)
        decision: Description de la décision (string)
        details: Détails optionnels (dict/str/obj)
        confidence: Score de confiance (0.0 à 1.0)
        needs_next_level: Indique si le niveau suivant est requis
    """
    try:
        # ---- Détection d'appels anciens / ambigus (5ème paramètre)
        # Cas fréquent: (logger, doc_id, level, decision, confidence) => details reçoit float
        if confidence is None and needs_next_level is None and isinstance(details, (int, float)):
            confidence = float(details)
            details = None

        # Cas: (logger, doc_id, level, decision, confidence, needs_next_level) passé via *args
        # ou confusion positional => on tente de récupérer dans args si absents.
        if confidence is None and args:
            if isinstance(args[0], (int, float)):
                confidence = float(args[0])

        if needs_next_level is None and args:
            # needs_next_level peut être 2ème arg après confidence
            for item in args:
                if isinstance(item, bool):
                    needs_next_level = bool(item)
                    break

        # kwargs fallback
        if confidence is None and "confidence" in kwargs:
            try:
                confidence = float(kwargs.get("confidence"))
            except Exception:
                pass

        if needs_next_level is None and "needs_next_level" in kwargs:
            try:
                needs_next_level = bool(kwargs.get("needs_next_level"))
            except Exception:
                pass

        # Si des args/kwargs supplémentaires existent, on les injecte dans details (audit)
        extra = {}
        if args:
            extra["extra_args"] = [repr(a) for a in args]
        if kwargs:
            extra["extra_kwargs"] = {k: repr(v) for k, v in kwargs.items()}

        payload = {
            "document_id": document_id,
            "level": int(level) if level is not None else None,
            "decision": str(decision),
        }

        if confidence is not None:
            payload["confidence"] = confidence
        if needs_next_level is not None:
            payload["needs_next_level"] = needs_next_level

        if details is not None:
            payload["details"] = details

        if extra:
            payload["extra"] = extra

        # JSON safe
        try:
            msg = json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            msg = f"[{document_id}] [Level {level}] DECISION: {decision} | confidence={confidence} | needs_next_level={needs_next_level} | details={repr(details)}"

        logger.info(msg)

    except Exception:
        # Ultra safe: ne jamais casser le pipeline à cause des logs
        try:
            logger.info(f"[{document_id}] [Level {level}] DECISION: {decision}")
        except Exception:
            pass
