"""
Master Pipeline Script
Orchestrates the complete RAG data preparation pipeline.
Runs all steps in sequence: scrape -> extract -> clean -> chunk -> enrich -> export.
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import pipeline modules
import scrape_html
import scrape_pdfs
import extract_text
import clean_text
import chunk_text
import add_metadata
import convert_to_markdown

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


def run_pipeline(skip_scraping=False, force_rescrape=False):
    """
    Run the complete RAG data preparation pipeline.
    
    Args:
        skip_scraping: If True, skip scraping steps (useful if you already have raw data)
        force_rescrape: If True, re-download files even if they exist
    """
    logger.info("=" * 70)
    logger.info("STARTING RAG DATA PREPARATION PIPELINE")
    logger.info("=" * 70)
    
    try:
        # Step 1: Scrape HTML pages
        if not skip_scraping:
            logger.info("\n" + "=" * 70)
            logger.info("STEP 1: SCRAPING HTML PAGES")
            if force_rescrape:
                logger.info("Force mode: Re-downloading all files")
            logger.info("=" * 70)
            scrape_html.main(force=force_rescrape)
        else:
            logger.info("Skipping HTML scraping (skip_scraping=True)")
        
        # Step 2: Download PDFs
        if not skip_scraping:
            logger.info("\n" + "=" * 70)
            logger.info("STEP 2: DOWNLOADING PDFs")
            if force_rescrape:
                logger.info("Force mode: Re-downloading all files")
            logger.info("=" * 70)
            scrape_pdfs.main(force=force_rescrape)
        else:
            logger.info("Skipping PDF downloading (skip_scraping=True)")
        
        # Step 3: Extract text from PDFs and HTML
        logger.info("\n" + "=" * 70)
        logger.info("STEP 3: EXTRACTING TEXT")
        logger.info("=" * 70)
        extract_text.main()
        
        # Step 4: Clean extracted text
        logger.info("\n" + "=" * 70)
        logger.info("STEP 4: CLEANING TEXT")
        logger.info("=" * 70)
        clean_text.main()
        
        # Step 5: Chunk text for RAG
        logger.info("\n" + "=" * 70)
        logger.info("STEP 5: CHUNKING TEXT")
        logger.info("=" * 70)
        chunk_text.main()
        
        # Step 6: Add metadata and export RAG JSON (legacy format)
        logger.info("\n" + "=" * 70)
        logger.info("STEP 6: ENRICHING WITH METADATA & EXPORTING (Legacy JSON)")
        logger.info("=" * 70)
        add_metadata.main()
        
        # Step 7: Convert to Markdown knowledge base (Industry Standard)
        logger.info("\n" + "=" * 70)
        logger.info("STEP 7: CONVERTING TO MARKDOWN KNOWLEDGE BASE (Industry Standard)")
        logger.info("=" * 70)
        convert_to_markdown.convert_all()
        
        # Success message
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info("Legacy JSON: processed/rag_json/rag_documents.json")
        logger.info("Markdown KB: processed/markdown_kb/*.md  (Industry Standard)")
        logger.info("")
        logger.info("Next: Run 'python init_vector_store.py --rebuild --test' from backend/")
        logger.info("This will build the vector store with header-aware chunking + reranking")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"\n{'=' * 70}")
        logger.error(f"PIPELINE FAILED: {e}")
        logger.error(f"{'=' * 70}")
        raise


def main():
    """
    Main entry point with command-line options.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='RAG Data Preparation Pipeline for Tomato Disease Treatment'
    )
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Skip web scraping steps (use if you already have raw data)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download of files even if they already exist'
    )
    
    args = parser.parse_args()
    
    run_pipeline(skip_scraping=args.skip_scraping, force_rescrape=args.force)


if __name__ == '__main__':
    main()
