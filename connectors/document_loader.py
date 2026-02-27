"""
Document Loader

Charge les documents PDF et images pour traitement OCR
"""

import logging
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger("OCREngine.Loader")


class Document:
    """
    Représente un document chargé
    
    Fournit une interface unifiée pour accéder au texte
    peu importe le format source (PDF, image, etc.)
    """
    
    def __init__(self, file_path: str, text_content: str, metadata: dict = None):
        """
        Initialise un document
        
        Args:
            file_path: Chemin source
            text_content: Texte extrait
            metadata: Métadonnées optionnelles
        """
        self.file_path = file_path
        self.text_content = text_content
        self.metadata = metadata or {}
        self.filename = os.path.basename(file_path)
    
    def get_text(self) -> str:
        """Retourne le texte complet du document"""
        return self.text_content
    
    def get_lines(self) -> list:
        """Retourne les lignes du document"""
        return self.text_content.split('\n')
    
    def __repr__(self):
        return f"Document(filename={self.filename}, text_length={len(self.text_content)})"


class DocumentLoader:
    """
    Charge les documents depuis différentes sources
    
    Supporte :
    - PDF (via PyPDF2, pdfplumber, ou pytesseract pour scans)
    - Images (via pytesseract)
    - Texte brut
    """
    
    def __init__(self, config: dict):
        """
        Initialise le loader
        
        Args:
            config: Configuration globale
        """
        self.config = config
        self.ocr_engine = config.get('ocr_engine', 'tesseract')
        
        # Vérifier disponibilité des libraries
        self.has_pypdf2 = self._check_import('PyPDF2')
        self.has_pdfplumber = self._check_import('pdfplumber')
        self.has_pytesseract = self._check_import('pytesseract')
        self.has_pillow = self._check_import('PIL')
        
        logger.info(f"Document Loader initialized (PyPDF2: {self.has_pypdf2}, pdfplumber: {self.has_pdfplumber}, pytesseract: {self.has_pytesseract})")
    
    def _check_import(self, module_name: str) -> bool:
        """Vérifie si un module est disponible"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def load(self, file_path: str) -> Document:
        """
        Charge un document depuis un fichier
        
        Args:
            file_path: Chemin vers le fichier
        
        Returns:
            Document chargé
        
        Raises:
            FileNotFoundError: Si fichier introuvable
            ValueError: Si format non supporté
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = Path(file_path).suffix.lower()
        
        logger.info(f"Loading document: {file_path}")
        
        # Dispatcher selon l'extension
        if file_extension == '.pdf':
            return self._load_pdf(file_path)
        
        elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self._load_image(file_path)
        
        elif file_extension == '.txt':
            return self._load_text(file_path)
        
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _load_pdf(self, file_path: str) -> Document:
        """
        Charge un PDF avec détection automatique PDF texte vs PDF scanné
        
        Logique :
        1. Essayer extraction texte (PyPDF2/pdfplumber)
        2. Si texte vide ou < 50 chars → considérer comme scanné
        3. Basculer vers OCR image
        """
        logger.info(f"DOCUMENT_LOADER_SIGNATURE: _load_pdf called for {os.path.basename(file_path)}")
        
        pdf_text_detected = False
        extracted_text = ""
        
        # === ÉTAPE 1 : TENTATIVE EXTRACTION TEXTE ===
        
        # Essayer d'abord PyPDF2 (pour PDF textuels)
        if self.has_pypdf2:
            try:
                text = self._extract_pdf_pypdf2(file_path)
                if text.strip():
                    extracted_text = text
                    logger.info(f"PyPDF2: extracted {len(text)} chars")
            except Exception as e:
                logger.warning(f"PyPDF2 failed: {e}")
        
        # Si pas de texte, essayer pdfplumber
        if not extracted_text and self.has_pdfplumber:
            try:
                text = self._extract_pdf_pdfplumber(file_path)
                if text.strip():
                    extracted_text = text
                    logger.info(f"pdfplumber: extracted {len(text)} chars")
            except Exception as e:
                logger.warning(f"pdfplumber failed: {e}")
        
        # === ÉTAPE 2 : DÉCISION PDF TEXTE VS SCANNÉ ===
        
        # Seuil : minimum 50 caractères pour considérer comme "texte natif"
        MIN_TEXT_THRESHOLD = 50
        
        if extracted_text.strip() and len(extracted_text.strip()) >= MIN_TEXT_THRESHOLD:
            pdf_text_detected = True
            logger.info(f"PDF_TEXT_DETECTED=true, OCR_MODE=TEXT (text_len={len(extracted_text)})")
            return Document(file_path, extracted_text, {
                'method': 'text_extraction',
                'ocr_mode': 'TEXT',
                'pdf_text_detected': True
            })
        
        # === ÉTAPE 3 : PDF SCANNÉ → OCR IMAGE ===
        
        logger.info(f"PDF_TEXT_DETECTED=false, OCR_MODE=IMAGE (text_len={len(extracted_text)})")
        logger.info("OCR_IMAGE_START: Converting PDF to images for OCR...")
        
        # Fallback : OCR avec pytesseract (PDF scanné)
        if self.has_pytesseract:
            try:
                text = self._extract_pdf_ocr(file_path)
                logger.info(f"OCR_IMAGE_OK: Extracted {len(text)} chars via OCR")
                logger.info(f"OCR_IMAGE_TEXT_LEN={len(text)}")
                
                return Document(file_path, text, {
                    'method': 'tesseract_ocr',
                    'ocr_mode': 'IMAGE',
                    'pdf_text_detected': False
                })
            except Exception as e:
                logger.error(f"OCR_IMAGE_FAILED: {e}")
                raise ValueError(f"OCR failed on scanned PDF: {e}")
        
        # Si rien n'a marché
        logger.error("NO_OCR_METHOD_AVAILABLE: pytesseract not found")
        raise ValueError(f"Could not extract text from PDF: {file_path}. Install PyPDF2, pdfplumber or pytesseract")
    
    def _extract_pdf_pypdf2(self, file_path: str) -> str:
        """Extrait texte avec PyPDF2"""
        import PyPDF2
        
        text = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text())
        
        return '\n'.join(text)
    
    def _extract_pdf_pdfplumber(self, file_path: str) -> str:
        """Extrait texte avec pdfplumber"""
        import pdfplumber
        
        text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        
        return '\n'.join(text)
    
    def _extract_pdf_ocr(self, file_path: str) -> str:
        """
        Extrait texte d'un PDF scanné via OCR (pytesseract).

        Principes (stables, non "patch bancal") :
        - Rendu PDF -> images via pdf2image
        - OCR plein page (PSM configurable)
        - Si les tokens de totaux (HT/TVA/TTC / NET A PAYER) ne sont pas détectés,
          on déclenche un "FOOTER PASS" : OCR du bas de page (crop) avec pré-traitement
          + double PSM (6 & 11) pour capturer les totaux.
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract
            from PIL import ImageOps, ImageEnhance
        except ImportError as e:
            raise ValueError(f"OCR dependencies missing: {e}. Install: pip install pdf2image pytesseract pillow")

        # ----------------------------
        # Runtime configuration (env)
        # ----------------------------
        def _env_bool(name: str, default: bool) -> bool:
            v = os.getenv(name)
            if v is None:
                return default
            return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

        def _env_int(name: str, default: int) -> int:
            v = os.getenv(name)
            try:
                return int(str(v).strip()) if v is not None and str(v).strip() else default
            except Exception:
                return default

        def _env_float(name: str, default: float) -> float:
            v = os.getenv(name)
            try:
                return float(str(v).strip()) if v is not None and str(v).strip() else default
            except Exception:
                return default

        dpi = _env_int("OCR_PDF_DPI", 300)  # 300 DPI par défaut
        lang = os.getenv("OCR_TESSERACT_LANG", "fra+eng") or "fra+eng"
        oem = str(os.getenv("OCR_TESSERACT_OEM", "1") or "1").strip() or "1"
        psm_main = str(os.getenv("OCR_TESSERACT_PSM_MAIN", "6") or "6").strip() or "6"
        psm_footer = str(os.getenv("OCR_TESSERACT_PSM_FOOTER", "11") or "11").strip() or "11"

        footer_pass = _env_bool("OCR_FOOTER_PASS", True)
        footer_ratio = _env_float("OCR_FOOTER_RATIO", 0.35)
        footer_ratio = max(0.15, min(0.60, footer_ratio))  # garde-fou

        # ----------------------------
        # Heuristiques "totaux"
        # ----------------------------
        def _has_totals_tokens_(t: str) -> bool:
            t2 = (t or "").upper()
            if "TOTAL" in t2 and ("TTC" in t2 or "TVA" in t2 or "HT" in t2):
                return True
            if "NET A PAYER" in t2 or "NET À PAYER" in t2:
                return True
            if "BASE HT" in t2 or "TOTAL TVA" in t2 or "TOTAL TTC" in t2:
                return True
            return False

        def _preproc(img):
            # Pré-traitement simple pour améliorer les petits caractères
            try:
                g = img.convert("L")
                g = ImageOps.autocontrast(g)
                g = ImageEnhance.Contrast(g).enhance(2.0)
                g = g.point(lambda x: 0 if x < 180 else 255, "1")
                return g
            except Exception:
                return img

        def _ocr(img, psm: str, preproc: bool = False) -> str:
            try:
                img2 = _preproc(img) if preproc else img
                config = f"--oem {oem} --psm {psm}"
                return pytesseract.image_to_string(img2, lang=lang, config=config)
            except Exception as e:
                logger.warning(f"OCR failed (psm={psm}): {e}")
                return ""

        try:
            # Convertir PDF en images (nécessite poppler-utils)
            logger.debug(f"Converting PDF to images (dpi={dpi})...")
            images = convert_from_path(file_path, dpi=dpi)
            logger.info(f"Converted to {len(images)} image(s) (dpi={dpi})")

            text_parts = []
            for i, image in enumerate(images):
                logger.debug(f"OCR page {i+1}/{len(images)} (psm={psm_main})...")
                page_text = _ocr(image, psm_main, preproc=False) or ""
                logger.debug(f"  → Page {i+1}: {len(page_text)} chars")

                footer_text = ""
                if footer_pass and not _has_totals_tokens_(page_text):
                    # OCR bas de page (totaux)
                    try:
                        w, h = image.size
                        y0 = int(h * (1.0 - footer_ratio))
                        y0 = max(0, min(h - 1, y0))
                        footer_img = image.crop((0, y0, w, h))

                        t1 = _ocr(footer_img, psm_main, preproc=True) or ""
                        t2 = _ocr(footer_img, psm_footer, preproc=True) or ""

                        # Choix du meilleur candidat
                        best = ""
                        if _has_totals_tokens_(t1):
                            best = t1
                        elif _has_totals_tokens_(t2):
                            best = t2
                        else:
                            best = t1 if len(t1) >= len(t2) else t2

                        if best.strip():
                            logger.info(f"OCR_FOOTER_PASS: page={i+1}, footer_len={len(best)}, ratio={footer_ratio}")
                            footer_text = f"\n[FOOTER_OCR_PAGE_{i+1}]\n{best}\n"
                    except Exception as e:
                        logger.warning(f"OCR_FOOTER_PASS failed (page={i+1}): {e}")

                text_parts.append(page_text + footer_text)

            full_text = "\n".join(text_parts)
            logger.info(f"OCR completed: {len(full_text)} total chars from {len(images)} page(s)")
            return full_text

        except Exception as e:
            logger.error(f"PDF to image conversion or OCR failed: {e}")
            raise ValueError(f"OCR processing failed: {e}. Check poppler-utils and tesseract installation.")

    def _load_image(self, file_path: str) -> Document:
        """Charge une image via OCR"""
        if not self.has_pytesseract:
            raise ValueError("pytesseract required for image OCR. Install: pip install pytesseract")
        
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='fra')
            
            logger.info(f"Image loaded with OCR: {len(text)} chars")
            
            return Document(file_path, text, {'method': 'tesseract_ocr'})
            
        except Exception as e:
            raise ValueError(f"Failed to OCR image: {e}")
    
    def _load_text(self, file_path: str) -> Document:
        """Charge un fichier texte"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        logger.info(f"Text file loaded: {len(text)} chars")
        
        return Document(file_path, text, {'method': 'direct_text'})
    
    def supported_formats(self) -> list:
        """Retourne les formats supportés"""
        formats = ['.txt']
        
        if self.has_pypdf2 or self.has_pdfplumber or self.has_pytesseract:
            formats.append('.pdf')
        
        if self.has_pytesseract and self.has_pillow:
            formats.extend(['.png', '.jpg', '.jpeg', '.tiff', '.bmp'])
        
        return formats
