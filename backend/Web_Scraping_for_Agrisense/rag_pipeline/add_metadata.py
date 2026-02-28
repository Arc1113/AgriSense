"""
Metadata Enrichment and RAG JSON Exporter
Adds metadata to chunks and exports final RAG-ready JSON format.
Metadata includes: crop, disease, region, source, content_type, language.
Uses advanced disease detection with NLP and confidence scoring.
Output is compatible with LangChain, LlamaIndex, FAISS, and Chroma.
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from tqdm import tqdm

# Import disease detector
try:
    from disease_detector import get_disease_detector
    DISEASE_DETECTOR_AVAILABLE = True
except ImportError:
    DISEASE_DETECTOR_AVAILABLE = False
    logger.warning("Disease detector not available. Using fallback keyword matching.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetadataEnricher:
    """
    Enrich text chunks with metadata for RAG system.
    """
    
    # Disease keywords for content classification
    DISEASE_KEYWORDS = {
        'late_blight': ['late blight', 'phytophthora infestans', 'phytophthora'],
        'early_blight': ['early blight', 'alternaria solani', 'alternaria'],
        'bacterial_spot': ['bacterial spot', 'xanthomonas'],
        'bacterial_speck': ['bacterial speck', 'pseudomonas syringae'],
        'septoria_leaf_spot': ['septoria', 'septoria leaf spot'],
        'fusarium_wilt': ['fusarium wilt', 'fusarium oxysporum'],
        'verticillium_wilt': ['verticillium wilt', 'verticillium'],
        'powdery_mildew': ['powdery mildew', 'oidium', 'leveillula taurica'],
        'tomato_mosaic_virus': ['tomato mosaic virus', 'tomv', 'mosaic virus'],
        'tomato_yellow_leaf_curl': ['tomato yellow leaf curl', 'tylcv'],
        'anthracnose': ['anthracnose', 'colletotrichum'],
        'gray_mold': ['gray mold', 'grey mold', 'botrytis'],
    }
    
    # Content type keywords
    CONTENT_TYPE_KEYWORDS = {
        'symptoms': ['symptom', 'symptoms', 'signs', 'identification', 'appears', 'lesion', 'spots'],
        'treatment': ['treatment', 'control', 'manage', 'fungicide', 'pesticide', 'spray', 'application'],
        'prevention': ['prevent', 'prevention', 'avoid', 'resistant varieties', 'cultural practices', 'sanitation'],
        'general': []  # Default category
    }
    
    # Source inference patterns
    SOURCE_PATTERNS = {
        'FAO': ['fao', 'food and agriculture organization'],
        'UC IPM': ['ucipm', 'uc ipm', 'university of california', 'ipm.ucanr'],
        'PCAARRD': ['pcaarrd', 'philippine council'],
        'DA': ['department of agriculture', 'da.gov.ph', 'da-ph'],
        'UPLB': ['uplb', 'university of the philippines los baños', 'university of the philippines los banos'],
    }
    
    def __init__(self, output_dir='processed/rag_json', use_advanced_detection=True):
        """
        Initialize the metadata enricher.
        
        Args:
            output_dir: Directory to save RAG-ready JSON files
            use_advanced_detection: Use advanced NLP-based disease detection
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize disease detector
        self.use_advanced_detection = use_advanced_detection and DISEASE_DETECTOR_AVAILABLE
        if self.use_advanced_detection:
            self.disease_detector = get_disease_detector(use_nlp=True)
            logger.info("Using advanced disease detection with NLP")
        else:
            self.disease_detector = None
            if use_advanced_detection:
                logger.warning("Advanced disease detection not available. Using keyword matching.")
    
    def infer_disease(self, text, filename):
        """
        Infer disease from text content and filename using advanced detection.
        
        Args:
            text: Chunk text
            filename: Source filename
            
        Returns:
            Dictionary with disease info (name, confidence, all_detected)
        """
        if self.use_advanced_detection and self.disease_detector:
            # Use advanced disease detector
            detected_diseases = self.disease_detector.detect_diseases(text, filename)
            
            if detected_diseases:
                primary = detected_diseases[0]
                
                # Get all diseases with confidence > 0.3
                all_diseases = [
                    {'name': d['name'], 'confidence': d['confidence']}
                    for d in detected_diseases if d['confidence'] > 0.3
                ]
                
                return {
                    'name': primary['name'],
                    'scientific_name': primary['scientific_name'],
                    'confidence': primary['confidence'],
                    'all_detected': all_diseases
                }
        
        # Fallback to simple keyword matching
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Check text and filename for disease keywords
        for disease, keywords in self.DISEASE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in filename_lower:
                    return {
                        'name': disease.replace('_', ' ').title(),
                        'scientific_name': 'Unknown',
                        'confidence': 0.7 if keyword in text_lower else 0.5,
                        'all_detected': []
                    }
        
        return {
            'name': 'General',
            'scientific_name': 'N/A',
            'confidence': 0.0,
            'all_detected': []
        }
    
    def infer_content_type(self, text):
        """
        Infer content type from text.
        
        Args:
            text: Chunk text
            
        Returns:
            Content type (Symptoms, Treatment, Prevention, or General)
        """
        text_lower = text.lower()
        
        # Count keyword matches for each content type
        type_scores = {}
        for content_type, keywords in self.CONTENT_TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            type_scores[content_type] = score
        
        # Return type with highest score
        if max(type_scores.values()) > 0:
            return max(type_scores, key=type_scores.get).title()
        else:
            return 'General'
    
    def infer_source(self, filename, text):
        """
        Infer source organization from filename and text.
        
        Args:
            filename: Source filename
            text: Chunk text
            
        Returns:
            Source organization name
        """
        filename_lower = filename.lower()
        text_lower = text[:500].lower()  # Check first 500 chars of text
        
        # Check filename and text for source patterns
        for source, patterns in self.SOURCE_PATTERNS.items():
            for pattern in patterns:
                if pattern in filename_lower or pattern in text_lower:
                    return source
        
        return 'Unknown'
    
    def infer_region(self, filename, source):
        """
        Infer region (PH or Global) from filename and source.
        
        Args:
            filename: Source filename
            source: Source organization
            
        Returns:
            Region ('PH' or 'Global')
        """
        # Philippines-specific sources
        ph_sources = ['PCAARRD', 'DA', 'UPLB']
        
        if source in ph_sources:
            return 'PH'
        
        # Check filename for Philippines indicators
        ph_indicators = ['philippines', 'ph', 'filipino', 'manila', 'pcaarrd', 'uplb']
        filename_lower = filename.lower()
        
        for indicator in ph_indicators:
            if indicator in filename_lower:
                return 'PH'
        
        return 'Global'
    
    def enrich_chunk(self, chunk, filename):
        """
        Add metadata to a single chunk with enhanced disease detection.
        
        Args:
            chunk: Chunk dictionary with text and chunk_id
            filename: Source filename
            
        Returns:
            Enriched chunk with metadata
        """
        text = chunk.get('text', '')
        
        # Infer metadata
        disease_info = self.infer_disease(text, filename)
        content_type = self.infer_content_type(text)
        source = self.infer_source(filename, text)
        region = self.infer_region(filename, source)
        
        # Create enriched document
        enriched = {
            'id': chunk.get('chunk_id', f"{Path(filename).stem}_{hash(text) % 10000}"),
            'text': text,
            'metadata': {
                'crop': 'Tomato',
                'disease': disease_info['name'],
                'disease_scientific_name': disease_info.get('scientific_name', 'Unknown'),
                'disease_confidence': disease_info.get('confidence', 0.0),
                'region': region,
                'source': source,
                'content_type': content_type,
                'language': 'English',
                'source_file': filename,
                'token_count': chunk.get('token_count', 0),
                'created_at': datetime.now().isoformat()
            }
        }
        
        # Add all detected diseases if available
        if disease_info.get('all_detected'):
            enriched['metadata']['all_diseases_detected'] = disease_info['all_detected']
        
        return enriched
    
    def process_chunk_file(self, chunk_file_path):
        """
        Process a single chunk JSON file and enrich all chunks.
        
        Args:
            chunk_file_path: Path to chunk JSON file
            
        Returns:
            List of enriched chunks
        """
        try:
            chunk_file_path = Path(chunk_file_path)
            logger.info(f"Processing: {chunk_file_path.name}")
            
            # Read chunk file
            with open(chunk_file_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            # Extract source filename from chunks
            source_filename = chunks[0].get('source_file', chunk_file_path.stem) if chunks else chunk_file_path.stem
            
            # Enrich each chunk
            enriched_chunks = []
            for chunk in chunks:
                enriched = self.enrich_chunk(chunk, source_filename)
                enriched_chunks.append(enriched)
            
            logger.info(f"Enriched {len(enriched_chunks)} chunks from {chunk_file_path.name}")
            return enriched_chunks
            
        except Exception as e:
            logger.error(f"Failed to process {chunk_file_path}: {e}")
            return []
    
    def process_directory(self, chunks_dir):
        """
        Process all chunk files in a directory.
        
        Args:
            chunks_dir: Directory containing chunk JSON files
            
        Returns:
            List of all enriched chunks
        """
        chunks_dir = Path(chunks_dir)
        all_enriched_chunks = []
        
        # Find all chunk JSON files
        chunk_files = list(chunks_dir.glob('*_chunks.json'))
        
        if not chunk_files:
            logger.warning(f"No chunk files found in {chunks_dir}")
            return all_enriched_chunks
        
        logger.info(f"Processing {len(chunk_files)} chunk files from {chunks_dir}")
        
        for chunk_file in tqdm(chunk_files, desc="Enriching chunks"):
            enriched_chunks = self.process_chunk_file(chunk_file)
            all_enriched_chunks.extend(enriched_chunks)
        
        logger.info(f"Total enriched chunks: {len(all_enriched_chunks)}")
        return all_enriched_chunks
    
    def export_rag_json(self, enriched_chunks, output_filename='rag_documents.json'):
        """
        Export enriched chunks to RAG-ready JSON format.
        
        Args:
            enriched_chunks: List of enriched chunk dictionaries
            output_filename: Name of output file
            
        Returns:
            Path to exported file
        """
        try:
            output_path = self.output_dir / output_filename
            
            # Create RAG-ready structure
            rag_data = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'total_documents': len(enriched_chunks),
                'documents': enriched_chunks
            }
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(rag_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported RAG data to: {output_path}")
            logger.info(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export RAG JSON: {e}")
            return None
    
    def generate_statistics(self, enriched_chunks):
        """
        Generate statistics about the enriched dataset.
        
        Args:
            enriched_chunks: List of enriched chunks
            
        Returns:
            Dictionary of statistics
        """
        if not enriched_chunks:
            return {}
        
        stats = {
            'total_documents': len(enriched_chunks),
            'diseases': {},
            'content_types': {},
            'sources': {},
            'regions': {},
            'avg_token_count': 0
        }
        
        total_tokens = 0
        
        for chunk in enriched_chunks:
            metadata = chunk.get('metadata', {})
            
            # Count diseases
            disease = metadata.get('disease', 'Unknown')
            stats['diseases'][disease] = stats['diseases'].get(disease, 0) + 1
            
            # Count content types
            content_type = metadata.get('content_type', 'Unknown')
            stats['content_types'][content_type] = stats['content_types'].get(content_type, 0) + 1
            
            # Count sources
            source = metadata.get('source', 'Unknown')
            stats['sources'][source] = stats['sources'].get(source, 0) + 1
            
            # Count regions
            region = metadata.get('region', 'Unknown')
            stats['regions'][region] = stats['regions'].get(region, 0) + 1
            
            # Sum tokens
            total_tokens += metadata.get('token_count', 0)
        
        stats['avg_token_count'] = total_tokens / len(enriched_chunks) if enriched_chunks else 0
        
        return stats


def main():
    """
    Main execution function.
    """
    # Initialize enricher
    enricher = MetadataEnricher(output_dir='processed/rag_json')
    
    # Process all chunk files
    logger.info("=" * 50)
    logger.info("ENRICHING CHUNKS WITH METADATA")
    logger.info("=" * 50)
    
    enriched_chunks = enricher.process_directory('processed/chunks')
    
    if not enriched_chunks:
        logger.error("No chunks to process. Please run previous pipeline steps first.")
        return
    
    # Export to RAG-ready JSON
    logger.info("=" * 50)
    logger.info("EXPORTING RAG-READY JSON")
    logger.info("=" * 50)
    
    output_file = enricher.export_rag_json(enriched_chunks)
    
    # Generate and display statistics
    stats = enricher.generate_statistics(enriched_chunks)
    
    logger.info("=" * 50)
    logger.info("DATASET STATISTICS")
    logger.info("=" * 50)
    logger.info(f"Total documents: {stats.get('total_documents', 0)}")
    logger.info(f"Average tokens per chunk: {stats.get('avg_token_count', 0):.1f}")
    logger.info("")
    logger.info("Diseases:")
    for disease, count in sorted(stats.get('diseases', {}).items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {disease}: {count}")
    logger.info("")
    logger.info("Content Types:")
    for ctype, count in sorted(stats.get('content_types', {}).items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {ctype}: {count}")
    logger.info("")
    logger.info("Sources:")
    for source, count in sorted(stats.get('sources', {}).items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {source}: {count}")
    logger.info("")
    logger.info("Regions:")
    for region, count in sorted(stats.get('regions', {}).items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {region}: {count}")
    logger.info("=" * 50)
    logger.info("PIPELINE COMPLETE!")
    logger.info(f"RAG-ready data saved to: {output_file}")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()
