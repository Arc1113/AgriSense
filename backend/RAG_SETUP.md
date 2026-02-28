# AgriSense RAG Setup Guide

## 🚀 Quick Start

The AgriSense backend now includes a complete RAG (Retrieval-Augmented Generation) system that retrieves relevant agricultural knowledge from 463 processed documents to generate evidence-based treatment recommendations.

## Prerequisites

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   Create a `.env` file in the `backend/` directory:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```
   Get your free API key at: https://console.groq.com

## One-Time Vector Store Initialization

Before running the backend for the first time, initialize the vector store:

```bash
python init_vector_store.py
```

This will:
- Load 463 agricultural documents from `rag_combined.json`
- Embed documents using HuggingFace sentence-transformers
- Create a persistent ChromaDB vector store
- Take ~2-3 minutes to complete

**Optional flags:**
- `--rebuild`: Force rebuild even if vector store exists
- `--test`: Run test queries after initialization

Example:
```bash
python init_vector_store.py --test
```

## Running the Backend

Once the vector store is initialized, start the FastAPI server:

```bash
python main.py
```

or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## How It Works

### Architecture

```
User Upload Image
    ↓
Vision Model (MobileNetV2/ResNet50)
    ↓
Disease Detection (e.g., "Early Blight")
    ↓
Vector Store Query ← RAG Pipeline Documents (463 docs)
    ↓
Top-5 Relevant Documents Retrieved
    ↓
Context Injection → Multi-Agent LLM (Groq)
    ↓
Treatment Advice + Source Citations
```

### RAG Pipeline Components

1. **VectorStoreManager** (`vector_store_manager.py`)
   - Manages ChromaDB vector store
   - Performs hybrid search (disease filter + semantic similarity)
   - Metadata filtering by disease, source, content type
   - Query caching for performance

2. **RAG Agent** (`rag_agent.py`)
   - Retrieves relevant documents before LLM generation
   - Injects retrieved context into agent prompts
   - Returns source citations with each response
   - Falls back gracefully if RAG unavailable

3. **Initialization Script** (`init_vector_store.py`)
   - One-time setup script
   - Embeds all documents and persists to disk
   - Optional test mode to verify retrieval

## API Response Changes

The `/predict` endpoint now includes RAG information:

```json
{
  "success": true,
  "disease": "Early Blight",
  "confidence": 0.94,
  "advice": {
    "severity": "Medium",
    "action_plan": "Apply chlorothalonil fungicide...",
    "safety_warning": "Wear PPE including gloves...",
    "weather_advisory": "Current weather: Sunny...",
    "sources": [
      {
        "source": "FAO",
        "content_type": "Treatment",
        "confidence": 0.89
      },
      {
        "source": "UC IPM",
        "content_type": "Prevention",
        "confidence": 0.85
      }
    ],
    "rag_enabled": true
  }
}
```

### New Fields

- **`sources`**: Array of source documents used for recommendations
  - `source`: Organization (FAO, PCAARRD, UC IPM, DA, etc.)
  - `content_type`: Type (Treatment, Symptoms, Prevention, General)
  - `confidence`: Relevance score (0-1)

- **`rag_enabled`**: Boolean indicating if RAG retrieval succeeded
  - `true`: Recommendations based on retrieved documents
  - `false`: Fallback to LLM knowledge only

## Data Sources

The knowledge base contains 463 documents from:

- **FAO** (Food and Agriculture Organization)
- **PCAARRD** (Philippine Council for Agriculture and Resources Research)
- **DA** (Department of Agriculture, Philippines)
- **UC IPM** (University of California Integrated Pest Management)
- **UPLB** (University of the Philippines Los Baños)
- **WorldVeg** (World Vegetable Center)

## Verification

### Check Vector Store Status

```python
from vector_store_manager import VectorStoreManager

manager = VectorStoreManager()
manager.initialize_from_json("./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_combined.json")

# Get stats
stats = manager.get_stats()
print(stats)
# Output: {'status': 'ready', 'document_count': 463, ...}
```

### Test Retrieval

```python
# Retrieve documents for a specific disease
docs = manager.retrieve_documents(
    query="How to treat early blight?",
    disease_filter="Early Blight",
    k=5
)

