"""Document types definitions"""

from enum import Enum


class DocumentType(Enum):
    """Types de documents gérés par le système OCR"""
    
    FACTURE = "facture"
    DEVIS = "devis"
    TICKET = "ticket"
    RECU = "recu"
    BON_LIVRAISON = "bon_livraison"
    NOTE_FRAIS = "note_frais"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, type_str: str) -> 'DocumentType':
        """Convertit une chaîne en DocumentType"""
        try:
            return cls(type_str.lower())
        except ValueError:
            return cls.UNKNOWN
    
    def is_accounting_document(self) -> bool:
        """Retourne True si document comptable"""
        return self in [
            DocumentType.FACTURE,
            DocumentType.DEVIS,
            DocumentType.TICKET,
            DocumentType.RECU
        ]