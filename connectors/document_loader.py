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
        """Charge un PDF"""
        # Essayer d'abord PyPDF2 (pour PDF textuels)
        if self.has_pypdf2:
            try:
                text = self._extract_pdf_pypdf2(file_path)
                if text.strip():
                    logger.info(f"PDF loaded with PyPDF2: {len(text)} chars")
                    return Document(file_path, text, {'method': 'pypdf2'})
            except Exception as e:
                logger.warning(f"PyPDF2 failed: {e}")
        
        # Essayer pdfplumber
        if self.has_pdfplumber:
            try:
                text = self._extract_pdf_pdfplumber(file_path)
                if text.strip():
                    logger.info(f"PDF loaded with pdfplumber: {len(text)} chars")
                    return Document(file_path, text, {'method': 'pdfplumber'})
            except Exception as e:
                logger.warning(f"pdfplumber failed: {e}")
        
        # Fallback : OCR avec pytesseract (PDF scanné)
        if self.has_pytesseract:
            try:
                text = self._extract_pdf_ocr(file_path)
                logger.info(f"PDF loaded with OCR: {len(text)} chars")
                return Document(file_path, text, {'method': 'tesseract_ocr'})
            except Exception as e:
                logger.error(f"OCR failed: {e}")
        
        # Si rien n'a marché
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
        """Extrait texte d'un PDF scanné via OCR"""
        # Nécessite pdf2image + pytesseract
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convertir PDF en images
            images = convert_from_path(file_path)
            
            text = []
            for i, image in enumerate(images):
                logger.debug(f"OCR page {i+1}/{len(images)}")
                page_text = pytesseract.image_to_string(image, lang='fra')
                text.append(page_text)
            
            return '\n'.join(text)
            
        except ImportError:
            raise ValueError("pdf2image required for OCR. Install: pip install pdf2image pytesseract")
    
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
