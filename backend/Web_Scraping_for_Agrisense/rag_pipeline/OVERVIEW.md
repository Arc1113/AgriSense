# RAG Pipeline Project Overview

## 🎯 Project Goal

Build a production-ready data preparation pipeline for a Retrieval-Augmented Generation (RAG) system focused on tomato disease treatment information from global and Philippine agricultural sources.

## 📦 What's Included

### Core Pipeline Scripts

1. **scrape_html.py** - Web scraper for HTML pages
   - Scrapes UC IPM and other HTML sources
   - Polite scraping with delays
   - User agent identification

2. **scrape_pdfs.py** - PDF downloader
   - Downloads FAO, PCAARRD, DA, UPLB PDFs
   - Progress bars for large files
   - Error handling and retry logic

3. **extract_text.py** - Text extraction
   - Extracts from PDFs using pdfplumber
   - Extracts from HTML using BeautifulSoup
   - Removes unwanted HTML elements

4. **clean_text.py** - Text cleaning
   - Removes page numbers, headers, footers
   - Normalizes whitespace
   - Fixes line breaks

5. **chunk_text.py** - Text chunking
   - ~500 token chunks with 100 token overlap
   - Sentence-based chunking (NLTK)
   - Preserves semantic boundaries

6. **add_metadata.py** - Metadata enrichment & export
   - Infers disease, source, region, content type
   - Exports RAG-ready JSON
   - Generates statistics

### Utility Scripts

7. **run_pipeline.py** - Master orchestrator
   - Runs entire pipeline in sequence
   - Supports skip-scraping mode
   - Comprehensive logging

8. **setup.py** - Environment setup
   - Checks Python version
   - Installs dependencies
   - Downloads NLTK data
   - Verifies installation

9. **validate_pipeline.py** - Output validator
   - Validates JSON structure
   - Checks data quality
   - Identifies issues and warnings

10. **example_usage.py** - Usage examples
    - LangChain integration
    - LlamaIndex integration
    - Chroma integration
    - FAISS examples

## 🗂️ Directory Structure

```
rag_pipeline/
│
├── raw/                          # Raw scraped data (gitignored)
│   ├── pdfs/                     # Downloaded PDFs
│   └── html/                     # Scraped HTML files
│
├── processed/                    # Processed data (gitignored)
│   ├── extracted_text/           # Extracted .txt files
│   ├── cleaned_text/             # Cleaned .txt files
│   ├── chunks/                   # Chunked JSON files
│   └── rag_json/                 # Final RAG-ready output
│       └── rag_documents.json    # ⭐ Main output file
│
├── scrape_html.py               # HTML scraper
├── scrape_pdfs.py               # PDF downloader
├── extract_text.py              # Text extraction
├── clean_text.py                # Text cleaning
├── chunk_text.py                # Text chunking
├── add_metadata.py              # Metadata & JSON export
├── run_pipeline.py              # Master pipeline
├── setup.py                     # Setup script
├── validate_pipeline.py         # Validator
├── example_usage.py             # Usage examples
├── README.md                    # Main documentation
├── .gitignore                   # Git ignore rules
└── OVERVIEW.md                  # This file
```

## 🚀 Quick Start

### 1. Setup
```bash
cd rag_pipeline
python setup.py
```

### 2. Configure Sources
Edit URLs in:
- `scrape_html.py` (lines 85-92)
- `scrape_pdfs.py` (lines 110-120)

### 3. Run Pipeline
```bash
python run_pipeline.py
```

### 4. Validate Output
```bash
python validate_pipeline.py
```

### 5. Use Data
```bash
python example_usage.py
```

## 📊 Output Format

### RAG JSON Structure
```json
{
  "version": "1.0",
  "created_at": "2026-01-31T12:00:00",
  "total_documents": 150,
  "documents": [
    {
      "id": "unique_chunk_id",
      "text": "chunk text...",
      "metadata": {
        "crop": "Tomato",
        "disease": "Late Blight",
        "region": "PH",
        "source": "PCAARRD",
        "content_type": "Treatment",
        "language": "English",
        "source_file": "original_file.txt",
        "token_count": 485,
        "created_at": "2026-01-31T12:00:00"
      }
    }
  ]
}
```

## 🎯 Key Features

### Polite Web Scraping
- User agent identification
- Request delays (2 seconds)
- Timeout handling
- Error recovery

### Intelligent Text Cleaning
- Page number removal
- Header/footer detection
- Whitespace normalization
- Special character handling
- URL removal

### Smart Chunking
- Target: ~500 tokens per chunk
- Minimum: 100 tokens
- Overlap: 100 tokens
- Sentence boundaries preserved
- NLTK tokenization

