"""
Test Script for New Features
Demonstrates OCR fallback and advanced disease detection.
"""

import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_disease_detection():
    """
    Test advanced disease detection with sample texts.
    """
    logger.info("=" * 70)
    logger.info("TESTING ADVANCED DISEASE DETECTION")
    logger.info("=" * 70)
    
    try:
        from disease_detector import get_disease_detector
    except ImportError:
        logger.error("Disease detector not found. Make sure disease_detector.py is in the same directory.")
        return False
    
    # Get detector
    detector = get_disease_detector(use_nlp=True)
    
    # Test cases
    test_cases = [
        {
            'name': 'Late Blight - Scientific Name',
            'text': 'The tomato plants showed severe infection by Phytophthora infestans. Water-soaked lesions appeared on leaves.',
            'filename': 'late_blight_management.txt'
        },
        {
            'name': 'Multiple Diseases',
            'text': 'Early blight (Alternaria solani) and late blight often occur together. Target spot lesions indicate Alternaria infection.',
            'filename': 'disease_guide.txt'
        },
        {
            'name': 'Virus with Acronym',
            'text': 'TYLCV causes severe yield loss. Symptoms include leaf curling and yellowing. Tomato yellow leaf curl virus spreads through whiteflies.',
            'filename': 'virus_diseases.pdf'
        },
        {
            'name': 'Symptom-Based Detection',
            'text': 'Plants exhibit concentric rings on leaves, a classic symptom. Target spots appear on older foliage first.',
            'filename': 'symptoms.txt'
        },
        {
            'name': 'No Disease',
            'text': 'Proper fertilization and irrigation are key to healthy tomato growth. Maintain soil pH between 6.0 and 6.8.',
            'filename': 'cultivation_guide.txt'
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\nTest {i}: {test_case['name']}")
        logger.info("-" * 70)
        
        # Detect diseases
        detected = detector.detect_diseases(test_case['text'], test_case['filename'])
        
        if detected:
            logger.info(f"✓ Detected {len(detected)} disease(s):")
            for disease in detected[:3]:  # Show top 3
                logger.info(f"  - {disease['name']}: {disease['confidence']:.2f} ({disease['scientific_name']})")
        else:
            logger.info("✓ No diseases detected (expected for general content)")
        
        # Get primary disease
        primary = detector.get_primary_disease(test_case['text'], test_case['filename'])
        logger.info(f"  Primary: {primary}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ Disease detection tests completed")
    logger.info("=" * 70)
    
    return True


def test_ocr_availability():
    """
    Test if OCR dependencies are available.
    """
    logger.info("\n" + "=" * 70)
    logger.info("TESTING OCR AVAILABILITY")
    logger.info("=" * 70)
    
    ocr_ready = True
    
    # Test pytesseract
    try:
        import pytesseract
        
        # Auto-configure Tesseract path for Windows
        import platform
        if platform.system() == 'Windows':
            import os
            tesseract_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
        
        logger.info("✓ pytesseract installed")
        
        # Try to get version
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"  Tesseract version: {version}")
        except Exception as e:
            logger.warning(f"  ⚠️  Tesseract not configured: {e}")
            logger.warning("  Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
            ocr_ready = False
    except ImportError:
        logger.error("✗ pytesseract not installed")
        logger.error("  Install: pip install pytesseract")
        ocr_ready = False
    
    # Test pdf2image
    try:
        from pdf2image import convert_from_path
        logger.info("✓ pdf2image installed")
    except ImportError:
        logger.error("✗ pdf2image not installed")
        logger.error("  Install: pip install pdf2image")
        ocr_ready = False
    
    # Test Pillow
    try:
        from PIL import Image
        logger.info("✓ Pillow installed")
    except ImportError:
        logger.error("✗ Pillow not installed")
        logger.error("  Install: pip install Pillow")
        ocr_ready = False
    
    if ocr_ready:
        logger.info("\n✓ OCR is ready to use!")
    else:
        logger.warning("\n⚠️  OCR not fully configured")
        logger.warning("Pipeline will work but scanned PDFs won't be processed")
    
    return ocr_ready


def test_nlp_availability():
    """
    Test if NLP dependencies are available.
    """
    logger.info("\n" + "=" * 70)
    logger.info("TESTING NLP AVAILABILITY")
    logger.info("=" * 70)
    
    nlp_ready = True
    
    # Test spaCy
    try:
        import spacy
        logger.info("✓ spaCy installed")
        
        # Try to load model
        try:
            nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model 'en_core_web_sm' loaded")
            logger.info(f"  Model version: {nlp.meta['version']}")
        except OSError:
            logger.warning("⚠️  spaCy model not found")
            logger.warning("  Download: python -m spacy download en_core_web_sm")
            nlp_ready = False
    except ImportError:
        logger.error("✗ spaCy not installed")
        logger.error("  Install: pip install spacy")
        nlp_ready = False
    
    if nlp_ready:
        logger.info("\n✓ NLP is ready for advanced disease detection!")
    else:
        logger.warning("\n⚠️  NLP not fully configured")
        logger.warning("Will use fallback keyword-based detection")
    
    return nlp_ready


def show_feature_summary():
    """
    Show summary of available features.
    """
    logger.info("\n" + "=" * 70)
    logger.info("FEATURE AVAILABILITY SUMMARY")
    logger.info("=" * 70)
    
    features = {
        'Core Pipeline': True,  # Always available
        'OCR for Scanned PDFs': False,
        'Advanced Disease Detection': False
    }
    
    # Check OCR
    try:
        import pytesseract
        from pdf2image import convert_from_path
        pytesseract.get_tesseract_version()
        features['OCR for Scanned PDFs'] = True
    except:
        pass
    
    # Check NLP
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        features['Advanced Disease Detection'] = True
    except:
        pass
    
    for feature, available in features.items():
        status = "✓ Available" if available else "✗ Not Available"
        logger.info(f"{feature:.<40} {status}")
    
    logger.info("\n" + "=" * 70)


def main():
    """
    Run all tests.
    """
    logger.info("=" * 70)
    logger.info("RAG PIPELINE - NEW FEATURES TEST")
    logger.info("=" * 70)
    
    # Test OCR availability
    ocr_ok = test_ocr_availability()
    
    # Test NLP availability
    nlp_ok = test_nlp_availability()
    
    # Test disease detection (works with or without NLP)
    disease_ok = test_disease_detection()
    
    # Show summary
    show_feature_summary()
    
    # Final message
    logger.info("\n" + "=" * 70)
    logger.info("TEST COMPLETE")
    logger.info("=" * 70)
    
    if not ocr_ok:
        logger.info("\n⚠️  To enable OCR:")
        logger.info("  1. Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
        logger.info("  2. Install Poppler (for pdf2image)")
        logger.info("  3. pip install pytesseract pdf2image Pillow")
    
    if not nlp_ok:
        logger.info("\n⚠️  To enable advanced disease detection:")
        logger.info("  1. pip install spacy")
        logger.info("  2. python -m spacy download en_core_web_sm")
    
    if ocr_ok and nlp_ok:
        logger.info("\n🎉 All features are available!")
        logger.info("Your pipeline is ready with OCR and advanced disease detection.")
    
    logger.info("\n✓ Tests completed. Check logs above for details.")


if __name__ == '__main__':
    main()
