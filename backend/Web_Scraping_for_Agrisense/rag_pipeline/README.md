# RAG Data Pipeline for Tomato Disease Treatment

A production-ready data preparation pipeline for a Retrieval-Augmented Generation (RAG) system focused on tomato disease treatments. This pipeline scrapes, processes, and structures agricultural data from public sources for use in RAG applications.

## � Enhanced Features (v2.0)

- **🖼️ OCR Support**: Automatic OCR fallback for scanned PDFs using Tesseract
- **🧠 Advanced Disease Detection**: NLP-powered detection with confidence scoring (15 diseases)
- **📊 Rich Metadata**: Scientific names, confidence scores, multiple disease detection
- **🔄 Smart Processing**: Intelligent fallback strategies for maximum coverage

## 🎯 Core Features

- **Web Scraping**: Polite scraping of HTML pages and PDFs from agricultural institutions
- **Text Extraction**: Clean text extraction from PDFs and HTML documents (with OCR fallback)
- **Text Cleaning**: Removes headers, footers, page numbers, and normalizes text
- **Smart Chunking**: Sentence-based chunking (~500 tokens) with overlap for semantic coherence
- **Metadata Enrichment**: Advanced disease detection with NLP and confidence scoring
- **RAG-Ready Output**: JSON format compatible with LangChain, LlamaIndex, FAISS, and Chroma

## 📁 Project Structure

```
rag_pipeline/
├── raw/                          # Raw scraped data
│   ├── pdfs/                     # Downloaded PDF files
│   └── html/                     # Scraped HTML pages
├── processed/                    # Processed data
│   ├── extracted_text/           # Text extracted from PDFs/HTML
│   ├── cleaned_text/             # Cleaned and normalized text
│   ├── chunks/                   # Chunked text (JSON files)
│   └── rag_json/                 # Final RAG-ready JSON
├── scrape_html.py               # HTML scraper
├── scrape_pdfs.py               # PDF downloader
├── extract_text.py              # Text extraction (with OCR)
├── clean_text.py                # Text cleaning
├── chunk_text.py                # Text chunking
├── disease_detector.py          # 🆕 Advanced disease detection
├── add_metadata.py              # Metadata enrichment (enhanced)
├── run_pipeline.py              # Master pipeline orchestrator
└── test_new_features.py         # 🆕 Feature testing

📚 Documentation:
├── README.md                    # This file
├── GETTING_STARTED.md           # Quick start guide
├── ARCHITECTURE.md              # Pipeline architecture
├── REFACTORING_GUIDE.md         # 🆕 New features guide
└── REFACTORING_SUMMARY.md       # 🆕 Changes summary
├── add_metadata.py              # Metadata enrichment & JSON export
├── run_pipeline.py              # Master pipeline orchestrator
└── requirements.txt             # Python dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd rag_pipeline
pip install -r requirements.txt
```

### 2. Configure Data Sources

Edit the source URLs in the scraping scripts:

**For HTML sources** ([scrape_html.py](rag_pipeline/scrape_html.py)):
```python
urls_to_scrape = [
    ('http://ipm.ucanr.edu/PMG/r783101011.html', 'ucipm_tomato_diseases.html'),
    # Add more URLs...
]
```

**For PDF sources** ([scrape_pdfs.py](rag_pipeline/scrape_pdfs.py)):
```python
pdfs_to_download = [
    ('http://www.fao.org/example.pdf', 'fao_tomato_guide.pdf'),
    # Add more URLs...
]
```

### 3. Run the Pipeline

**Full pipeline** (including scraping):
```bash
python run_pipeline.py
```

**Skip scraping** (if you already have raw data):
```bash
python run_pipeline.py --skip-scraping
```

### 4. Use the Output

The final RAG-ready data is saved in `processed/rag_json/rag_documents.json`.

## 📋 Pipeline Steps

### Step 1: HTML Scraping
- Scrapes publicly accessible HTML pages
- Respects robots.txt and polite scraping delays
- Saves raw HTML to `raw/html/`

```bash
python scrape_html.py
```

### Step 2: PDF Downloading
- Downloads publicly available PDFs
- Shows progress bars for large files
- Saves to `raw/pdfs/`

```bash
python scrape_pdfs.py
```

### Step 3: Text Extraction
- Extracts text from PDFs using pdfplumber
- Extracts text from HTML using BeautifulSoup
- Removes scripts, styles, and navigation elements
- Saves to `processed/extracted_text/`

```bash
python extract_text.py
```

### Step 4: Text Cleaning
- Removes page numbers, headers, and footers
- Normalizes whitespace and line breaks
- Fixes broken sentences
- Saves to `processed/cleaned_text/`

