"""
Document Loader

Charge les documents PDF et images pour traitement OCR.

Objectif WORK (BOX MAGIC 2026) :
- Détecter correctement les PDF image (scan/photo) et basculer sur OCR IMAGE.
- Fournir des logs précis (diagnostic poppler / tesseract) pour éviter les erreurs génériques.
- Ne jamais masquer l’exception racine.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("OCREngine.Loader")


class Document:
    """
    Représente un document chargé.
    Fournit une interface unifiée pour accéder au texte quel que soit le format source.
    """

    def __init__(self, file_path: str, text_content: str, metadata: dict = None):
        self.file_path = file_path
        self.text_content = text_content or ""
        self.metadata = metadata or {}
        self.filename = os.path.basename(file_path)

    def get_text(self) -> str:
        return self.text_content

    def get_lines(self) -> list:
        return self.text_content.split("\n")

    def __repr__(self):
        return f"Document(filename={self.filename}, text_length={len(self.text_content)})"


class DocumentLoader:
    """
    Charge des documents depuis différentes sources :
    - PDF (texte natif via PyPDF2/pdfplumber, sinon OCR via pdf2image+pytesseract)
    - Images (OCR via pytesseract)
    - Texte brut
    """

    def __init__(self, config: dict):
        self.config = config or {}
        self.ocr_engine = self.config.get("ocr_engine", "tesseract")

        # OCR config
        self.ocr_lang = self.config.get("ocr_lang", "fra+eng")
        self.ocr_dpi = int(self.config.get("ocr_dpi", 250))
        self.ocr_timeout_sec = int(self.config.get("ocr_timeout_sec", 30))
        self.min_text_len_for_pdf_text = int(self.config.get("min_text_len_for_pdf_text", 50))

        # Vérifier disponibilité des libs Python
        self.has_pypdf2 = self._check_import("PyPDF2")
        self.has_pdfplumber = self._check_import("pdfplumber")
        self.has_pytesseract = self._check_import("pytesseract")
        self.has_pillow = self._check_import("PIL")
        self.has_pdf2image = self._check_import("pdf2image")

        # Vérifier binaires système nécessaires (poppler, tesseract)
        self.has_tesseract_bin = self._check_binary("tesseract")
        self.has_pdfinfo_bin = self._check_binary("pdfinfo")
        self.has_pdftoppm_bin = self._check_binary("pdftoppm")

        logger.info(
            "DocumentLoader init | PyPDF2=%s pdfplumber=%s pytesseract=%s pdf2image=%s | "
            "BIN tesseract=%s pdfinfo=%s pdftoppm=%s | ocr_lang=%s dpi=%s",
            self.has_pypdf2,
            self.has_pdfplumber,
            self.has_pytesseract,
            self.has_pdf2image,
            self.has_tesseract_bin,
            self.has_pdfinfo_bin,
            self.has_pdftoppm_bin,
            self.ocr_lang,
            self.ocr_dpi,
        )

    def _check_import(self, module_name: str) -> bool:
        try:
            __import__(module_name)
            return True
        except Exception:
            return False

    def _check_binary(self, bin_name: str) -> bool:
        try:
            return shutil.which(bin_name) is not None
        except Exception:
            return False

    def load(self, file_path: str) -> Document:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_extension = Path(file_path).suffix.lower()
        logger.info("Loading document: %s (ext=%s)", file_path, file_extension)

        if file_extension == ".pdf":
            return self._load_pdf(file_path)

        if file_extension in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            return self._load_image(file_path)

        if file_extension == ".txt":
            return self._load_text(file_path)

        raise ValueError(f"Unsupported file format: {file_extension}")

    # -------------------------------------------------------------------------
    # PDF loading
    # -------------------------------------------------------------------------

    def _load_pdf(self, file_path: str) -> Document:
        """
        Charge un PDF :
        1) tente extraction texte natif
        2) si vide → bascule OCR IMAGE (pdf2image -> pytesseract)
        """
        # 1) extraction texte natif
        text, method = self._try_extract_pdf_text(file_path)

        if text and text.strip():
            logger.info("PDF TEXT OK (%s): %s chars", method, len(text))
            return Document(file_path, text, {"method": method, "ocr_mode": "TEXT"})

        logger.info("PDF appears IMAGE/SCAN (no extractible text). Switching to OCR IMAGE.")

        # 2) OCR IMAGE
        ocr_text = self._extract_pdf_ocr(file_path)

        if ocr_text and ocr_text.strip():
            logger.info("PDF OCR IMAGE OK: %s chars", len(ocr_text))
            return Document(file_path, ocr_text, {"method": "tesseract_ocr", "ocr_mode": "IMAGE"})

        # Si OCR retourne vide, on retourne une erreur claire
        raise ValueError(
            f"OCR_IMAGE_EMPTY: No text extracted from scanned PDF: {file_path}. "
            f"Check image quality / DPI / language. "
            f"(tesseract_bin={self.has_tesseract_bin}, pdftoppm_bin={self.has_pdftoppm_bin})"
        )

    def _try_extract_pdf_text(self, file_path: str) -> Tuple[str, str]:
        """
        Retourne (text, method) ou ("","") si rien d’extractible.
        """
        # PyPDF2
        if self.has_pypdf2:
            try:
                text = self._extract_pdf_pypdf2(file_path)
                if text and len(text.strip()) >= self.min_text_len_for_pdf_text:
                    return text, "pypdf2"
            except Exception as e:
                logger.warning("PDF text extract (PyPDF2) failed: %s", e)

        # pdfplumber
        if self.has_pdfplumber:
            try:
                text = self._extract_pdf_pdfplumber(file_path)
                if text and len(text.strip()) >= self.min_text_len_for_pdf_text:
                    return text, "pdfplumber"
            except Exception as e:
                logger.warning("PDF text extract (pdfplumber) failed: %s", e)

        return "", ""

    def _extract_pdf_pypdf2(self, file_path: str) -> str:
        import PyPDF2

        text = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_txt = page.extract_text() or ""
                text.append(page_txt)
        return "\n".join(text)

    def _extract_pdf_pdfplumber(self, file_path: str) -> str:
        import pdfplumber

        text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text.append(page_text)
        return "\n".join(text)

    def _extract_pdf_ocr(self, file_path: str) -> str:
        """
        OCR d’un PDF scanné :
        - convert PDF -> images via pdf2image (poppler required)
        - OCR via pytesseract
        Logs précis si poppler/tesseract manquent.
        """
        if not self.has_pdf2image:
            raise ValueError("OCR_IMAGE_MISSING_PYLIB: pdf2image not installed")

        if not self.has_pytesseract:
            raise ValueError("OCR_IMAGE_MISSING_PYLIB: pytesseract not installed")

        if not self.has_tesseract_bin:
            raise ValueError("OCR_IMAGE_MISSING_BIN: tesseract not found in PATH")

        # Poppler bins
        if not self.has_pdftoppm_bin and not self.has_pdfinfo_bin:
            raise ValueError(
                "OCR_IMAGE_MISSING_BIN: poppler not found in PATH (pdftoppm/pdfinfo missing). "
                "Install poppler-utils and ensure binaries are in PATH."
            )

        try:
            from pdf2image import convert_from_path
            import pytesseract

            # Diagnostic runtime (utile Cloud Run)
            logger.info(
                "OCR_IMAGE_START | file=%s | dpi=%s | lang=%s | bin(tesseract=%s, pdftoppm=%s, pdfinfo=%s)",
                file_path,
                self.ocr_dpi,
                self.ocr_lang,
                shutil.which("tesseract"),
                shutil.which("pdftoppm"),
                shutil.which("pdfinfo"),
            )

            # Convert PDF -> images
            images = convert_from_path(file_path, dpi=self.ocr_dpi)

            logger.info("OCR_IMAGE_CONVERT_OK | pages=%s", len(images))

            text_parts = []
            for i, image in enumerate(images):
                logger.debug("OCR_IMAGE_PAGE | %s/%s", i + 1, len(images))
                page_text = pytesseract.image_to_string(image, lang=self.ocr_lang) or ""
                text_parts.append(page_text)

            full_text = "\n".join(text_parts).strip()

            logger.info("OCR_IMAGE_TEXT_LEN | %s", len(full_text))
            return full_text

        except Exception as e:
            # Ne pas masquer l’erreur : on la remonte clairement
            logger.exception("OCR_IMAGE_FAILED | file=%s | reason=%s", file_path, str(e))
            raise ValueError(f"OCR_IMAGE_FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # Image loading
    # -------------------------------------------------------------------------

    def _load_image(self, file_path: str) -> Document:
        if not self.has_pytesseract:
            raise ValueError("OCR_IMAGE_MISSING_PYLIB: pytesseract not installed")
        if not self.has_pillow:
            raise ValueError("OCR_IMAGE_MISSING_PYLIB: Pillow (PIL) not installed")
        if not self.has_tesseract_bin:
            raise ValueError("OCR_IMAGE_MISSING_BIN: tesseract not found in PATH")

        try:
            import pytesseract
            from PIL import Image

            logger.info("IMAGE_OCR_START | file=%s | lang=%s", file_path, self.ocr_lang)
            image = Image.open(file_path)
            text = (pytesseract.image_to_string(image, lang=self.ocr_lang) or "").strip()

            logger.info("IMAGE_OCR_TEXT_LEN | %s", len(text))
            return Document(file_path, text, {"method": "tesseract_ocr", "ocr_mode": "IMAGE"})

        except Exception as e:
            logger.exception("IMAGE_OCR_FAILED | file=%s | reason=%s", file_path, str(e))
            raise ValueError(f"IMAGE_OCR_FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # Text loading
    # -------------------------------------------------------------------------

    def _load_text(self, file_path: str) -> Document:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read() or ""
        logger.info("Text file loaded: %s chars", len(text))
        return Document(file_path, text, {"method": "direct_text", "ocr_mode": "TEXT"})

    def supported_formats(self) -> list:
        formats = [".txt"]
        if self.has_pypdf2 or self.has_pdfplumber or self.has_pytesseract:
            formats.append(".pdf")
        if self.has_pytesseract and self.has_pillow:
            formats.extend([".png", ".jpg", ".jpeg", ".tiff", ".bmp"])
        return formats
