"""
HTML Web Scraper for Agricultural Content
Scrapes publicly accessible HTML pages from agricultural institutions (UC IPM, FAO, etc.)
Respects polite scraping practices with user agents and delays.
"""

import os
import time
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
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
TIMEOUT = 30  # request timeout in seconds


class HTMLScraper:
    """
    Web scraper for agricultural HTML content with polite scraping practices.
    """
    
    def __init__(self, output_dir='raw/html', delay=REQUEST_DELAY, force=False):
        """
        Initialize the HTML scraper.
        
        Args:
            output_dir: Directory to save scraped HTML files
            delay: Delay between requests in seconds
            force: If True, re-download even if file exists
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.force = force
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def scrape_page(self, url, filename=None):
        """
        Scrape a single HTML page.
        
        Args:
            url: URL to scrape
            filename: Custom filename (optional, auto-generated from URL if not provided)
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Generate filename first to check if exists
            if filename is None:
                parsed_url = urlparse(url)
                filename = parsed_url.path.strip('/').replace('/', '_')
                if not filename:
                    filename = parsed_url.netloc.replace('.', '_')
                if not filename.endswith('.html'):
                    filename += '.html'
            
            output_path = self.output_dir / filename
            
            # Skip if file exists and not forcing re-download
            if output_path.exists() and not self.force:
                logger.info(f"⏭️  Skipping (already exists): {filename}")
                return output_path
            
            logger.info(f"Scraping: {url}")
            
            # Make request
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            
            logger.info(f"Saved: {output_path}")
            
            # Polite delay
            time.sleep(self.delay)
            
            return output_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return None
    
    def scrape_multiple(self, url_list):
        """
        Scrape multiple URLs.
        
        Args:
            url_list: List of tuples (url, filename) or just URLs
            
        Returns:
            List of successfully scraped file paths
        """
        scraped_files = []
        
        for item in tqdm(url_list, desc="Scraping HTML pages"):
            if isinstance(item, tuple):
                url, filename = item
            else:
                url, filename = item, None
            
            result = self.scrape_page(url, filename)
            if result:
                scraped_files.append(result)
        
        logger.info(f"Successfully scraped {len(scraped_files)}/{len(url_list)} pages")
        return scraped_files


def main(force=False):
    """
    Main execution function with example agricultural URLs.
    
    Args:
        force: If True, re-download files even if they exist
    """
    # Initialize scraper
    scraper = HTMLScraper(output_dir='raw/html', force=force)
    
    # Example URLs for tomato disease information
    # These are publicly accessible agricultural resources
    urls_to_scrape = [
    # =========================
    # UC IPM (Global – HTML)
    # =========================
        ('https://ipm.ucanr.edu/agriculture/tomato/', 'ucipm_tomato_index.html'),
        ('https://ipm.ucanr.edu/agriculture/tomato/late-blight/', 'ucipm_tomato_late_blight.html'),
        ('https://ipm.ucanr.edu/agriculture/tomato/early-blight/', 'ucipm_tomato_early_blight.html'),
        ('https://ipm.ucanr.edu/agriculture/tomato/bacterial-wilt/', 'ucipm_tomato_bacterial_wilt.html'),
        ('https://ipm.ucanr.edu/agriculture/tomato/fusarium-wilt/', 'ucipm_tomato_fusarium_wilt.html'),
        ('https://ipm.ucanr.edu/agriculture/tomato/septoria-leaf-spot/', 'ucipm_tomato_septoria_leaf_spot.html'),

        # =========================
        # FAO / ALiSEA (HTML pages, not PDFs)
        # =========================
        ('https://ckan.ali-sea.org/dataset/tomato-integrated-pest-managementan-ecological-guide', 'alisea_fao_tomato_ipm.html'),
        ('https://www.fao.org/plant-health/areas-of-work/integrated-pest-management/en/', 'fao_ipm_overview.html'),

        # =========================
        # PCAARRD / DOST (Philippines – HTML)
        # =========================
        ('https://www.pcaarrd.dost.gov.ph/index.php/quick-information-dispatch-qid-articles/pcaarrd-funded-program-to-increase-productivity-of-fresh-and-processing-tomato',
        'pcaarrd_tomato_productivity.html'),
        ('https://www.pcaarrd.dost.gov.ph/index.php/quick-information-dispatch-qid-articles/tomato-productivity-in-ilocos-region-to-be-addressed-with-integrated-crop-management',
        'pcaarrd_tomato_icm_ilocos.html'),

        # =========================
        # DA / ATI Philippines (HTML)
        # =========================
        ('https://ati2.da.gov.ph/ati-car/content/publications/adrian-chris-p-velasco/da-jica-mv2c-training-module-long-term-harvesting-tomato-and',
        'da_ati_tomato_training.html'),

        # =========================
        # WorldVeg / AVRDC (HTML)
        # =========================
        ('https://avrdc.org/collecting-disease-samples-in-the-philippines/',
        'worldveg_collecting_disease_samples_ph.html'),
        ('https://avrdc.org/farmer-field-days-on-integrated-pest-management-of-tomato-in-the-philippines/',
        'worldveg_ipm_field_days_ph.html'),

        # =========================
        # UPLB / Academic HTML pages
        # =========================
        ('https://www.ukdr.uplb.edu.ph/', 'uplb_ukdr_home.html'),

        # Add more HTML-only extension or university pages below
    ]

    
    logger.info(f"Starting HTML scraping of {len(urls_to_scrape)} pages")
    
    # Scrape all URLs
    scraped_files = scraper.scrape_multiple(urls_to_scrape)
    
    logger.info(f"Scraping complete. Files saved in: {scraper.output_dir}")
    logger.info(f"Total files: {len(scraped_files)}")


if __name__ == '__main__':
    main()
