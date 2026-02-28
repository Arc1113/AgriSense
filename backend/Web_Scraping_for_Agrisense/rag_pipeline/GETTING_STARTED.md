# 🚀 RAG Pipeline - Getting Started

## What You Have

A **complete, production-ready RAG data pipeline** for tomato disease treatment information with:

✅ 6 core processing scripts  
✅ 4 utility scripts  
✅ Comprehensive documentation  
✅ Example integrations  
✅ Validation tools  

## 📁 Files Created

### In `rag_pipeline/` directory:

**Core Pipeline:**
1. `scrape_html.py` - HTML web scraper
2. `scrape_pdfs.py` - PDF downloader
3. `extract_text.py` - Text extraction (PDF & HTML)
4. `clean_text.py` - Text cleaning & normalization
5. `chunk_text.py` - Smart chunking (~500 tokens)
6. `add_metadata.py` - Metadata enrichment & JSON export

**Utilities:**
7. `run_pipeline.py` - Master orchestrator
8. `setup.py` - Environment setup
9. `validate_pipeline.py` - Output validator
10. `example_usage.py` - Integration examples

**Documentation:**
11. `README.md` - Comprehensive user guide
12. `OVERVIEW.md` - Project overview
13. `.gitignore` - Git configuration

**In parent directory:**
14. `requirements.txt` - Updated with all dependencies

## 🎯 Quick Start (3 Steps)

### Step 1: Setup Environment
```bash
cd rag_pipeline
python setup.py
```

### Step 2: Configure Data Sources

**Edit `scrape_html.py`** (line 85+):
```python
urls_to_scrape = [
    ('http://example.org/tomato-diseases.html', 'filename.html'),
    # Add your URLs here
]
```

**Edit `scrape_pdfs.py`** (line 110+):
```python
pdfs_to_download = [
    ('http://example.org/tomato-guide.pdf', 'filename.pdf'),
    # Add your PDF URLs here
]
```

### Step 3: Run Pipeline
```bash
python run_pipeline.py
```

## 📊 Output

Your final RAG-ready data will be in:
```
processed/rag_json/rag_documents.json
```

This file contains:
- Cleaned, chunked text (~500 tokens each)
- Rich metadata (disease, source, region, content type)
- Ready for LangChain, LlamaIndex, FAISS, Chroma

## 🎓 What Each Script Does

| Script | Input | Output | Purpose |
|--------|-------|--------|---------|
| `scrape_html.py` | URLs | HTML files | Download web pages |
| `scrape_pdfs.py` | URLs | PDF files | Download PDFs |
| `extract_text.py` | PDFs/HTML | Text files | Extract clean text |
| `clean_text.py` | Raw text | Clean text | Remove noise |
| `chunk_text.py` | Clean text | JSON chunks | Create ~500-token chunks |
| `add_metadata.py` | Chunks | RAG JSON | Add metadata, export final format |

## 🔍 How to Validate

After running the pipeline:
```bash
python validate_pipeline.py
```

This checks:
- JSON structure is correct
- All required fields present
- Metadata quality
- Document completeness

## 💡 Example Usage

### Load the data:
```python
import json

with open('processed/rag_json/rag_documents.json', 'r') as f:
    data = json.load(f)

print(f"Total documents: {data['total_documents']}")
```

### Filter by disease:
```python
late_blight_docs = [
    doc for doc in data['documents']
    if doc['metadata']['disease'] == 'Late Blight'
]
```

### Use with LangChain:
```python
from langchain.docstore.document import Document

documents = [
    Document(
        page_content=doc['text'],
        metadata=doc['metadata']
    )
    for doc in data['documents']
]
```

## 📚 Recommended Reading Order

1. **First time?** → Read this file (GETTING_STARTED.md)
2. **Need details?** → Read `README.md`
3. **Want overview?** → Read `OVERVIEW.md`
4. **Ready to integrate?** → Run `example_usage.py`

## 🎨 Customization Points

Want to customize? Edit these:

**Add more diseases:**
- Edit `add_metadata.py` (line 35-48)
- Add your disease keywords

**Adjust chunk size:**
- Edit `chunk_text.py` (line 21-24)
- Change TARGET_CHUNK_SIZE, OVERLAP_SIZE

**Add more sources:**
- Edit `add_metadata.py` (line 59-65)
- Add your source patterns

**Change content types:**
- Edit `add_metadata.py` (line 51-56)
- Add your content categories

## ⚙️ Advanced Usage

### Run individual steps:
```bash
python extract_text.py    # Just extract
python clean_text.py      # Just clean
python chunk_text.py      # Just chunk
```

### Skip scraping (if you have raw data):
```bash
python run_pipeline.py --skip-scraping
```

### Check logs:
```bash
cat pipeline.log
```

## 🐛 Troubleshooting

### "No files found"
- Make sure raw data exists in `raw/pdfs/` and `raw/html/`
- Or run the scraping steps first

### "NLTK data not found"
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

### "Module not found"
```bash
pip install -r ../requirements.txt
```

### "Invalid JSON"
- Check if previous steps completed successfully
- Review pipeline.log for errors

## 📈 Expected Results

A successful pipeline run produces:
- **~150-500 chunks** (depends on source data)
- **Average 400-500 tokens** per chunk
- **Rich metadata** on all documents
- **RAG-ready JSON** file (2-10 MB)

## 🎯 Success Checklist

- [ ] Setup completed without errors
- [ ] URLs configured in scraper scripts
- [ ] Pipeline runs successfully
- [ ] RAG JSON file created
- [ ] Validation passes
- [ ] Example usage works
- [ ] Data loads into your RAG framework

## 🚦 Next Steps

1. ✅ **You are here** - Pipeline created
2. ⏭️ Run `python setup.py`
3. ⏭️ Configure your data sources
4. ⏭️ Run `python run_pipeline.py`
5. ⏭️ Validate with `python validate_pipeline.py`
6. ⏭️ Integrate with your RAG framework
7. 🎉 Build your tomato disease RAG system!

## 📞 Need Help?

1. Check `README.md` for detailed documentation
2. Run `validate_pipeline.py` to check output
3. Review `pipeline.log` for error details
4. Look at `example_usage.py` for integration examples

## 🏆 What Makes This Production-Ready?

✅ **Modular design** - Each script does one thing well  
✅ **Error handling** - Graceful failures with logging  
✅ **Data validation** - Built-in quality checks  
✅ **Polite scraping** - Respects servers with delays  
✅ **Clean code** - Well-commented and documented  
✅ **Flexible** - Easy to customize and extend  
✅ **Complete** - From raw data to RAG-ready JSON  

---

**Ready to start? Run:** `python setup.py` 🚀

Good luck building your tomato disease RAG system! 🍅🤖
