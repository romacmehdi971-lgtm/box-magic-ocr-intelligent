"""
OCR LEVEL 2 - ANALYSE APPROFONDIE
Objectif : Améliorer les résultats OCR1 sans les dégrader
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List
from copy import deepcopy

logger = logging.getLogger("OCREngine.Level2")


class OCRLevel2:
    """
    OCR Niveau 2 : Analyse approfondie et amélioration ciblée
    """

    def __init__(self):
        logger.info("OCR Level 2 initialized")

    def process(
        self,
        document,
        ocr1_result=None,
        context=None,
        previous_result=None,
        **kwargs
    ):
        """
        Traitement OCR niveau 2
        Compatibilité :
        - ocr1_result (ancien appel positionnel)
        - previous_result (appel keyword depuis le moteur)
        """

        # 🔁 Compatibilité backward
        if previous_result is not None and ocr1_result is None:
            ocr1_result = previous_result

        if ocr1_result is None:
            logger.warning("OCR Level 2 called without previous OCR result")
            return None

        result = deepcopy(ocr1_result)

        # Exemple d'amélioration simple
        if result.fields.get("type") == "facture":
            result.confidence = min(result.confidence + 0.1, 1.0)

        result.level = 2
        result.processing_date = datetime.utcnow()

        logger.info(
            f"[{result.document_id}] Level 2 processed | confidence={result.confidence}"
        )

        return result
