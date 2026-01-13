"""
OCR LEVEL 3 - ANALYSE AVANCÉE + MÉMOIRE IA
Niveau rare, déclenché uniquement si nécessaire
"""

import logging
from datetime import datetime
from copy import deepcopy

logger = logging.getLogger("OCREngine.Level3")


class OCRLevel3:
    """
    OCR Niveau 3 : Règles mémoire + enrichissement IA
    """

    def __init__(self):
        logger.info("OCR Level 3 initialized")
        logger.warning("Level 3 is RARE and creates memory rules")

    def process(
        self,
        document,
        ocr2_result=None,
        context=None,
        previous_result=None,
        **kwargs
    ):
        """
        Traitement OCR niveau 3
        Compatibilité :
        - ocr2_result (ancien appel)
        - previous_result (nouveau moteur)
        """

        # 🔁 Compatibilité backward
        if previous_result is not None and ocr2_result is None:
            ocr2_result = previous_result

        if ocr2_result is None:
            logger.warning("OCR Level 3 called without previous OCR result")
            return None

        result = deepcopy(ocr2_result)

        # Exemple règle mémoire
        result.confidence = min(result.confidence + 0.05, 1.0)
        result.level = 3
        result.processing_date = datetime.utcnow()
        result.needs_next_level = False

        logger.info(
            f"[{result.document_id}] Level 3 applied | confidence={result.confidence}"
        )

        return result
