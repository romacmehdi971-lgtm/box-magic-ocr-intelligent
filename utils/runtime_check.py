"""
Runtime checks for OCR dependencies

Vérifie au démarrage que tous les binaires et libs nécessaires sont disponibles
"""

import logging
import subprocess
import sys
from typing import Dict, Tuple

logger = logging.getLogger("OCREngine.RuntimeCheck")


def check_binary(binary_name: str) -> Tuple[bool, str]:
    """
    Vérifie la présence et version d'un binaire
    
    Returns:
        (is_available, version_info)
    """
    try:
        # pdfinfo et pdftoppm utilisent -v au lieu de --version
        if binary_name in ['pdfinfo', 'pdftoppm']:
            result = subprocess.run(
                [binary_name, '-v'],
                capture_output=True,
                text=True,
                timeout=5
            )
        else:
            result = subprocess.run(
                [binary_name, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
        
        # Extraire version depuis stdout ou stderr
        output = result.stdout if result.stdout else result.stderr
        version = output.split('\n')[0] if output else "FOUND (no version)"
        return True, version
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "NOT FOUND"
    except Exception as e:
        return False, f"ERROR: {e}"


def check_python_lib(lib_name: str) -> Tuple[bool, str]:
    """
    Vérifie la présence d'une lib Python
    
    Returns:
        (is_available, version_info)
    """
    try:
        module = __import__(lib_name)
        version = getattr(module, '__version__', 'unknown version')
        return True, version
    except ImportError:
        return False, "NOT INSTALLED"
    except Exception as e:
        return False, f"ERROR: {e}"


def check_runtime_dependencies() -> Dict[str, Dict]:
    """
    Vérifie toutes les dépendances runtime
    
    Returns:
        Dict avec status de chaque dépendance
    """
    logger.info("=" * 60)
    logger.info("RUNTIME DEPENDENCY CHECK")
    logger.info("=" * 60)
    
    checks = {
        'binaries': {},
        'python_libs': {},
        'all_ok': True
    }
    
    # Binaires système critiques
    binaries_to_check = [
        ('tesseract', True),   # (name, is_critical)
        ('pdfinfo', True),
        ('pdftoppm', True),
    ]
    
    for binary_name, is_critical in binaries_to_check:
        is_available, version = check_binary(binary_name)
        checks['binaries'][binary_name] = {
            'available': is_available,
            'version': version,
            'critical': is_critical
        }
        
        status = "✓" if is_available else "✗"
        logger.info(f"{status} {binary_name}: {version}")
        
        if is_critical and not is_available:
            checks['all_ok'] = False
            logger.error(f"CRITICAL: {binary_name} is missing!")
    
    logger.info("-" * 60)
    
    # Libs Python critiques
    python_libs = [
        ('PyPDF2', False),      # (name, is_critical)
        ('pdfplumber', False),
        ('pdf2image', True),
        ('pytesseract', True),
        ('PIL', True),
    ]
    
    for lib_name, is_critical in python_libs:
        is_available, version = check_python_lib(lib_name)
        checks['python_libs'][lib_name] = {
            'available': is_available,
            'version': version,
            'critical': is_critical
        }
        
        status = "✓" if is_available else "✗"
        logger.info(f"{status} {lib_name}: {version}")
        
        if is_critical and not is_available:
            checks['all_ok'] = False
            logger.error(f"CRITICAL: {lib_name} is missing!")
    
    logger.info("=" * 60)
    
    if checks['all_ok']:
        logger.info("✓ ALL RUNTIME DEPENDENCIES OK")
    else:
        logger.error("✗ SOME CRITICAL DEPENDENCIES MISSING")
        logger.error("OCR IMAGE mode will NOT work properly!")
    
    logger.info("=" * 60)
    
    return checks


def guard_critical_dependencies():
    """
    Vérifie les dépendances critiques et FAIL si manquantes
    
    À appeler au démarrage de l'application
    """
    checks = check_runtime_dependencies()
    
    if not checks['all_ok']:
        logger.error("")
        logger.error("=" * 60)
        logger.error("CRITICAL DEPENDENCIES MISSING - APPLICATION CANNOT START")
        logger.error("=" * 60)
        
        missing_binaries = [
            name for name, info in checks['binaries'].items()
            if info['critical'] and not info['available']
        ]
        
        missing_libs = [
            name for name, info in checks['python_libs'].items()
            if info['critical'] and not info['available']
        ]
        
        if missing_binaries:
            logger.error(f"Missing binaries: {', '.join(missing_binaries)}")
            logger.error("Install with: apt-get install tesseract-ocr poppler-utils")
        
        if missing_libs:
            logger.error(f"Missing Python libs: {', '.join(missing_libs)}")
            logger.error("Install with: pip install pdf2image pytesseract Pillow")
        
        logger.error("=" * 60)
        
        raise RuntimeError("Critical dependencies missing - see logs above")
    
    return True


if __name__ == "__main__":
    # Test standalone
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        guard_critical_dependencies()
        print("\n✓ Runtime checks PASSED")
    except RuntimeError as e:
        print(f"\n✗ Runtime checks FAILED: {e}")
        sys.exit(1)