for doc in docs:
    print(f"Source: {doc['source']}")
    print(f"Type: {doc['content_type']}")
    print(f"Text: {doc['text'][:100]}...")
```

### Monitor Logs

Look for these log messages when RAG is working:

```
✅ Vector store ready with 463 documents
🔍 Searching with filter: {'disease': 'Early Blight'}
✅ Retrieved 5 relevant documents
✅ Advice generated in 3.45s (RAG: ON)
```

## Troubleshooting

### Vector Store Not Found

**Error**: `❌ RAG JSON not found`

**Solution**: Ensure the RAG pipeline has been run and `rag_combined.json` exists:
```bash
ls Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_combined.json
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'chromadb'`

**Solution**: Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```

### RAG Disabled

**Log**: `⚠️ Vector store not available - RAG disabled`

**Behavior**: System falls back to LLM-only mode
- Responses are still generated
- `rag_enabled` will be `false`
- No `sources` array in response

**Solution**: Run initialization:
```bash
python init_vector_store.py
```

### Slow First Query

**Observation**: First query takes 5-10 seconds

**Explanation**: Normal behavior
- Embedding model loads on first use (~80MB download)
- ChromaDB initializes collections
- Subsequent queries are fast (<1s)

## Performance Tuning

### Retrieval Parameters

Adjust in `rag_agent.py`:

```python
retrieved_context, source_docs = retrieve_context(
    disease_name, 
    k=5  # Number of documents to retrieve (default: 5)
)
```

- **k=3**: Faster, less context
- **k=5**: Balanced (recommended)
- **k=10**: More context, higher token usage

### Confidence Threshold

Adjust minimum document confidence in `vector_store_manager.py`:

```python
docs = vector_store.retrieve_documents(
    query=query,
    disease_filter=disease_filter,
    k=k,
    min_confidence=0.3  # Minimum relevance score (0-1)
)
```

- **0.0**: Include all results
- **0.3**: Default, balanced filtering
- **0.5**: Strict, high-quality only

### Caching

The system uses two levels of caching:

1. **Query Cache** (in `VectorStoreManager`)
   - Caches retrieval results per query
   - Speeds up repeated queries

2. **Advice Cache** (in `rag_agent.py`)
   - Caches full LLM responses
   - Saves API calls and latency

Clear cache by restarting the backend.

## Advanced Usage

### Rebuild Vector Store

Force rebuild from source documents:

```bash
python init_vector_store.py --rebuild
```

Use when:
- RAG documents have been updated
- Vector store is corrupted
- Want to change embedding model

### Metadata Search

Search by metadata without semantic search:

```python
# Find all treatment documents from FAO
docs = manager.search_by_metadata(
    source="FAO",
    content_type="Treatment",
    limit=10
)

# Find all late blight documents
docs = manager.search_by_metadata(
    disease="Late Blight",
    limit=20
)
```

### Direct Vector Store Access

```python
# Get raw ChromaDB collection
collection = manager.vectorstore._collection

# Query directly
results = collection.query(
    query_texts=["fungicide treatment"],
    n_results=5,
    where={"disease": "Early Blight"}
)
```

## Integration with Frontend

The frontend can display source citations to build user trust:

```jsx
// Example React component
{advice.rag_enabled && (
  <div className="sources">
    <h4>📚 Information Sources</h4>
    {advice.sources.map((source, i) => (
      <span key={i} className="source-badge">
        {source.source} ({source.content_type})
      </span>
    ))}
  </div>
)}
```

## Monitoring

### Health Check

The `/health` endpoint now includes vector store status:

```bash
curl http://localhost:8000/health
```

### Logs

Enable debug logging for detailed RAG information:

```python
# In rag_agent.py
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

1. ✅ Run `python init_vector_store.py`
2. ✅ Start backend with `python main.py`
3. ✅ Test with frontend or Postman
4. ✅ Verify `rag_enabled: true` in responses
5. ✅ Check `sources` array for citations

## Support

For issues or questions:
- Check logs for error messages
- Verify all dependencies installed
- Ensure GROQ_API_KEY is set
- Run with `--test` flag to diagnose retrieval

---

**Status**: ✅ RAG system fully operational with 463 documents ready for retrieval
