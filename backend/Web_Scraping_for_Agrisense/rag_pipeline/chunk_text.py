"""
Text Chunking for RAG
Chunks cleaned text into ~500-token chunks using sentence-based chunking with overlap.
Uses NLTK for sentence tokenization to preserve semantic boundaries.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict
import nltk
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chunking configuration
TARGET_CHUNK_SIZE = 500  # Target tokens per chunk
MIN_CHUNK_SIZE = 100  # Minimum tokens per chunk
OVERLAP_SIZE = 100  # Overlap between chunks in tokens
APPROX_TOKENS_PER_CHAR = 0.25  # Rough approximation: 4 chars = 1 token


class TextChunker:
    """
    Chunk text into overlapping segments for RAG pipeline.
    Uses sentence boundaries to maintain semantic coherence.
    """
    
    def __init__(self, output_dir='processed/chunks',
                 target_chunk_size=TARGET_CHUNK_SIZE,
                 overlap_size=OVERLAP_SIZE):
        """
        Initialize the text chunker.
        
        Args:
            output_dir: Directory to save chunked text files
            target_chunk_size: Target size of each chunk in tokens
            overlap_size: Overlap between chunks in tokens
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size
        
        # Download required NLTK data
        self._setup_nltk()
    
    def _setup_nltk(self):
        """
        Download required NLTK data files.
        """
        # Try both punkt formats (newer punkt_tab and legacy punkt)
        punkt_available = False
        
        try:
            nltk.data.find('tokenizers/punkt_tab')
            punkt_available = True
        except (LookupError, OSError):
            try:
                logger.info("Downloading NLTK punkt_tab tokenizer...")
                nltk.download('punkt_tab', quiet=True)
                punkt_available = True
            except:
                pass
        
        if not punkt_available:
            try:
                nltk.data.find('tokenizers/punkt')
                punkt_available = True
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)
    
    def estimate_tokens(self, text):
        """
        Estimate the number of tokens in text.
        Uses a rough approximation of 4 characters per token.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        return int(len(text) * APPROX_TOKENS_PER_CHAR)
    
    def split_into_sentences(self, text):
        """
        Split text into sentences using NLTK.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        try:
            sentences = nltk.sent_tokenize(text)
            return sentences
        except Exception as e:
            logger.warning(f"NLTK sentence tokenization failed: {e}. Falling back to simple split.")
            # Fallback: split on period followed by space
            return [s.strip() + '.' for s in text.split('. ') if s.strip()]
    
    def create_chunks(self, text, source_filename):
        """
        Create overlapping chunks from text using sentence boundaries.
        
        Args:
            text: Cleaned text to chunk
            source_filename: Original filename for reference
            
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            logger.warning(f"Empty text for {source_filename}")
            return []
        
        # Split into sentences
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            logger.warning(f"No sentences found in {source_filename}")
            return []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_id = 0
        
        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            
            # If adding this sentence exceeds target size, save current chunk
            if current_tokens + sentence_tokens > self.target_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'chunk_id': f"{Path(source_filename).stem}_chunk_{chunk_id}",
                    'text': chunk_text,
                    'token_count': current_tokens,
                    'source_file': source_filename
                })
                
                # Start new chunk with overlap
                # Keep last few sentences for overlap
                overlap_sentences = []
                overlap_tokens = 0
                
                for sent in reversed(current_chunk):
                    sent_tokens = self.estimate_tokens(sent)
                    if overlap_tokens + sent_tokens <= self.overlap_size:
                        overlap_sentences.insert(0, sent)
                        overlap_tokens += sent_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
                chunk_id += 1
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Save final chunk if it meets minimum size
        if current_chunk and current_tokens >= MIN_CHUNK_SIZE:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'chunk_id': f"{Path(source_filename).stem}_chunk_{chunk_id}",
                'text': chunk_text,
                'token_count': current_tokens,
                'source_file': source_filename
            })
        
        logger.info(f"Created {len(chunks)} chunks from {source_filename}")
        return chunks
    
    def process_file(self, input_path):
        """
        Chunk a single text file.
        
        Args:
            input_path: Path to input text file
            
        Returns:
            List of chunk dictionaries
        """
        try:
            input_path = Path(input_path)
            logger.info(f"Chunking: {input_path.name}")
            
            # Read input file
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Create chunks
            chunks = self.create_chunks(text, input_path.name)
            
            # Save chunks to JSON file
            if chunks:
                output_path = self.output_dir / f"{input_path.stem}_chunks.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved {len(chunks)} chunks to: {output_path.name}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk {input_path}: {e}")
            return []
    
    def process_directory(self, input_dir):
        """
        Chunk all text files in a directory.
        
        Args:
            input_dir: Directory containing cleaned text files
            
        Returns:
            Dictionary mapping filenames to their chunks
        """
        input_dir = Path(input_dir)
        all_chunks = {}
        
        # Find all .txt files
        files = list(input_dir.glob('*.txt'))
        
        if not files:
            logger.warning(f"No .txt files found in {input_dir}")
            return all_chunks
        
        logger.info(f"Chunking {len(files)} text files from {input_dir}")
        
        total_chunks = 0
        for file_path in tqdm(files, desc="Chunking text files"):
            chunks = self.process_file(file_path)
            
            if chunks:
                all_chunks[file_path.name] = chunks
                total_chunks += len(chunks)
        
        logger.info(f"Successfully created {total_chunks} chunks from {len(all_chunks)} files")
        return all_chunks


def main():
    """
    Main execution function.
    """
    # Initialize chunker
    chunker = TextChunker(
        output_dir='processed/chunks',
        target_chunk_size=TARGET_CHUNK_SIZE,
        overlap_size=OVERLAP_SIZE
    )
    
    # Process all cleaned text files
    logger.info("=" * 50)
    logger.info("CHUNKING TEXT FOR RAG")
    logger.info(f"Target chunk size: {TARGET_CHUNK_SIZE} tokens")
    logger.info(f"Overlap size: {OVERLAP_SIZE} tokens")
    logger.info("=" * 50)
    
    all_chunks = chunker.process_directory('processed/cleaned_text')
    
    # Calculate statistics
    total_chunks = sum(len(chunks) for chunks in all_chunks.values())
    if total_chunks > 0:
        avg_tokens = sum(
            chunk['token_count'] 
            for chunks in all_chunks.values() 
            for chunk in chunks
        ) / total_chunks
    else:
        avg_tokens = 0
    
    # Summary
    logger.info("=" * 50)
    logger.info(f"CHUNKING COMPLETE")
    logger.info(f"Total files processed: {len(all_chunks)}")
    logger.info(f"Total chunks created: {total_chunks}")
    logger.info(f"Average tokens per chunk: {avg_tokens:.1f}")
    logger.info(f"Output directory: {chunker.output_dir}")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()
