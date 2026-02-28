"""
Text Extraction from PDFs and HTML
Extracts clean text from PDFs using pdfplumber with OCR fallback for scanned PDFs.
Uses pytesseract and pdf2image for OCR when pdfplumber fails.
Removes scripts, styles, and other non-content elements from HTML.
"""

import os
import logging
from pathlib import Path
import pdfplumber
from bs4 import BeautifulSoup
from tqdm import tqdm

# OCR imports (optional - will gracefully degrade if not available)
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    
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
    
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extract text from PDF and HTML files for RAG pipeline.
    Includes OCR fallback for scanned PDFs.
    """
    
    def __init__(self, output_dir='processed/extracted_text', enable_ocr=True):
        """
        Initialize the text extractor.
        
        Args:
            output_dir: Directory to save extracted text files
            enable_ocr: Whether to use OCR for scanned PDFs (default: True)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_ocr = enable_ocr and OCR_AVAILABLE
        
        if enable_ocr and not OCR_AVAILABLE:
            logger.warning("OCR libraries not available. Install pytesseract and pdf2image for OCR support.")
            logger.warning("pip install pytesseract pdf2image Pillow")
    
    def extract_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file using pdfplumber with OCR fallback.
        If pdfplumber fails or extracts minimal text, uses OCR.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text as string or None if failed
        """
        try:
            pdf_path = Path(pdf_path)
            logger.info(f"Extracting text from PDF: {pdf_path.name}")
            
            text_content = []
            scanned_pages = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text from page
                    page_text = page.extract_text()
                    
                    if page_text and len(page_text.strip()) > 50:
                        # Good text extraction
                        text_content.append(page_text)
                    else:
                        # Possibly scanned page
                        logger.warning(f"Minimal text on page {page_num} of {pdf_path.name} - may be scanned")
                        scanned_pages.append(page_num)
                        if page_text:
                            text_content.append(page_text)
            
            # Check if we need OCR
            if not text_content or len(''.join(text_content).strip()) < 100:
                logger.warning(f"Insufficient text extracted from {pdf_path.name}")
                
                if self.enable_ocr:
                    logger.info(f"Attempting OCR extraction for {pdf_path.name}")
                    ocr_text = self._extract_with_ocr(pdf_path)
                    if ocr_text:
                        return ocr_text
                
                return None
            
            # If some pages are scanned, try OCR for those
            if scanned_pages and self.enable_ocr and len(scanned_pages) < 10:
                logger.info(f"Attempting OCR for {len(scanned_pages)} scanned pages")
                for page_num in scanned_pages:
                    ocr_text = self._extract_page_with_ocr(pdf_path, page_num)
                    if ocr_text:
                        # Replace or append the OCR text
                        if page_num <= len(text_content):
                            text_content[page_num - 1] = ocr_text
                        else:
                            text_content.append(ocr_text)
            
            # Join all pages with double newline
            full_text = '\n\n'.join(text_content)
            
            logger.info(f"Extracted {len(full_text)} characters from {pdf_path.name}")
            return full_text
            
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return None
    
    def _extract_with_ocr(self, pdf_path):
        """
        Extract text from entire PDF using OCR.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text as string or None if failed
        """
        if not self.enable_ocr:
            return None
        
        try:
            logger.info(f"Converting PDF to images for OCR: {pdf_path.name}")
            
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            text_content = []
            for i, image in enumerate(tqdm(images, desc="OCR processing"), 1):
                # Perform OCR on each image
                page_text = pytesseract.image_to_string(image)
                
                if page_text.strip():
                    text_content.append(page_text)
                    logger.debug(f"OCR extracted {len(page_text)} characters from page {i}")
            
            if text_content:
                full_text = '\n\n'.join(text_content)
                logger.info(f"OCR extracted {len(full_text)} characters from {pdf_path.name}")
                return full_text
            
            return None
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {pdf_path}: {e}")
            return None
    
    def _extract_page_with_ocr(self, pdf_path, page_num):
        """
        Extract text from a single page using OCR.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            
        Returns:
            Extracted text as string or None if failed
        """
        if not self.enable_ocr:
            return None
        
        try:
            # Convert single page to image
            images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=300)
            
            if images:
                page_text = pytesseract.image_to_string(images[0])
                if page_text.strip():
                    logger.debug(f"OCR extracted {len(page_text)} characters from page {page_num}")
                    return page_text
            
            return None
            
        except Exception as e:
            logger.error(f"OCR extraction failed for page {page_num} of {pdf_path}: {e}")
            return None
    
    def extract_from_html(self, html_path):
        """
        Extract clean text from an HTML file using BeautifulSoup.
        Removes scripts, styles, and navigation elements.
        
        Args:
            html_path: Path to HTML file
            
        Returns:
            Extracted text as string or None if failed
        """
        try:
            html_path = Path(html_path)
            logger.info(f"Extracting text from HTML: {html_path.name}")
            
            # Read HTML file
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 
                                'aside', 'form', 'button', 'iframe']):
                element.decompose()
            
            # Extract text
            text = soup.get_text(separator='\n', strip=True)
            
            if not text:
                logger.warning(f"No text extracted from {html_path.name}")
                return None
            
            logger.info(f"Extracted {len(text)} characters from {html_path.name}")
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract text from {html_path}: {e}")
            return None
    
    def save_extracted_text(self, text, output_filename):
        """
        Save extracted text to a file.
        
        Args:
            text: Text content to save
            output_filename: Name of output file
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            output_path = self.output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"Saved extracted text: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save text to {output_filename}: {e}")
            return None
    
    def process_directory(self, input_dir, file_extension):
        """
        Process all files of a given type in a directory.
        
        Args:
            input_dir: Directory containing input files
            file_extension: File extension to process ('.pdf' or '.html')
            
        Returns:
            List of successfully processed file paths
        """
        input_dir = Path(input_dir)
        processed_files = []
        
        # Find all files with the specified extension
        files = list(input_dir.glob(f'*{file_extension}'))
        
        if not files:
            logger.warning(f"No {file_extension} files found in {input_dir}")
            return processed_files
        
        logger.info(f"Processing {len(files)} {file_extension} files from {input_dir}")
        
        for file_path in tqdm(files, desc=f"Extracting {file_extension} files"):
            # Extract text based on file type
            if file_extension == '.pdf':
                text = self.extract_from_pdf(file_path)
            elif file_extension == '.html':
                text = self.extract_from_html(file_path)
            else:
                logger.error(f"Unsupported file extension: {file_extension}")
                continue
            
            if text:
                # Save with .txt extension
                output_filename = file_path.stem + '.txt'
                result = self.save_extracted_text(text, output_filename)
                
                if result:
                    processed_files.append(result)
        
        logger.info(f"Successfully processed {len(processed_files)}/{len(files)} files")
        return processed_files


def main():
    """
    Main execution function.
    """
    # Initialize extractor
    extractor = TextExtractor(output_dir='processed/extracted_text')
    
    # Process PDFs
    logger.info("=" * 50)
    logger.info("EXTRACTING TEXT FROM PDFs")
    logger.info("=" * 50)
    pdf_files = extractor.process_directory('raw/pdfs', '.pdf')
    
    # Process HTML files
    logger.info("=" * 50)
    logger.info("EXTRACTING TEXT FROM HTML")
    logger.info("=" * 50)
    html_files = extractor.process_directory('raw/html', '.html')
    
    # Summary
    total_processed = len(pdf_files) + len(html_files)
    logger.info("=" * 50)
    logger.info(f"EXTRACTION COMPLETE")
    logger.info(f"Total files processed: {total_processed}")
    logger.info(f"  - PDFs: {len(pdf_files)}")
    logger.info(f"  - HTML: {len(html_files)}")
    logger.info(f"Output directory: {extractor.output_dir}")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()
