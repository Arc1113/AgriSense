"""
Disease Detection Utility
Advanced disease name extraction and tagging using NLP.
Combines keyword matching with named entity recognition and context analysis.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import spaCy for advanced NLP
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
        nlp = None
        SPACY_AVAILABLE = False
except (ImportError, OSError) as e:
    # Catches both import errors and DLL/system errors
    SPACY_AVAILABLE = False
    nlp = None
    logger.warning(f"spaCy not available ({type(e).__name__}). Using keyword-based detection.")


class DiseaseDetector:
    """
    Advanced disease detection for agricultural text.
    Uses multiple strategies: keyword matching, NLP entity recognition, and context analysis.
    """
    
    # Comprehensive disease database with multiple forms
    DISEASE_DATABASE = {
        'late_blight': {
            'name': 'Late Blight',
            'scientific': 'Phytophthora infestans',
            'keywords': ['late blight', 'phytophthora infestans', 'phytophthora', 'potato blight'],
            'aliases': ['LB', 'late-blight'],
            'symptoms': ['water-soaked lesions', 'white mold', 'brown spots on leaves']
        },
        'early_blight': {
            'name': 'Early Blight',
            'scientific': 'Alternaria solani',
            'keywords': ['early blight', 'alternaria solani', 'alternaria'],
            'aliases': ['EB', 'early-blight', 'alternaria leaf spot'],
            'symptoms': ['concentric rings', 'target spot', 'dark spots']
        },
        'bacterial_spot': {
            'name': 'Bacterial Spot',
            'scientific': 'Xanthomonas',
            'keywords': ['bacterial spot', 'xanthomonas', 'bacterial leaf spot'],
            'aliases': ['BS'],
            'symptoms': ['water-soaked spots', 'bacterial lesions']
        },
        'bacterial_speck': {
            'name': 'Bacterial Speck',
            'scientific': 'Pseudomonas syringae',
            'keywords': ['bacterial speck', 'pseudomonas syringae', 'pseudomonas'],
            'aliases': [],
            'symptoms': ['small black spots', 'speck lesions']
        },
        'septoria_leaf_spot': {
            'name': 'Septoria Leaf Spot',
            'scientific': 'Septoria lycopersici',
            'keywords': ['septoria', 'septoria leaf spot', 'septoria lycopersici'],
            'aliases': ['SLS'],
            'symptoms': ['circular spots', 'pycnidia', 'leaf spots with dark center']
        },
        'fusarium_wilt': {
            'name': 'Fusarium Wilt',
            'scientific': 'Fusarium oxysporum',
            'keywords': ['fusarium wilt', 'fusarium oxysporum', 'fusarium'],
            'aliases': ['FW'],
            'symptoms': ['yellowing leaves', 'wilting', 'vascular discoloration']
        },
        'verticillium_wilt': {
            'name': 'Verticillium Wilt',
            'scientific': 'Verticillium',
            'keywords': ['verticillium wilt', 'verticillium', 'verticillium dahliae'],
            'aliases': ['VW'],
            'symptoms': ['v-shaped yellowing', 'vascular browning', 'wilting lower leaves']
        },
        'powdery_mildew': {
            'name': 'Powdery Mildew',
            'scientific': 'Oidium neolycopersici',
            'keywords': ['powdery mildew', 'oidium', 'leveillula taurica'],
            'aliases': ['PM'],
            'symptoms': ['white powder', 'powdery coating', 'yellow spots']
        },
        'tomato_mosaic_virus': {
            'name': 'Tomato Mosaic Virus',
            'scientific': 'ToMV',
            'keywords': ['tomato mosaic virus', 'tomv', 'mosaic virus', 'mosaic disease'],
            'aliases': ['TMV'],
            'symptoms': ['mosaic pattern', 'leaf mottling', 'distorted leaves']
        },
        'tomato_yellow_leaf_curl': {
            'name': 'Tomato Yellow Leaf Curl Virus',
            'scientific': 'TYLCV',
            'keywords': ['tomato yellow leaf curl', 'tylcv', 'yellow leaf curl', 'TYLC'],
            'aliases': ['TYLCV', 'TYLC'],
            'symptoms': ['leaf curling', 'yellowing', 'stunted growth']
        },
        'anthracnose': {
            'name': 'Anthracnose',
            'scientific': 'Colletotrichum',
            'keywords': ['anthracnose', 'colletotrichum', 'fruit rot'],
            'aliases': [],
            'symptoms': ['sunken lesions', 'circular spots on fruit', 'fruit rot']
        },
        'gray_mold': {
            'name': 'Gray Mold',
            'scientific': 'Botrytis cinerea',
            'keywords': ['gray mold', 'grey mold', 'botrytis', 'botrytis cinerea'],
            'aliases': ['botrytis blight'],
            'symptoms': ['gray fuzzy growth', 'brown spots', 'stem cankers']
        },
        'tomato_spotted_wilt': {
            'name': 'Tomato Spotted Wilt Virus',
            'scientific': 'TSWV',
            'keywords': ['tomato spotted wilt', 'tswv', 'spotted wilt'],
            'aliases': ['TSWV'],
            'symptoms': ['bronze spots', 'ring spots', 'necrotic lesions']
        },
        'leaf_mold': {
            'name': 'Leaf Mold',
            'scientific': 'Passalora fulva',
            'keywords': ['leaf mold', 'passalora fulva', 'cladosporium fulvum'],
            'aliases': [],
            'symptoms': ['olive green mold', 'yellow spots on upper leaf']
        },
        'southern_blight': {
            'name': 'Southern Blight',
            'scientific': 'Sclerotium rolfsii',
            'keywords': ['southern blight', 'sclerotium rolfsii', 'southern stem rot'],
            'aliases': [],
            'symptoms': ['white mycelium', 'stem rot', 'mustard seed sclerotia']
        },
        'target_spot': {
            'name': 'Target Spot',
            'scientific': 'Corynespora cassiicola',
            'keywords': ['target spot', 'corynespora', 'corynespora cassiicola'],
            'aliases': [],
            'symptoms': ['concentric rings', 'target-like lesions', 'brown spots with rings']
        },
        'spider_mites': {
            'name': 'Spider Mites',
            'scientific': 'Tetranychus urticae',
            'keywords': ['spider mites', 'two-spotted spider mite', 'tetranychus', 'mite damage'],
            'aliases': ['TSSM', 'red spider mite'],
            'symptoms': ['stippling', 'webbing', 'yellowing leaves', 'bronze appearance']
        }
    }
    
    def __init__(self, use_nlp=True):
        """
        Initialize disease detector.
        
        Args:
            use_nlp: Whether to use spaCy NLP for advanced detection
        """
        self.use_nlp = use_nlp and SPACY_AVAILABLE
        
        if use_nlp and not SPACY_AVAILABLE:
            logger.warning("NLP features disabled. spaCy not available.")
        
        # Build reverse lookup for fast matching
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """
        Build an index for fast keyword lookup.
        """
        self.keyword_to_disease = {}
        
        for disease_id, disease_info in self.DISEASE_DATABASE.items():
            # Add all keywords
            for keyword in disease_info['keywords']:
                self.keyword_to_disease[keyword.lower()] = disease_id
            
            # Add aliases
            for alias in disease_info['aliases']:
                self.keyword_to_disease[alias.lower()] = disease_id
            
            # Add scientific name
            sci_name = disease_info['scientific'].lower()
            self.keyword_to_disease[sci_name] = disease_id
    
    def detect_diseases(self, text: str, filename: str = "") -> List[Dict[str, any]]:
        """
        Detect all diseases mentioned in text.
        
        Args:
            text: Text to analyze
            filename: Optional filename for additional context
            
        Returns:
            List of detected diseases with confidence scores
        """
        detected = []
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Strategy 1: Direct keyword matching
        keyword_matches = self._detect_by_keywords(text_lower, filename_lower)
        
        # Strategy 2: NLP-based detection (if available)
        if self.use_nlp and nlp:
            nlp_matches = self._detect_by_nlp(text)
            # Merge results
            all_diseases = set(keyword_matches) | set(nlp_matches)
        else:
            all_diseases = set(keyword_matches)
        
        # Calculate confidence scores
        for disease_id in all_diseases:
            confidence = self._calculate_confidence(disease_id, text_lower, filename_lower)
            disease_info = self.DISEASE_DATABASE[disease_id]
            
            detected.append({
                'id': disease_id,
                'name': disease_info['name'],
                'scientific_name': disease_info['scientific'],
                'confidence': confidence
            })
        
        # Sort by confidence
        detected.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected
    
    def _detect_by_keywords(self, text: str, filename: str) -> Set[str]:
        """
        Detect diseases using keyword matching.
        
        Args:
            text: Lowercase text
            filename: Lowercase filename
            
        Returns:
            Set of detected disease IDs
        """
        detected = set()
        
        # Check text and filename
        combined_text = text + " " + filename
        
        for keyword, disease_id in self.keyword_to_disease.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, combined_text):
                detected.add(disease_id)
        
        return detected
    
    def _detect_by_nlp(self, text: str) -> Set[str]:
        """
        Detect diseases using spaCy NLP.
        
        Args:
            text: Original text (with proper casing)
            
        Returns:
            Set of detected disease IDs
        """
        if not nlp:
            return set()
        
        detected = set()
        
        try:
            # Process text with spaCy (limit to first 100k chars for performance)
            doc = nlp(text[:100000])
            
            # Look for disease-related entities and phrases
            for ent in doc.ents:
                if ent.label_ in ['DISEASE', 'PRODUCT', 'ORG']:
                    ent_lower = ent.text.lower()
                    # Check against our disease database
                    for disease_id, disease_info in self.DISEASE_DATABASE.items():
                        if any(keyword in ent_lower for keyword in disease_info['keywords']):
                            detected.add(disease_id)
            
            # Look for noun chunks that might be diseases
            for chunk in doc.noun_chunks:
                chunk_lower = chunk.text.lower()
                if any(word in chunk_lower for word in ['blight', 'wilt', 'mold', 'virus', 'spot', 'rot']):
                    # Check against database
                    for keyword, disease_id in self.keyword_to_disease.items():
                        if keyword in chunk_lower:
                            detected.add(disease_id)
        
        except Exception as e:
            logger.warning(f"NLP detection error: {e}")
        
        return detected
    
    def _calculate_confidence(self, disease_id: str, text: str, filename: str) -> float:
        """
        Calculate confidence score for disease detection.
        
        Args:
            disease_id: Disease identifier
            text: Lowercase text
            filename: Lowercase filename
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        disease_info = self.DISEASE_DATABASE[disease_id]
        confidence = 0.0
        matches = 0
        
        # Check main keywords (high weight)
        for keyword in disease_info['keywords']:
            count = text.count(keyword.lower())
            if count > 0:
                confidence += min(count * 0.2, 0.5)
                matches += count
        
        # Check scientific name (high weight)
        if disease_info['scientific'].lower() in text:
            confidence += 0.3
            matches += 1
        
        # Check filename (medium weight)
        for keyword in disease_info['keywords']:
            if keyword.lower() in filename:
                confidence += 0.2
                matches += 1
        
        # Check symptoms (lower weight)
        for symptom in disease_info.get('symptoms', []):
            if symptom.lower() in text:
                confidence += 0.1
                matches += 1
        
        # Check aliases
        for alias in disease_info['aliases']:
            if alias.lower() in text:
                confidence += 0.15
                matches += 1
        
        # Normalize confidence to 0-1 range
        confidence = min(confidence, 1.0)
        
        # Boost confidence if multiple matches
        if matches > 3:
            confidence = min(confidence * 1.2, 1.0)
        
        return round(confidence, 3)
    
    def get_primary_disease(self, text: str, filename: str = "") -> str:
        """
        Get the most likely primary disease from text.
        
        Args:
            text: Text to analyze
            filename: Optional filename
            
        Returns:
            Disease name or 'General' if none detected
        """
        detected = self.detect_diseases(text, filename)
        
        if detected and detected[0]['confidence'] > 0.3:
            return detected[0]['name']
        
        return 'General'
    
    def get_all_disease_names(self) -> List[str]:
        """
        Get list of all supported disease names.
        
        Returns:
            List of disease names
        """
        return [info['name'] for info in self.DISEASE_DATABASE.values()]


# Global instance
_detector = None

def get_disease_detector(use_nlp=True) -> DiseaseDetector:
    """
    Get or create disease detector singleton.
    
    Args:
        use_nlp: Whether to use NLP features
        
    Returns:
        DiseaseDetector instance
    """
    global _detector
    if _detector is None:
        _detector = DiseaseDetector(use_nlp=use_nlp)
    return _detector