### Metadata Inference
- **Disease**: Keyword matching in text and filename
- **Source**: URL and filename pattern matching
- **Region**: PH/Global based on source
- **Content Type**: Keyword analysis (symptoms, treatment, prevention)

### Supported Diseases
- Late Blight
- Early Blight
- Bacterial Spot
- Bacterial Speck
- Septoria Leaf Spot
- Fusarium Wilt
- Verticillium Wilt
- Powdery Mildew
- Tomato Mosaic Virus
- Tomato Yellow Leaf Curl
- Anthracnose
- Gray Mold

### Data Sources
**Global:**
- FAO (Food and Agriculture Organization)
- UC IPM (UC Integrated Pest Management)

**Philippines:**
- PCAARRD (Philippine Council for Agriculture)
- DA (Department of Agriculture)
- UPLB (University of the Philippines Los Baños)

## 🔌 RAG Framework Integration

### Compatible With:
- ✅ LangChain
- ✅ LlamaIndex
- ✅ FAISS
- ✅ Chroma
- ✅ Pinecone
- ✅ Weaviate
- ✅ Qdrant

### Example: LangChain
```python
from langchain.docstore.document import Document

with open('processed/rag_json/rag_documents.json', 'r') as f:
    data = json.load(f)

documents = [
    Document(page_content=doc['text'], metadata=doc['metadata'])
    for doc in data['documents']
]
```

## 📈 Pipeline Flow

```
1. SCRAPE
   ├── HTML Pages → raw/html/*.html
   └── PDF Files → raw/pdfs/*.pdf

2. EXTRACT
   └── Text → processed/extracted_text/*.txt

3. CLEAN
   └── Normalized Text → processed/cleaned_text/*.txt

4. CHUNK
   └── JSON Chunks → processed/chunks/*_chunks.json

5. ENRICH
   └── RAG JSON → processed/rag_json/rag_documents.json ⭐

6. VALIDATE
   └── Quality Check → Pass/Fail Report

7. USE
   └── Load into RAG Framework
```

## 🛠️ Configuration Options

### Chunking (chunk_text.py)
```python
TARGET_CHUNK_SIZE = 500    # tokens per chunk
MIN_CHUNK_SIZE = 100       # minimum chunk size
OVERLAP_SIZE = 100         # overlap between chunks
```

### Scraping (scrape_*.py)
```python
REQUEST_DELAY = 2          # seconds between requests
TIMEOUT = 30               # request timeout (seconds)
```

## ⚙️ Requirements

- Python 3.7+
- requests 2.31.0
- beautifulsoup4 4.12.3
- pdfplumber 0.10.4
- nltk 3.8.1
- tqdm 4.66.1
- lxml 5.1.0

## 📝 Best Practices

1. **Always validate output** after pipeline run
2. **Start with small datasets** for testing
3. **Review metadata inference** for accuracy
4. **Adjust chunk sizes** based on your model
5. **Respect source terms of service**
6. **Verify agricultural information** with experts

## 🔍 Troubleshooting

### No documents in output
- Check raw data exists
- Verify extraction worked
- Review cleaning settings

### Poor metadata quality
- Adjust keyword lists in add_metadata.py
- Add more disease patterns
- Improve source detection

### Chunking issues
- Adjust TARGET_CHUNK_SIZE
- Check MIN_CHUNK_SIZE
- Verify NLTK data downloaded

## 📚 Documentation Files

- **README.md** - Main user guide
- **OVERVIEW.md** - This project overview
- **requirements.txt** - Python dependencies
- **.gitignore** - Git ignore rules

## 🤝 Contributing

This is a complete, production-ready pipeline. Customize for your needs:
- Add more data sources
- Enhance metadata inference
- Implement custom chunking strategies
- Add more disease patterns
- Support additional languages

## ⚠️ Important Notes

1. **Copyright**: Only use publicly accessible documents
2. **Terms of Service**: Respect all source website terms
3. **Medical Disclaimer**: This is for educational/research purposes only
4. **Data Quality**: Always verify agricultural information
5. **Polite Scraping**: Built-in delays respect servers

## 🎓 Educational Purpose

This pipeline is designed for:
- Agricultural research
- Educational projects
- RAG system prototyping
- Data science learning
- AI/ML experimentation

## 📞 Support

For issues or questions:
1. Check the README.md
2. Run validate_pipeline.py
3. Review pipeline.log
4. Check example_usage.py

## 🏆 Success Criteria

Your pipeline is successful when:
- ✅ All scripts run without errors
- ✅ RAG JSON file is created
- ✅ Validation passes
- ✅ Documents have proper metadata
- ✅ Chunks are appropriate size
- ✅ Data loads into your RAG framework

---

**Ready to build your RAG system? Start with `python setup.py`!** 🚀
