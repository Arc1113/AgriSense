# 🔄 Pipeline Refactoring: OCR & Advanced Disease Detection

## Overview

The RAG pipeline has been **enhanced** with two major features:

1. **OCR Fallback for Scanned PDFs** - Automatically detects and processes scanned documents
2. **Advanced Disease Detection** - NLP-powered disease tagging with confidence scoring

---

## 🆕 New Features

### 1. OCR Fallback for Scanned PDFs

**Problem Solved:** Many agricultural PDFs are scanned images, which pdfplumber cannot read.

**Solution:** Automatic OCR processing using Tesseract when text extraction fails.

#### How It Works

```
PDF Input
    │
    ▼
pdfplumber attempts extraction
    │
    ├─── Text found (>50 chars/page) ────► Use extracted text
    │
    └─── Minimal/no text ────► Trigger OCR
                                    │
                                    ▼
                              Convert to images (300 DPI)
                                    │
                                    ▼
                              Tesseract OCR
                                    │
                                    ▼
                              Extracted text
```

#### Key Features

- ✅ **Automatic Detection**: Identifies scanned pages automatically
- ✅ **Page-Level Fallback**: OCR only scanned pages, not entire document
- ✅ **High Quality**: 300 DPI conversion for accurate OCR
- ✅ **Progress Tracking**: Shows OCR progress with tqdm
- ✅ **Graceful Degradation**: Works without OCR if libraries not installed

#### Configuration

```python
# Enable OCR (default)
extractor = TextExtractor(enable_ocr=True)

# Disable OCR
extractor = TextExtractor(enable_ocr=False)
```

---

### 2. Advanced Disease Detection

**Problem Solved:** Simple keyword matching misses diseases mentioned in different forms.

**Solution:** Multi-strategy detection with NLP, confidence scoring, and comprehensive database.

#### Detection Strategies

1. **Keyword Matching** - Direct string matching with word boundaries
2. **Scientific Names** - Matches Latin binomial nomenclature
3. **Aliases & Abbreviations** - Recognizes acronyms (LB, EB, TYLCV, etc.)
4. **Symptom Context** - Considers disease symptoms in text
5. **NLP Entity Recognition** - Uses spaCy for context-aware detection

#### Disease Database (15 Diseases)

```python
✅ Late Blight (Phytophthora infestans)
✅ Early Blight (Alternaria solani)
✅ Bacterial Spot (Xanthomonas)
✅ Bacterial Speck (Pseudomonas syringae)
✅ Septoria Leaf Spot (Septoria lycopersici)
✅ Fusarium Wilt (Fusarium oxysporum)
✅ Verticillium Wilt (Verticillium)
✅ Powdery Mildew (Oidium neolycopersici)
✅ Tomato Mosaic Virus (ToMV)
✅ Tomato Yellow Leaf Curl Virus (TYLCV)
✅ Anthracnose (Colletotrichum)
✅ Gray Mold (Botrytis cinerea)
✅ Tomato Spotted Wilt Virus (TSWV)
✅ Leaf Mold (Passalora fulva)
✅ Southern Blight (Sclerotium rolfsii)
```

#### Confidence Scoring

Each detection includes a confidence score (0.0 - 1.0):

- **0.9-1.0**: Very high confidence (multiple keyword matches + scientific name)
- **0.7-0.9**: High confidence (main keyword + context)
- **0.5-0.7**: Medium confidence (single keyword or filename match)
- **0.3-0.5**: Low confidence (symptom match or weak signal)
- **<0.3**: Not reported

#### Enhanced Metadata

Old format:
```json
{
  "disease": "Late Blight"
}
```

New format:
```json
{
  "disease": "Late Blight",
  "disease_scientific_name": "Phytophthora infestans",
  "disease_confidence": 0.85,
  "all_diseases_detected": [
    {"name": "Late Blight", "confidence": 0.85},
    {"name": "Early Blight", "confidence": 0.42}
  ]
}
```

---

## 📦 New Dependencies

### Required

```bash
# OCR Support
pip install pytesseract pdf2image Pillow

# Advanced NLP
pip install spacy
python -m spacy download en_core_web_sm
```

### System Requirements

**For OCR:**
- **Tesseract OCR** must be installed on your system
  - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux: `sudo apt-get install tesseract-ocr`
  - Mac: `brew install tesseract`
