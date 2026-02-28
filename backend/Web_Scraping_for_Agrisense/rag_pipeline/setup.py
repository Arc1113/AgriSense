"""
Quick Setup Script
Helps users set up the pipeline environment and verify installation.
"""

import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """
    Check if Python version is compatible.
    """
    logger.info("Checking Python version...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        logger.error(f"Python 3.7+ required. Current: {version.major}.{version.minor}")
        return False
    
    logger.info(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_requirements():
    """
    Install required packages from requirements.txt
    """
    logger.info("\nInstalling requirements...")
    
    try:
        # Navigate to parent directory to find requirements.txt
        req_file = Path(__file__).parent.parent / 'requirements.txt'
        
        if not req_file.exists():
            logger.error(f"requirements.txt not found at: {req_file}")
            return False
        
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', str(req_file)
        ])
        
        logger.info("✓ Requirements installed")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install requirements: {e}")
        return False


def download_nltk_data():
    """
    Download required NLTK data.
    """
    logger.info("\nDownloading NLTK data...")
    
    try:
        import nltk
        
        # Download required NLTK datasets
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        
        logger.info("✓ NLTK data downloaded")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download NLTK data: {e}")
        return False


def download_spacy_model():
    """
    Download required spaCy model.
    """
    logger.info("\nDownloading spaCy model...")
    
    try:
        import spacy
        
        # Check if model is already installed
        try:
            nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model already installed")
            return True
        except OSError:
            pass
        
        # Download model
        logger.info("  Downloading en_core_web_sm (this may take a minute)...")
        subprocess.check_call([
            sys.executable, '-m', 'spacy', 'download', 'en_core_web_sm'
        ])
        
        logger.info("✓ spaCy model downloaded")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to download spaCy model: {e}")
        logger.warning("  Advanced disease detection will use fallback mode")
        return True  # Not critical


def check_system_dependencies():
    """
    Check for system-level dependencies (Tesseract, Poppler).
    """
    logger.info("\nChecking system dependencies...")
    
    all_ok = True
    
    # Check Tesseract
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("  ✓ Tesseract OCR found")
        else:
            raise Exception("Tesseract check failed")
    except Exception:
        logger.warning("  ✗ Tesseract OCR not found (OCR features will be disabled)")
        logger.warning("    Install: https://github.com/UB-Mannheim/tesseract/wiki")
        all_ok = False
    
    # Check Poppler (pdf2image dependency)
    try:
        # Try to import pdf2image and see if it works
        from pdf2image import convert_from_path
        logger.info("  ✓ Poppler (pdf2image) available")
    except Exception:
        logger.warning("  ✗ Poppler not found (OCR features will be disabled)")
        logger.warning("    Windows: http://blog.alivate.com.au/poppler-windows/")
        logger.warning("    Linux: sudo apt-get install poppler-utils")
        logger.warning("    Mac: brew install poppler")
        all_ok = False
    
    if not all_ok:
        logger.warning("\n  ⚠️  Some system dependencies missing")
        logger.warning("  Pipeline will work but OCR features will be disabled")
    else:
        logger.info("✓ All system dependencies found")
    
    return True  # Not critical, continue anyway


def verify_imports():
    """
    Verify that all required modules can be imported.
    """
    logger.info("\nVerifying imports...")
    
    core_modules = [
        'requests',
        'bs4',
        'pdfplumber',
        'nltk',
        'tqdm'
    ]
    
    optional_modules = [
        ('pytesseract', 'OCR support'),
        ('pdf2image', 'OCR support'),
        ('spacy', 'Advanced disease detection')
    ]
    
    failed_imports = []
    
    # Check core modules
    for module in core_modules:
        try:
            __import__(module)
            logger.info(f"  ✓ {module}")
        except ImportError:
            logger.error(f"  ✗ {module}")
            failed_imports.append(module)
    
    # Check optional modules
    for module, purpose in optional_modules:
        try:
            __import__(module)
            logger.info(f"  ✓ {module} ({purpose})")
        except ImportError:
            logger.warning(f"  ○ {module} (optional - {purpose})")
    
    if failed_imports:
        logger.error(f"\nFailed to import: {', '.join(failed_imports)}")
        return False
    
    logger.info("✓ All core modules imported successfully")
    return True


def verify_directory_structure():
    """
    Verify that required directories exist.
    """
    logger.info("\nVerifying directory structure...")
    
    base_dir = Path(__file__).parent
    
    required_dirs = [
        'raw/pdfs',
        'raw/html',
        'processed/extracted_text',
        'processed/cleaned_text',
        'processed/chunks',
        'processed/rag_json'
    ]
    
    all_exist = True
    
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            logger.info(f"  ✓ {dir_path}")
        else:
            logger.warning(f"  ✗ {dir_path} (will be created automatically)")
            all_exist = False
    
    if all_exist:
        logger.info("✓ All directories exist")
    else:
        logger.info("ℹ Some directories missing but will be created during pipeline run")
    
    return True


def print_next_steps():
    """
    Print instructions for next steps.
    """
    logger.info("\n" + "=" * 70)
    logger.info("SETUP COMPLETE! 🎉")
    logger.info("=" * 70)
    logger.info("\nNext steps:")
    logger.info("1. Configure data sources:")
    logger.info("   - Edit scrape_html.py to add HTML URLs")
    logger.info("   - Edit scrape_pdfs.py to add PDF URLs")
    logger.info("")
    logger.info("2. Run the pipeline:")
    logger.info("   python run_pipeline.py")
    logger.info("")
    logger.info("3. Or run individual steps:")
    logger.info("   python scrape_html.py")
    logger.info("   python scrape_pdfs.py")
    logger.info("   python extract_text.py")
    logger.info("   python clean_text.py")
    logger.info("   python chunk_text.py")
    logger.info("   python add_metadata.py")
    logger.info("")
    logger.info("4. Validate output:")
    logger.info("   python validate_pipeline.py")
    logger.info("")
    logger.info("5. See example usage:")
    logger.info("   python example_usage.py")
    logger.info("=" * 70)


def main():
    """
    Main setup function.
    """
    logger.info("=" * 70)
    logger.info("RAG PIPELINE SETUP")
    logger.info("=" * 70)
    
    # Run all checks
    checks = [
        ("Python version", check_python_version),
        ("Install requirements", install_requirements),
        ("Download NLTK data", download_nltk_data),
        ("Download spaCy model", download_spacy_model),
        ("Check system dependencies", check_system_dependencies),
        ("Verify imports", verify_imports),
        ("Verify directories", verify_directory_structure),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
                logger.error(f"✗ {check_name} failed")
        except Exception as e:
            logger.error(f"✗ {check_name} failed with error: {e}")
            all_passed = False
    
    # Print results
    if all_passed:
        print_next_steps()
        return True
    else:
        logger.error("\n" + "=" * 70)
        logger.error("SETUP FAILED ❌")
        logger.error("=" * 70)
        logger.error("Please fix the errors above and run setup again.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
