"""
Pipeline Validator
Validates the output of the RAG pipeline to ensure data quality.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineValidator:
    """
    Validate RAG pipeline output for data quality and completeness.
    """
    
    def __init__(self, rag_file_path='processed/rag_json/rag_documents.json'):
        """
        Initialize validator.
        
        Args:
            rag_file_path: Path to RAG JSON file
        """
        self.rag_file_path = Path(rag_file_path)
        self.rag_data = None
        self.validation_results = {
            'file_exists': False,
            'valid_json': False,
            'has_documents': False,
            'total_documents': 0,
            'issues': [],
            'warnings': []
        }
    
    def load_data(self):
        """
        Load RAG JSON file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.rag_file_path.exists():
                self.validation_results['issues'].append(
                    f"File not found: {self.rag_file_path}"
                )
                return False
            
            self.validation_results['file_exists'] = True
            
            with open(self.rag_file_path, 'r', encoding='utf-8') as f:
                self.rag_data = json.load(f)
            
            self.validation_results['valid_json'] = True
            return True
            
        except json.JSONDecodeError as e:
            self.validation_results['issues'].append(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.validation_results['issues'].append(f"Failed to load file: {e}")
            return False
    
    def validate_structure(self):
        """
        Validate the structure of the RAG data.
        """
        if not self.rag_data:
            return
        
        # Check required top-level fields
        required_fields = ['version', 'created_at', 'total_documents', 'documents']
        for field in required_fields:
            if field not in self.rag_data:
                self.validation_results['issues'].append(
                    f"Missing required field: {field}"
                )
        
        # Check documents
        if 'documents' in self.rag_data:
            documents = self.rag_data['documents']
            
            if not isinstance(documents, list):
                self.validation_results['issues'].append(
                    "Documents field is not a list"
                )
                return
            
            if len(documents) == 0:
                self.validation_results['warnings'].append(
                    "No documents in the dataset"
                )
            else:
                self.validation_results['has_documents'] = True
                self.validation_results['total_documents'] = len(documents)
    
    def validate_documents(self):
        """
        Validate individual documents.
        """
        if not self.rag_data or 'documents' not in self.rag_data:
            return
        
        documents = self.rag_data['documents']
        
        # Track issues
        documents_without_id = 0
        documents_without_text = 0
        documents_without_metadata = 0
        empty_texts = 0
        duplicate_ids = set()
        seen_ids = set()
        
        # Required metadata fields
        required_metadata_fields = [
            'crop', 'disease', 'region', 'source', 
            'content_type', 'language'
        ]
        
        for i, doc in enumerate(documents):
            # Check ID
            if 'id' not in doc:
                documents_without_id += 1
            elif doc['id'] in seen_ids:
                duplicate_ids.add(doc['id'])
            else:
                seen_ids.add(doc['id'])
            
            # Check text
            if 'text' not in doc:
                documents_without_text += 1
            elif not doc['text'] or not doc['text'].strip():
                empty_texts += 1
            
            # Check metadata
            if 'metadata' not in doc:
                documents_without_metadata += 1
            else:
                metadata = doc['metadata']
                for field in required_metadata_fields:
                    if field not in metadata:
                        self.validation_results['warnings'].append(
                            f"Document {i} missing metadata field: {field}"
                        )
        
        # Report issues
        if documents_without_id > 0:
            self.validation_results['issues'].append(
                f"{documents_without_id} documents missing 'id' field"
            )
        
        if documents_without_text > 0:
            self.validation_results['issues'].append(
                f"{documents_without_text} documents missing 'text' field"
            )
        
        if documents_without_metadata > 0:
            self.validation_results['warnings'].append(
                f"{documents_without_metadata} documents missing 'metadata' field"
            )
        
        if empty_texts > 0:
            self.validation_results['warnings'].append(
                f"{empty_texts} documents have empty text"
            )
        
        if duplicate_ids:
            self.validation_results['warnings'].append(
                f"Found {len(duplicate_ids)} duplicate IDs"
            )
    
    def validate_metadata_quality(self):
        """
        Validate metadata quality and coverage.
        """
        if not self.rag_data or 'documents' not in self.rag_data:
            return
        
        documents = self.rag_data['documents']
        
        # Track metadata statistics
        diseases = set()
        sources = set()
        regions = set()
        content_types = set()
        
        unknown_disease_count = 0
        unknown_source_count = 0
        
        for doc in documents:
            if 'metadata' not in doc:
                continue
            
            metadata = doc['metadata']
            
            # Collect unique values
            if 'disease' in metadata:
                disease = metadata['disease']
                diseases.add(disease)
                if disease.lower() in ['unknown', 'general']:
                    unknown_disease_count += 1
            
            if 'source' in metadata:
                source = metadata['source']
                sources.add(source)
                if source.lower() == 'unknown':
                    unknown_source_count += 1
            
            if 'region' in metadata:
                regions.add(metadata['region'])
            
            if 'content_type' in metadata:
                content_types.add(metadata['content_type'])
        
        # Report findings
        logger.info(f"Unique diseases identified: {len(diseases)}")
        logger.info(f"Unique sources: {len(sources)}")
        logger.info(f"Unique regions: {len(regions)}")
        logger.info(f"Unique content types: {len(content_types)}")
        
        # Warnings for low metadata quality
        if unknown_disease_count > len(documents) * 0.5:
            self.validation_results['warnings'].append(
                f"High number of documents with unknown disease: {unknown_disease_count}/{len(documents)}"
            )
        
        if unknown_source_count > len(documents) * 0.3:
            self.validation_results['warnings'].append(
                f"High number of documents with unknown source: {unknown_source_count}/{len(documents)}"
            )
    
    def validate(self):
        """
        Run all validation checks.
        
        Returns:
            True if validation passed, False otherwise
        """
        logger.info("=" * 70)
        logger.info("VALIDATING RAG PIPELINE OUTPUT")
        logger.info("=" * 70)
        
        # Load data
        if not self.load_data():
            logger.error("Failed to load RAG data file")
            return False
        
        # Run validations
        self.validate_structure()
        self.validate_documents()
        self.validate_metadata_quality()
        
        # Print results
        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 70)
        
        logger.info(f"✓ File exists: {self.validation_results['file_exists']}")
        logger.info(f"✓ Valid JSON: {self.validation_results['valid_json']}")
        logger.info(f"✓ Has documents: {self.validation_results['has_documents']}")
        logger.info(f"✓ Total documents: {self.validation_results['total_documents']}")
        
        # Report issues
        if self.validation_results['issues']:
            logger.error("\n❌ ISSUES FOUND:")
            for issue in self.validation_results['issues']:
                logger.error(f"  - {issue}")
        
        # Report warnings
        if self.validation_results['warnings']:
            logger.warning("\n⚠️  WARNINGS:")
            for warning in self.validation_results['warnings']:
                logger.warning(f"  - {warning}")
        
        # Final verdict
        logger.info("\n" + "=" * 70)
        if self.validation_results['issues']:
            logger.error("VALIDATION FAILED ❌")
            logger.error("Please fix the issues above before using this data.")
            return False
        elif self.validation_results['warnings']:
            logger.warning("VALIDATION PASSED WITH WARNINGS ⚠️")
            logger.warning("Data is usable but may have quality issues.")
            return True
        else:
            logger.info("VALIDATION PASSED ✓")
            logger.info("Data is ready for use in RAG applications!")
            return True


def main():
    """
    Main execution function.
    """
    validator = PipelineValidator()
    success = validator.validate()
    
    if not success:
        exit(1)


if __name__ == '__main__':
    main()