```bash
python clean_text.py
```

### Step 5: Text Chunking
- Chunks text into ~500-token segments
- Uses sentence boundaries (NLTK)
- Includes 100-token overlap between chunks
- Saves to `processed/chunks/`

```bash
python chunk_text.py
```

### Step 6: Metadata Enrichment
- Adds metadata to each chunk:
  - `crop`: "Tomato"
  - `disease`: Inferred from content
  - `region`: "PH" or "Global"
  - `source`: FAO, UC IPM, PCAARRD, DA, UPLB
  - `content_type`: Symptoms, Treatment, Prevention
  - `language`: "English"
- Exports final RAG-ready JSON
- Saves to `processed/rag_json/rag_documents.json`

```bash
python add_metadata.py
```

## 📊 Output Format

The final `rag_documents.json` has the following structure:

```json
{
  "version": "1.0",
  "created_at": "2026-01-31T12:00:00",
  "total_documents": 150,
  "documents": [
    {
      "id": "unique_chunk_id",
      "text": "Chunk text content...",
      "metadata": {
        "crop": "Tomato",
        "disease": "Late Blight",
        "region": "Global",
        "source": "FAO",
        "content_type": "Treatment",
        "language": "English",
        "source_file": "fao_tomato_guide.txt",
        "token_count": 485,
        "created_at": "2026-01-31T12:00:00"
      }
    }
  ]
}
```

## 🔧 Configuration

### Chunking Parameters

Edit [chunk_text.py](rag_pipeline/chunk_text.py):

```python
TARGET_CHUNK_SIZE = 500    # Target tokens per chunk
MIN_CHUNK_SIZE = 100       # Minimum chunk size
OVERLAP_SIZE = 100         # Overlap between chunks
```

### Scraping Behavior

Edit scraping scripts:

```python
REQUEST_DELAY = 2          # Seconds between requests
TIMEOUT = 30               # Request timeout
```

## 🎯 Data Sources

This pipeline is designed to work with public agricultural data from:

### Global Sources
- **FAO** (Food and Agriculture Organization)
- **UC IPM** (University of California Integrated Pest Management)

### Philippines Sources
- **PCAARRD** (Philippine Council for Agriculture, Aquatic and Natural Resources Research and Development)
- **DA** (Department of Agriculture Philippines)
- **UPLB** (University of the Philippines Los Baños)

## 🔌 Integration with RAG Frameworks

### LangChain

```python
import json
from langchain.docstore.document import Document

with open('processed/rag_json/rag_documents.json', 'r') as f:
    data = json.load(f)

documents = [
    Document(
        page_content=doc['text'],
        metadata=doc['metadata']
    )
    for doc in data['documents']
]
```

### LlamaIndex

```python
import json
from llama_index.core import Document

with open('processed/rag_json/rag_documents.json', 'r') as f:
    data = json.load(f)

documents = [
    Document(
        text=doc['text'],
        metadata=doc['metadata'],
        doc_id=doc['id']
    )
    for doc in data['documents']
]
```

### FAISS / Chroma

```python
import json

with open('processed/rag_json/rag_documents.json', 'r') as f:
    data = json.load(f)

texts = [doc['text'] for doc in data['documents']]
metadatas = [doc['metadata'] for doc in data['documents']]
ids = [doc['id'] for doc in data['documents']]

# Use with your vector store
```

## 📝 Logging

All pipeline operations are logged to:
- Console (INFO level)
- `pipeline.log` file (when using run_pipeline.py)

## ⚠️ Important Notes

1. **Respect Copyright**: Only scrape publicly accessible documents
2. **Polite Scraping**: Built-in delays respect server resources
3. **No Medical Claims**: This pipeline does NOT generate treatment recommendations
4. **Verify Content**: Always verify agricultural guidance with experts

## 🛠️ Troubleshooting

### NLTK Data Not Found
The pipeline automatically downloads required NLTK data. If issues occur:
```python
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
```

### No Files Processed
- Check that raw data exists in `raw/pdfs/` and `raw/html/`
- Verify file permissions
- Check logs for specific errors

### Empty Chunks
- Verify text extraction worked (check `processed/extracted_text/`)
- Ensure text cleaning didn't remove all content
- Check minimum chunk size settings

## 📄 License

This pipeline is for educational and research purposes. Respect the licenses and terms of use for all data sources.

## 🤝 Contributing

This is a production-ready template. Customize for your specific needs:
- Add more data sources
- Adjust metadata inference rules
- Modify chunking strategies
- Enhance disease detection

## 📚 References

- [LangChain Documentation](https://python.langchain.com/)
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [UC IPM](http://ipm.ucanr.edu/)
- [FAO](http://www.fao.org/)
