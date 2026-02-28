"""
Text Cleaning and Normalization
Cleans extracted text by removing page numbers, headers, excessive whitespace,
and normalizing spacing and line breaks for RAG processing.
"""

import os
import re
import logging
from pathlib import Path
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Clean and normalize extracted text for RAG pipeline.
    """
    
    def __init__(self, output_dir='processed/cleaned_text'):
        """
        Initialize the text cleaner.
        
        Args:
            output_dir: Directory to save cleaned text files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def remove_page_numbers(self, text):
        """
        Remove common page number patterns.
        
        Args:
            text: Input text
            
        Returns:
            Text with page numbers removed
        """
        # Pattern: Page X, Page X of Y, standalone numbers at start/end of lines
        patterns = [
            r'^\s*Page\s+\d+\s*$',  # "Page 5"
            r'^\s*Page\s+\d+\s+of\s+\d+\s*$',  # "Page 5 of 20"
            r'^\s*\d+\s*$',  # Standalone numbers
            r'^\s*-\s*\d+\s*-\s*$',  # "- 5 -"
            r'^\s*\[\s*\d+\s*\]\s*$',  # "[5]"
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            is_page_number = False
            for pattern in patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    is_page_number = True
                    break
            
            if not is_page_number:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def remove_headers_footers(self, text):
        """
        Remove repeated headers and footers that appear on multiple pages.
        
        Args:
            text: Input text
            
        Returns:
            Text with headers/footers removed
        """
        lines = text.split('\n')
        
        # Find lines that appear more than 3 times (likely headers/footers)
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) > 5:  # Ignore very short lines
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        # Identify repeated lines
        repeated_lines = {line for line, count in line_counts.items() if count > 3}
        
        # Remove repeated lines
        cleaned_lines = [
            line for line in lines 
            if line.strip() not in repeated_lines
        ]
        
        return '\n'.join(cleaned_lines)
    
    def normalize_whitespace(self, text):
        """
        Normalize whitespace: remove excessive spaces, tabs, and blank lines.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace multiple newlines with max 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove spaces at start/end of lines
        lines = [line.strip() for line in text.split('\n')]
        
        # Remove empty lines at start and end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def remove_special_characters(self, text):
        """
        Remove or replace special characters that may interfere with processing.
        
        Args:
            text: Input text
            
        Returns:
            Text with special characters handled
        """
        # Replace common unicode characters
        replacements = {
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2026': '...',  # Ellipsis
            '\xa0': ' ',  # Non-breaking space
            '\t': ' ',  # Tab
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def remove_urls(self, text):
        """
        Remove URLs from text (optional, can be disabled if URLs are important).
        
        Args:
            text: Input text
            
        Returns:
            Text with URLs removed
        """
        # Remove http/https URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove www URLs
        text = re.sub(r'www\.\S+', '', text)
        
        return text
    
    def fix_line_breaks(self, text):
        """
        Fix awkward line breaks that split sentences incorrectly.
        
        Args:
            text: Input text
            
        Returns:
            Text with fixed line breaks
        """
        lines = text.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            current_line = lines[i].strip()
            
            # If current line doesn't end with sentence-ending punctuation
            # and next line exists and doesn't start with capital letter,
            # merge them
            if (i + 1 < len(lines) and 
                current_line and 
                not current_line[-1] in '.!?:' and
                lines[i + 1].strip() and
                not lines[i + 1].strip()[0].isupper()):
                
                # Merge with next line
                merged = current_line + ' ' + lines[i + 1].strip()
                fixed_lines.append(merged)
                i += 2
            else:
                fixed_lines.append(current_line)
                i += 1
        
        return '\n'.join(fixed_lines)
    
    def clean_text(self, text):
        """
        Apply all cleaning operations to text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return text
        
        # Apply cleaning steps in sequence
        text = self.remove_special_characters(text)
        text = self.remove_page_numbers(text)
        text = self.remove_headers_footers(text)
        text = self.remove_urls(text)
        text = self.fix_line_breaks(text)
        text = self.normalize_whitespace(text)
        
        return text
    
    def process_file(self, input_path):
        """
        Clean a single text file.
        
        Args:
            input_path: Path to input text file
            
        Returns:
            Path to cleaned file or None if failed
        """
        try:
            input_path = Path(input_path)
            logger.info(f"Cleaning: {input_path.name}")
            
            # Read input file
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Clean text
            cleaned_text = self.clean_text(text)
            
            if not cleaned_text:
                logger.warning(f"No text remaining after cleaning: {input_path.name}")
                return None
            
            # Save cleaned text
            output_path = self.output_dir / input_path.name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            logger.info(f"Saved cleaned text: {output_path.name}")
            logger.info(f"  Original: {len(text)} chars -> Cleaned: {len(cleaned_text)} chars")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to clean {input_path}: {e}")
            return None
    
    def process_directory(self, input_dir):
        """
        Clean all text files in a directory.
        
        Args:
            input_dir: Directory containing extracted text files
            
        Returns:
            List of successfully processed file paths
        """
        input_dir = Path(input_dir)
        processed_files = []
        
        # Find all .txt files
        files = list(input_dir.glob('*.txt'))
        
        if not files:
            logger.warning(f"No .txt files found in {input_dir}")
            return processed_files
        
        logger.info(f"Cleaning {len(files)} text files from {input_dir}")
        
        for file_path in tqdm(files, desc="Cleaning text files"):
            result = self.process_file(file_path)
            
            if result:
                processed_files.append(result)
        
        logger.info(f"Successfully cleaned {len(processed_files)}/{len(files)} files")
        return processed_files


def main():
    """
    Main execution function.
    """
    # Initialize cleaner
    cleaner = TextCleaner(output_dir='processed/cleaned_text')
    
    # Process all extracted text files
    logger.info("=" * 50)
    logger.info("CLEANING EXTRACTED TEXT")
    logger.info("=" * 50)
    
    cleaned_files = cleaner.process_directory('processed/extracted_text')
    
    # Summary
    logger.info("=" * 50)
    logger.info(f"CLEANING COMPLETE")
    logger.info(f"Total files cleaned: {len(cleaned_files)}")
    logger.info(f"Output directory: {cleaner.output_dir}")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()
