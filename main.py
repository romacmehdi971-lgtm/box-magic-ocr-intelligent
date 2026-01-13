# PATH: /main.py

import base64
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ocr_engine import OCREngine


APP_NAME = "box-magic-ocr-intelligent"
APP_VERSION = "1.0.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)

_ENGINE: Optional[OCREngine] = None


def _get_engine() -> OCREngine:
    global _ENGINE
    if _ENGINE is None:
        # Le moteur charge par défaut: config/config.yaml (chemin relatif repo)
        _ENGINE = OCREngine()
    return _ENGINE


class OCRRequest(BaseModel):
    source_entreprise: str = Field(..., min_length=1, description="Entreprise source (ex: MARTIN’S TRAITEUR)")
    filename: str = Field(default="document.pdf", description="Nom du fichier (info)")
    file_b64: str = Field(..., min_length=10, description="Contenu du fichier encodé en base64")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Options OCR (ex: force_level, force_full_ocr)")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
    }


@app.post("/ocr")
def ocr(req: OCRRequest) -> Dict[str, Any]:
    # 1) Decode base64
    try:
        raw = base64.b64decode(req.file_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="file_b64 invalid base64")

    # 2) Write temp file in /tmp (Cloud Run writable)
    safe_name = "".join([c for c in (req.filename or "document.pdf") if c.isalnum() or c in "._-"])[:120]
    tmp_path = f"/tmp/{uuid.uuid4().hex}_{safe_name}"

    try:
        with open(tmp_path, "wb") as f:
            f.write(raw)

        # 3) Run OCR Engine
        engine = _get_engine()
        result = engine.process_document(
            file_path=tmp_path,
            source_entreprise=req.source_entreprise,
            options=req.options or {},
        )

        # 4) Return JSON (OCRResult.to_dict() existe)
        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR error: {type(e).__name__}: {str(e)}")

    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
