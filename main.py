"""
BOX MAGIC OCR INTELLIGENT - Main FastAPI Application for Cloud Run
Version: 1.0.2 - SAFE PATCH (multipart robustness + request diagnostics)

This is the main entry point for the Cloud Run service.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ocr_engine import OCREngine, OCRResult
from utils.runtime_check import check_runtime_dependencies
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("main", level="INFO")

# Initialize FastAPI app
app = FastAPI(
    title="BOX MAGIC OCR INTELLIGENT",
    description="Service OCR 3 niveaux avec détection de type de document",
    version="1.0.2"
)

# Global OCR engine instance
ocr_engine: Optional[OCREngine] = None

# Runtime diagnostics flag (can be disabled in production)
ENABLE_RUNTIME_DIAGNOSTICS = os.getenv("ENABLE_RUNTIME_DIAGNOSTICS", "true").lower() == "true"


@app.on_event("startup")
async def startup_event():
    """Initialize the OCR engine and run runtime checks on startup"""
    global ocr_engine

    logger.info("=" * 80)
    logger.info("BOX MAGIC OCR INTELLIGENT - Cloud Run Service Starting")
    logger.info("=" * 80)

    # Run runtime dependency checks
    if ENABLE_RUNTIME_DIAGNOSTICS:
        logger.info("Running runtime dependency checks...")
        try:
            check_runtime_dependencies()
            logger.info("✅ All runtime dependencies verified successfully")
        except Exception as e:
            logger.error(f"❌ Runtime dependency check failed: {e}")
            logger.error("Service will continue but OCR may fail")
    else:
        logger.info("Runtime diagnostics disabled (ENABLE_RUNTIME_DIAGNOSTICS=false)")

    # Initialize OCR engine
    try:
        logger.info("Initializing OCR Engine...")
        ocr_engine = OCREngine()
        logger.info("✅ OCR Engine initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OCR Engine: {e}")
        raise

    logger.info("=" * 80)
    logger.info("Service ready to process documents")
    logger.info("=" * 80)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "BOX MAGIC OCR INTELLIGENT",
        "version": "1.0.2",
        "status": "running",
        "features": [
            "3-level OCR (fast, contextual, memory)",
            "PDF text extraction",
            "PDF image OCR (Tesseract)",
            "Document type detection",
            "Multi-company support"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    if ocr_engine is None:
        raise HTTPException(status_code=503, detail="OCR Engine not initialized")

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ocr_engine": "initialized"
    }


@app.post("/ocr")
async def process_ocr(
    request: Request,
    file: UploadFile = File(None),
    source_entreprise: str = Form(default="auto-detect"),
    force_full_ocr: bool = Form(default=False)
):
    """
    Process a document with OCR

    Args:
        file: Document file (PDF, image)
        source_entreprise: Source company name or "auto-detect"
        force_full_ocr: Force full OCR even if rules exist

    Returns:
        OCR result with extracted fields and document type
    """
    if ocr_engine is None:
        raise HTTPException(status_code=503, detail="OCR Engine not initialized")

    # Log request diagnostics (SAFE: no body logging)
    content_type = request.headers.get("content-type", "")
    logger.info(f"OCR request received: content-type={content_type}")

    # If file is missing, fail fast with a clear 400 (instead of 500)
    if file is None:
        raise HTTPException(
            status_code=400,
            detail="Missing file. Expected multipart/form-data with field name 'file'."
        )

    logger.info(f"OCR request payload: file={file.filename}, source={source_entreprise}, force_full_ocr={force_full_ocr}")

    # Save uploaded file temporarily
    temp_dir = Path("/tmp/ocr_uploads")
    temp_dir.mkdir(exist_ok=True)

    safe_name = file.filename or "upload.bin"
    temp_file_path = temp_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"

    try:
        # Save file
        contents = await file.read()
        with open(temp_file_path, "wb") as f:
            f.write(contents)

        logger.info(f"File saved to: {temp_file_path} (size={len(contents)} bytes)")

        # Process with OCR engine
        options = {
            "force_full_ocr": force_full_ocr
        }

        result: OCRResult = ocr_engine.process_document(
            file_path=str(temp_file_path),
            source_entreprise=source_entreprise,
            options=options
        )

        # Convert result to dict (contract unchanged)
        response = {
            "document_id": result.document_id,
            "document_type": result.document_type,
            "level": result.level,
            "confidence": result.confidence,
            "entreprise_source": result.entreprise_source,
            "fields": {
                name: {
                    "value": field.value,
                    "confidence": field.confidence,
                    "extraction_method": field.extraction_method,
                    "position": field.position,
                    "pattern": field.pattern
                }
                for name, field in result.fields.items()
            },
            "processing_date": result.processing_date.isoformat() if isinstance(result.processing_date, datetime) else result.processing_date,
            "needs_next_level": result.needs_next_level,
            "improved_fields": result.improved_fields or [],
            "corrections": result.corrections or [],
            "rule_created": result.rule_created,
            "logs": result.logs
        }

        logger.info(f"OCR completed: type={result.document_type}, level={result.level}, confidence={result.confidence:.2f}%")
        return JSONResponse(content=response)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

    finally:
        # Cleanup temp file
        if temp_file_path.exists():
            temp_file_path.unlink()
            logger.info(f"Temp file removed: {temp_file_path}")


@app.get("/config")
async def get_config():
    """Get current OCR configuration"""
    if ocr_engine is None:
        raise HTTPException(status_code=503, detail="OCR Engine not initialized")

    return {
        "config": ocr_engine.config,
        "entreprises": ocr_engine.entreprises
    }


if __name__ == "__main__":
    # For local testing
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