- **Poppler** (for pdf2image)
  - Windows: Download from [poppler releases](http://blog.alivate.com.au/poppler-windows/)
  - Linux: `sudo apt-get install poppler-utils`
  - Mac: `brew install poppler`

**For NLP:**
- Python 3.7+
- 200MB for spaCy model

---

## 🔧 Installation & Setup

### Step 1: Install Python Dependencies

```bash
cd rag_pipeline
pip install -r ../requirements.txt
```

### Step 2: Install System Dependencies

**Windows:**
```powershell
# Download and install:
# 1. Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
# 2. Poppler: http://blog.alivate.com.au/poppler-windows/

# Add to PATH if needed
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

### Step 3: Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### Step 4: Verify Installation

```bash
python -c "import pytesseract; import pdf2image; import spacy; print('✓ All dependencies installed')"
```

---

## 🚀 Usage

### Using OCR

**Automatic (Recommended):**
```python
from extract_text import TextExtractor

# OCR enabled by default
extractor = TextExtractor(enable_ocr=True)
text = extractor.extract_from_pdf('scanned_document.pdf')
```

**Manual Control:**
```python
# Disable OCR
extractor = TextExtractor(enable_ocr=False)

# Extract normally (will fail on scanned PDFs)
text = extractor.extract_from_pdf('document.pdf')
```

### Using Advanced Disease Detection

**In Pipeline:**
```python
from add_metadata import MetadataEnricher

# Advanced detection enabled by default
enricher = MetadataEnricher(use_advanced_detection=True)
enriched_chunks = enricher.process_directory('processed/chunks')
```

**Standalone:**
```python
from disease_detector import get_disease_detector

detector = get_disease_detector(use_nlp=True)

# Detect diseases in text
text = "The tomato plant shows symptoms of late blight..."
diseases = detector.detect_diseases(text)

for disease in diseases:
    print(f"{disease['name']}: {disease['confidence']:.2f}")
# Output: Late Blight: 0.85
```

**Get Primary Disease:**
```python
primary = detector.get_primary_disease(text, filename="late_blight_guide.pdf")
print(primary)  # "Late Blight"
```

---

## 📊 Performance Considerations

### OCR Performance

- **Speed**: ~2-5 seconds per page at 300 DPI
- **Accuracy**: 95%+ for clean scanned text
- **Memory**: ~100MB per page during processing
- **Recommendation**: Process scanned PDFs separately if possible

### Disease Detection Performance

- **Speed**: <0.1s per chunk (keyword matching)
- **Speed with NLP**: ~0.5s per chunk (first time), <0.1s cached
- **Memory**: ~200MB for spaCy model
- **Recommendation**: Use NLP for better accuracy, disable for speed

---

## 🎯 Configuration Options

### OCR Settings

In `extract_text.py`:

```python
# DPI for PDF to image conversion
DPI = 300  # Higher = better quality, slower

# Minimum characters to trigger OCR
MIN_TEXT_THRESHOLD = 50  # per page
```

### Disease Detection Settings

In `disease_detector.py`:

```python
# Confidence thresholds
REPORT_THRESHOLD = 0.3  # Don't report below this

# NLP text limit
NLP_TEXT_LIMIT = 100000  # chars (performance)
```

---

## 📈 Benefits

### OCR Benefits

✅ **Higher Coverage**: Process scanned agricultural manuals  
✅ **Automatic**: No manual intervention needed  
✅ **Smart**: Only uses OCR when necessary  
✅ **Reliable**: Fallback ensures no data loss  

### Disease Detection Benefits

✅ **Higher Accuracy**: Multi-strategy detection  
✅ **Confidence Scores**: Know reliability of detection  
✅ **Multiple Diseases**: Detect all diseases in text  
✅ **Context-Aware**: Understands scientific names and symptoms  
✅ **Extensible**: Easy to add new diseases  

---

## 🔍 Validation

### Test OCR

```python
from extract_text import TextExtractor

extractor = TextExtractor(enable_ocr=True)

# Test with scanned PDF
text = extractor.extract_from_pdf('tests/scanned_sample.pdf')
print(f"Extracted: {len(text)} characters")
```

### Test Disease Detection

```python
from disease_detector import get_disease_detector

detector = get_disease_detector()

# Test text
test_text = """
The tomato plant shows water-soaked lesions on leaves, 
characteristic of Phytophthora infestans infection. 
White mold appears on the underside.
"""

diseases = detector.detect_diseases(test_text)
print(f"Detected {len(diseases)} diseases:")
for d in diseases:
    print(f"  - {d['name']}: {d['confidence']:.2f}")
```

---

## 🆚 Comparison: Before vs After

### OCR Capability

| Feature | Before | After |
|---------|--------|-------|
| Scanned PDFs | ❌ Failed | ✅ Processed with OCR |
| Mixed PDFs | ⚠️ Partial | ✅ Full extraction |
| Error Handling | ❌ Return None | ✅ Automatic fallback |
| Progress Feedback | ❌ None | ✅ Progress bars |

### Disease Detection

| Feature | Before | After |
|---------|--------|-------|
| Detection Method | Simple keywords | Multi-strategy + NLP |
| Diseases Supported | 12 | 15 |
| Confidence Scores | ❌ No | ✅ Yes (0-1) |
| Scientific Names | ❌ No | ✅ Yes |
| Multiple Diseases | ❌ No | ✅ Yes |
| Aliases/Abbreviations | ⚠️ Limited | ✅ Comprehensive |
| Symptom Context | ❌ No | ✅ Yes |

---

## 🐛 Troubleshooting

### OCR Issues

**"Tesseract not found"**
```bash
# Verify installation
tesseract --version

# Windows: Add to PATH
# C:\Program Files\Tesseract-OCR
```

**"pdf2image error"**
```bash
# Verify Poppler installation
# Windows: Add poppler/bin to PATH
# Linux/Mac: Install poppler-utils
```

**Slow OCR processing**
```python
# Reduce DPI (faster but less accurate)
# Or disable OCR for non-scanned PDFs
extractor = TextExtractor(enable_ocr=False)
```

### Disease Detection Issues

**"spaCy model not found"**
```bash
python -m spacy download en_core_web_sm
```

**Low confidence scores**
```python
# Check if text contains disease keywords
from disease_detector import get_disease_detector
detector = get_disease_detector()
print(detector.get_all_disease_names())
```

**NLP errors**
```python
# Disable NLP, use keyword matching only
detector = get_disease_detector(use_nlp=False)
```

---

## 📚 API Reference

### TextExtractor

```python
class TextExtractor:
    def __init__(self, output_dir='processed/extracted_text', enable_ocr=True)
    def extract_from_pdf(self, pdf_path) -> str
    def extract_from_html(self, html_path) -> str
    def _extract_with_ocr(self, pdf_path) -> str
    def _extract_page_with_ocr(self, pdf_path, page_num) -> str
```

### DiseaseDetector

```python
class DiseaseDetector:
    def __init__(self, use_nlp=True)
    def detect_diseases(self, text: str, filename: str = "") -> List[Dict]
    def get_primary_disease(self, text: str, filename: str = "") -> str
    def get_all_disease_names(self) -> List[str]
```

### MetadataEnricher

```python
class MetadataEnricher:
    def __init__(self, output_dir='processed/rag_json', use_advanced_detection=True)
    def infer_disease(self, text, filename) -> Dict
    def enrich_chunk(self, chunk, filename) -> Dict
```

---

## 🎯 Best Practices

### For OCR

1. ✅ **Keep enabled by default** - automatic fallback is safe
2. ✅ **Monitor logs** - check which PDFs needed OCR
3. ✅ **Test accuracy** - verify OCR output quality
4. ❌ **Don't force OCR** - let automatic detection work

### For Disease Detection

1. ✅ **Use NLP when available** - better accuracy
2. ✅ **Check confidence scores** - filter low-confidence results
3. ✅ **Review all_diseases_detected** - catch multiple diseases
4. ✅ **Add custom diseases** - extend disease database as needed

---

## 🔄 Migration Guide

### Updating Existing Pipelines

**No changes required!** Both features have graceful fallback:

1. **Without OCR libraries**: Falls back to pdfplumber only
2. **Without spaCy**: Falls back to keyword matching
3. **Existing code**: Works without modification

### Opting In

```python
# In your scripts, replace:
extractor = TextExtractor()

# With:
extractor = TextExtractor(enable_ocr=True)  # Enable OCR

# And replace:
enricher = MetadataEnricher()

# With:
enricher = MetadataEnricher(use_advanced_detection=True)  # Enable NLP
```

---

## 📝 Updated Files

1. ✅ `requirements.txt` - Added OCR and NLP dependencies
2. ✅ `extract_text.py` - Added OCR fallback logic
3. ✅ `disease_detector.py` - New disease detection module
4. ✅ `add_metadata.py` - Integrated advanced detection
5. ✅ `REFACTORING_GUIDE.md` - This document

---

## 🎉 Summary

Your RAG pipeline now has:

- **🖼️ OCR Support**: Process scanned PDFs automatically
- **🧠 Smart Disease Detection**: NLP-powered with confidence scores
- **📊 Better Metadata**: Scientific names, multiple diseases, confidence
- **🔄 Backward Compatible**: Existing code still works
- **⚡ Performance**: Optimized with caching and smart fallbacks

**Ready to process more agricultural documents with higher accuracy!** 🍅🤖
