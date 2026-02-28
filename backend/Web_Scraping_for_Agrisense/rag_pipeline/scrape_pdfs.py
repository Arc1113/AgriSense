"""
PDF Downloader for Agricultural Documents
Downloads publicly available PDF manuals from agricultural institutions (FAO, PCAARRD, DA, etc.)
Respects polite scraping practices with user agents and delays.
"""

import os
import time
import logging
from pathlib import Path
from urllib.parse import urlparse
import requests
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Polite scraping configuration
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 (Educational Agricultural Research Bot)'
REQUEST_DELAY = 2  # seconds between requests
TIMEOUT = 60  # request timeout in seconds (longer for PDFs)
CHUNK_SIZE = 8192  # Download chunk size in bytes


class PDFDownloader:
    """
    PDF downloader for agricultural documents with polite scraping practices.
    """
    
    def __init__(self, output_dir='raw/pdfs', delay=REQUEST_DELAY, force=False):
        """
        Initialize the PDF downloader.
        
        Args:
            output_dir: Directory to save downloaded PDFs
            delay: Delay between requests in seconds
            force: If True, re-download even if file exists
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.force = force
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def download_pdf(self, url, filename=None):
        """
        Download a single PDF file.
        
        Args:
            url: URL of the PDF to download
            filename: Custom filename (optional, auto-generated from URL if not provided)
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Generate filename first to check if exists
            if filename is None:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                if not filename or not filename.endswith('.pdf'):
                    filename = parsed_url.path.strip('/').replace('/', '_') + '.pdf'
            
            # Ensure .pdf extension
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            output_path = self.output_dir / filename
            
            # Skip if file exists and not forcing re-download
            if output_path.exists() and not self.force:
                logger.info(f"⏭️  Skipping (already exists): {filename}")
                return output_path
            
            logger.info(f"Downloading PDF: {url}")
            
            # Make request with streaming
            response = self.session.get(url, timeout=TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Verify content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type:
                logger.warning(f"URL may not be a PDF (Content-Type: {content_type}): {url}")
            
            # Save to file with progress bar
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as pbar:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
            
            logger.info(f"Saved: {output_path} ({os.path.getsize(output_path)} bytes)")
            
            # Polite delay
            time.sleep(self.delay)
            
            return output_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            return None
    
    def download_multiple(self, url_list):
        """
        Download multiple PDF files.
        
        Args:
            url_list: List of tuples (url, filename) or just URLs
            
        Returns:
            List of successfully downloaded file paths
        """
        downloaded_files = []
        
        logger.info(f"Starting download of {len(url_list)} PDFs")
        
        for item in url_list:
            if isinstance(item, tuple):
                url, filename = item
            else:
                url, filename = item, None
            
            result = self.download_pdf(url, filename)
            if result:
                downloaded_files.append(result)
        
        logger.info(f"Successfully downloaded {len(downloaded_files)}/{len(url_list)} PDFs")
        return downloaded_files


def main(force=False):
    """
    Main execution function with example agricultural PDF URLs.
    
    Args:
        force: If True, re-download files even if they exist
    """
    # Initialize downloader
    downloader = PDFDownloader(output_dir='raw/pdfs', force=force)
    
    # Example URLs for publicly available agricultural PDFs
    # These should be direct PDF links from official agricultural institutions
    # PDF download list (url, filename)
    pdfs_to_download = [
        # FAO — Tomato Integrated Pest Management (ecological guide)
        ('https://openknowledge.fao.org/server/api/core/bitstreams/79f188d5-64cf-49a0-b924-47bc7a184eb5/content',
        'fao_tomato_ipm_2010.pdf'),

        # AVRDC / WorldVeg — Field-grown Tomato Production Guide (South Asia)
        ('https://avrdc.org/download/project-support/v4pp/training-trainers/1-5-GAP/Field-grown-tomato-production-guide_South-Asia.pdf',
        'avrdc_field_grown_tomato_production_guide_south_asia.pdf'),

        # WorldVeg / AVRDC — The Tomato Collection (catalog / technical PDF)
        ('https://worldveg.tind.io/record/56152/files/e12516.pdf',
        'worldveg_tomato_collection_e12516.pdf'),

        # Department of Agriculture / ATI (Philippines) — Techno Guide on Organic Tomato (regional PDF)
        ('https://ati2.da.gov.ph/ati-7/content/sites/default/files/users/user16/Techno%20guide%20on%20Tomato_Final.pdf',
        'da_ati_techno_guide_organic_tomato.pdf'),

        # Department of Agriculture (Philippines) — Investment Guide for Tomato
        ('https://www.da.gov.ph/wp-content/uploads/2021/04/Investment-Guide-for-Tomato.pdf',
        'da_investment_guide_for_tomato.pdf'),

        # Regional DA (Cagayan Valley) — Tomato Production Guide (useful local production practices)
        ('https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Tomato.pdf',
        'da_cagayanvalley_tomato_production_guide.pdf'),

        # UPLB / UKDR — Field assessment / tomato production guide (PDF)
        ('https://www.ukdr.uplb.edu.ph/cgi/viewcontent.cgi?article=1134&context=pas',
        'uplb_tomato_field_assessment.pdf'),
    ]

    
    if not pdfs_to_download:
        logger.warning("No PDF URLs configured. Please add URLs to the pdfs_to_download list.")
        logger.info("Example format: ('https://example.org/document.pdf', 'custom_name.pdf')")
        return
    
    # Download all PDFs
    downloaded_files = downloader.download_multiple(pdfs_to_download)
    
    logger.info(f"Download complete. Files saved in: {downloader.output_dir}")
    logger.info(f"Total files: {len(downloaded_files)}")


if __name__ == '__main__':
    main()
