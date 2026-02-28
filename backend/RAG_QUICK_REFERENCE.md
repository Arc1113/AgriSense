# 🚀 AgriSense RAG - Quick Reference

## One-Time Setup (3 steps)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize vector store
python init_vector_store.py

# 3. Set API key
echo "GROQ_API_KEY=your_key_here" > .env
```

**Or use automated script:**
- Windows: `setup_rag.bat`
- Linux/Mac: `./setup_rag.sh`

---

## Start Backend

```bash
python main.py
```

**Expected log messages:**
```
✅ Vector store ready with 463 documents
🚀 AgriSense API ready to serve requests
```

---

## API Response Changes

### New Fields in `/predict` Response:

```json
{
  "advice": {
    "severity": "Medium",
    "action_plan": "...",
    "safety_warning": "...",
    "weather_advisory": "...",
    
    // NEW: Source citations
    "sources": [
      {
        "source": "FAO",
        "content_type": "Treatment",
        "confidence": 0.89
      }
    ],
    
    // NEW: RAG status indicator
    "rag_enabled": true
  }
}
```

---

## Verify RAG is Working

### ✅ Check Logs:
```
✅ Retrieved 5 relevant documents
✅ Advice generated in 3.45s (RAG: ON)
```

### ✅ Check Response:
- `"rag_enabled": true`
- `"sources": [...]` array present (3-5 items)

### ❌ If RAG Disabled:
```
⚠️ Vector store unavailable - RAG disabled
```
- System still works (uses LLM knowledge only)
- `"rag_enabled": false`
- Empty `"sources": []` array

---

## Files Added

| File | Purpose |
|------|---------|
| `vector_store_manager.py` | ChromaDB vector store management |
| `init_vector_store.py` | One-time initialization script |
| `setup_rag.sh` / `.bat` | Automated setup scripts |
| `RAG_SETUP.md` | Complete setup guide |
| `RAG_IMPLEMENTATION_SUMMARY.md` | Technical details |
| `.gitignore` | Exclude vector_store/ directory |

---

## Files Modified

| File | Changes |
|------|---------|
| `requirements.txt` | Added chromadb, langchain dependencies |
| `rag_agent.py` | Added retrieval, context injection |
| `main.py` | Added source citations to response model |

---

## Troubleshooting

### Problem: Module not found
```bash
pip install -r requirements.txt --force-reinstall
```

### Problem: Vector store not initialized
```bash
python init_vector_store.py --rebuild
```

### Problem: RAG disabled in logs
**Check:** Does `rag_combined.json` exist?
```bash
ls Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_combined.json
```

### Problem: Slow first query
**Normal:** Embedding model downloads on first use (~80MB)
- Subsequent queries are fast (<1s)

---

## Configuration

### Tune Retrieval (in `rag_agent.py`):

```python
# Number of documents to retrieve
retrieved_context, source_docs = retrieve_context(disease_name, k=5)
# k=3 (fast), k=5 (balanced), k=10 (thorough)

# Minimum confidence threshold
docs = vector_store.retrieve_documents(
    query=query,
    k=k,
    min_confidence=0.3  # 0.0-1.0
)
```

---

## Data Sources

**463 documents from:**
- FAO (Food and Agriculture Organization)
- PCAARRD (Philippine Council for Agriculture)
- DA (Department of Agriculture, Philippines)
- UC IPM (University of California)
- UPLB (University of the Philippines Los Baños)
- WorldVeg (World Vegetable Center)

---

## Performance

| Metric | Value |
|--------|-------|
| Vector store init | ~2-3 minutes (one-time) |
| First query | 5-10 seconds |
| Cached queries | <100 ms |
| Fresh queries | 1-2 seconds |
| API response (RAG) | 3-5 seconds |

---

## Testing

### Test Vector Store:
```bash
python init_vector_store.py --test
```

### Test Retrieval:
```python
from vector_store_manager import VectorStoreManager

manager = VectorStoreManager()
manager.initialize_from_json("./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_combined.json")

docs = manager.retrieve_documents(
    query="How to treat early blight?",
    disease_filter="Early Blight",
    k=5
)

for doc in docs:
    print(f"{doc['source']} - {doc['content_type']}")
```

### Test API:
```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@tomato_leaf.jpg" \
  -F "model=mobile" \
  -F "weather=Sunny"
```

---

## Frontend Integration

```jsx
// Display RAG sources
{advice.rag_enabled && (
  <div className="sources">
    <h4>📚 Information Sources</h4>
    {advice.sources.map((src, i) => (
      <span key={i} className="badge">
        {src.source} ({src.content_type})
      </span>
    ))}
  </div>
)}
```

---

## Commands Cheat Sheet

```bash
# Setup
pip install -r requirements.txt
python init_vector_store.py

# Start
python main.py

# Test
python init_vector_store.py --test

# Rebuild
python init_vector_store.py --rebuild

# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

---

## Key Benefits

### Before RAG:
❌ Generic LLM advice  
❌ No source attribution  
❌ May be outdated  

### After RAG:
✅ Evidence-based from 463 documents  
✅ Source citations (FAO, PCAARRD, etc.)  
✅ Region-appropriate (Philippine + Global)  
✅ Transparent and verifiable  

---

## Support

📚 **Full Documentation**: See `RAG_SETUP.md`  
📊 **Technical Details**: See `RAG_IMPLEMENTATION_SUMMARY.md`  
🐛 **Issues**: Check logs and error messages  

---

**Status**: ✅ RAG System Ready  
**Documents**: 463 embedded and indexed  
**Sources**: FAO, PCAARRD, UC IPM, DA, UPLB, WorldVeg  
**Mode**: Hybrid (RAG + LLM with graceful fallback)
