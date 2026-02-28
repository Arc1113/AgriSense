# 🌱 AgriSense Backend - RAG-Enhanced Disease Detection API

Advanced FastAPI backend with **Retrieval-Augmented Generation (RAG)** for evidence-based agricultural treatment recommendations.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize RAG System (One-Time)
**Automated:**
```bash
# Windows
setup_rag.bat

# Linux/Mac
chmod +x setup_rag.sh
./setup_rag.sh
```

**Or manually:**
```bash
python init_vector_store.py
```

### 3. Configure Environment
```bash
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```
Get your free API key at: https://console.groq.com

### 4. Start Backend
```bash
python main.py
```

or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test API
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 📁 Project Structure

```
backend/
├── main.py                          # FastAPI server & endpoints
├── vision_engine.py                 # ML models (MobileNetV2, ResNet50)
├── rag_agent.py                     # Multi-agent RAG system (CrewAI)
├── vector_store_manager.py          # ChromaDB vector store management
├── init_vector_store.py             # Vector store initialization script
│
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (API keys)
│
├── setup_rag.sh / .bat              # Automated setup scripts
├── RAG_SETUP.md                     # Complete setup guide (400+ lines)
├── RAG_QUICK_REFERENCE.md           # Quick reference card
├── RAG_IMPLEMENTATION_SUMMARY.md    # Technical implementation details
├── RAG_ARCHITECTURE_DIAGRAM.md      # Visual architecture diagrams
│
├── models/                          # ML model files
│   ├── class_names.json
│   ├── mobilenetv2/
│   └── resnet50/
│
├── vector_store/                    # ChromaDB persistence (auto-generated)
│   ├── chroma.sqlite3
│   └── collections/
│
└── Web_Scraping_for_Agrisense/
    └── rag_pipeline/
        └── processed/
            └── rag_json/
                └── rag_combined.json   # 463 agricultural documents
```

---

## 🎯 Key Features

### 1. **Disease Detection**
- Two ML models: MobileNetV2 (fast) & ResNet50 (accurate)
- 10 tomato disease classes + healthy
- 90%+ accuracy on test set

### 2. **RAG-Enhanced Advice**
- Retrieves from **463 agricultural documents**
- Sources: FAO, PCAARRD, UC IPM, DA, UPLB, WorldVeg
- Evidence-based treatment recommendations
- Source citations for transparency

### 3. **Multi-Agent System**
- **Senior Pathologist**: Analyzes disease & treatments
- **Field Specialist**: Adapts for weather & safety
- Powered by Groq (llama-3.3-70b-versatile)

### 4. **Weather-Aware Recommendations**
- Adjusts advice for Sunny, Rainy, Cloudy, Windy conditions
- Timing recommendations for application
- Safety guidelines (PPE requirements)

### 5. **Graceful Degradation**
- Works even if RAG unavailable (fallback to LLM)
- Caching for fast repeated queries
- Robust error handling

---

## 🔌 API Endpoints

### **POST /predict**
Main prediction endpoint with RAG-enhanced advice.

**Request:**
```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@tomato_leaf.jpg" \
  -F "model=mobile" \
  -F "weather=Sunny"
```

**Response:**
```json
{
  "success": true,
  "disease": "Early Blight",
  "confidence": 0.94,
  "is_healthy": false,
  "model_used": "MobileNetV2",
  "weather": "Sunny",
  "advice": {
    "severity": "Medium",
    "action_plan": "Apply chlorothalonil fungicide at 7-10 day intervals. Remove and destroy heavily infected leaves. Ensure proper plant spacing for air circulation.",
    "safety_warning": "Wear PPE including gloves, goggles, long sleeves, and a mask. Avoid spray drift onto edible parts. Observe a 7-day pre-harvest interval.",
    "weather_advisory": "Current weather: Sunny. Apply fungicide in early morning or late evening to avoid leaf burn. Ideal conditions for application.",
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
      },
      {
        "source": "PCAARRD",
        "content_type": "Symptoms",
        "confidence": 0.82
      }
    ],
    "rag_enabled": true
  },
  "response_time_ms": 3456.78,
  "timestamp": "2026-02-01T10:30:45.123Z"
}
```

### **GET /health**
Health check with system status.

```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "models_loaded": {
    "MobileNetV2": true,
    "ResNet50": true
  },
  "version": "2.0.0"
}
```

### **GET /models/status**
Detailed model information.

### **GET /**
API information and documentation links.

---

## 🧠 RAG System

### How It Works

1. **Disease Detection**: Vision model identifies disease from image
2. **Document Retrieval**: Vector store searches 463 documents for relevant content
3. **Context Injection**: Retrieved documents injected into LLM prompts
4. **Multi-Agent Generation**: AI agents synthesize treatment advice
5. **Source Citations**: Response includes document sources

### Data Sources

**463 documents from:**
- **FAO** (89 docs): Global agricultural best practices
- **PCAARRD** (142 docs): Philippine-specific guidelines
- **UC IPM** (103 docs): Scientific research & IPM strategies
- **DA Philippines** (76 docs): Local agricultural policies
- **UPLB** (28 docs): Academic research
- **WorldVeg** (25 docs): International vegetable production

### Vector Store Details

- **Engine**: ChromaDB (persistent disk storage)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (384-dim)
- **Search**: Hybrid (semantic + metadata filtering)
- **Storage**: ~50-100 MB
- **Performance**: <1s query time (after first load)

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional
LOG_LEVEL=INFO
```

### Retrieval Tuning (in rag_agent.py)

```python
# Number of documents to retrieve (3-10)
retrieved_context, source_docs = retrieve_context(disease_name, k=5)

# Minimum confidence threshold (0.0-1.0)
docs = vector_store.retrieve_documents(
    query=query,
    k=k,
    min_confidence=0.3
)
```

---

## 🧪 Testing

### Test Vector Store
```bash
python init_vector_store.py --test
```

### Test API
```bash
# Health check
curl http://localhost:8000/health

# Prediction
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_image.jpg" \
  -F "model=mobile" \
  -F "weather=Sunny"
```

### Test RAG Retrieval
```python
from vector_store_manager import VectorStoreManager

manager = VectorStoreManager()
manager.initialize_from_json("./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_combined.json")

# Retrieve documents
docs = manager.retrieve_documents(
    query="How to treat early blight?",
    disease_filter="Early Blight",
    k=5
)

for doc in docs:
    print(f"{doc['source']} - {doc['content_type']}")
    print(f"Confidence: {doc['confidence']:.2f}")
    print(f"Text: {doc['text'][:150]}...\n")
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Vector store init (one-time) | 2-3 minutes |
| First API query | 5-10 seconds |
| Cached queries | <100 ms |
| Fresh queries with RAG | 3-5 seconds |
| Disease detection only | <1 second |

---

## 🐛 Troubleshooting

### Common Issues

**1. Module not found: chromadb**
```bash
pip install -r requirements.txt --force-reinstall
```

**2. Vector store not initialized**
```bash
python init_vector_store.py --rebuild
```

**3. RAG disabled warning**
```
⚠️ Vector store unavailable - RAG disabled
```
- Check if `rag_combined.json` exists
- Run `python init_vector_store.py`
- System still works (fallback mode)

**4. Slow first query**
- Normal: Embedding model downloads on first use (~80MB)
- Subsequent queries are fast

**5. GROQ_API_KEY not set**
```
ValueError: GROQ_API_KEY not found
```
- Create `.env` file with `GROQ_API_KEY=your_key`

---

## 📚 Documentation

- **[RAG_QUICK_REFERENCE.md](RAG_QUICK_REFERENCE.md)**: Quick reference card
- **[RAG_SETUP.md](RAG_SETUP.md)**: Complete setup guide (400+ lines)
- **[RAG_IMPLEMENTATION_SUMMARY.md](RAG_IMPLEMENTATION_SUMMARY.md)**: Technical details
- **[RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md)**: Visual architecture

---

## 🚢 Deployment

### Docker (Recommended)
```bash
docker build -t agrisense-backend .
docker run -p 8000:8000 --env-file .env agrisense-backend
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🔄 Updates & Maintenance

### Rebuild Vector Store
When RAG documents are updated:
```bash
python init_vector_store.py --rebuild
```

### Update Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Clear Cache
Restart the backend to clear:
- Query cache (vector store)
- Advice cache (RAG agent)

---

## 📈 Benefits Over Previous Version

### Before RAG:
❌ Generic advice from LLM pre-trained knowledge  
❌ No source attribution  
❌ May include outdated information  
❌ Limited to training data  

### After RAG:
✅ Evidence-based from 463 curated documents  
✅ Source citations (FAO, PCAARRD, UC IPM, etc.)  
✅ Region-appropriate (Philippine + Global)  
✅ Transparent and verifiable  
✅ Up-to-date agricultural research  

---

## 🎓 Tech Stack

- **FastAPI**: Modern async web framework
- **TensorFlow/Keras**: ML models (MobileNetV2, ResNet50)
- **CrewAI**: Multi-agent orchestration
- **LangChain**: RAG pipeline components
- **ChromaDB**: Vector database
- **HuggingFace**: Embedding models
- **Groq**: LLM inference (llama-3.3-70b)

---

## 📜 API Version History

### v2.0.0 (Current) - RAG Implementation
- ✅ Added RAG retrieval from 463 documents
- ✅ Source citations in responses
- ✅ ChromaDB vector store
- ✅ Hybrid search (semantic + filtering)
- ✅ Graceful degradation

### v1.0.0 - Initial Release
- Disease detection with ML models
- Multi-agent treatment advice
- Weather-aware recommendations

---

## 🤝 Contributing

When modifying the RAG system:

1. **Vector Store**: Changes to `vector_store_manager.py`
2. **RAG Agent**: Changes to `rag_agent.py`
3. **API**: Changes to `main.py`
4. **Test**: Run `python init_vector_store.py --test`
5. **Rebuild**: Run `python init_vector_store.py --rebuild` if needed

---

## 📞 Support

For issues or questions:
- Check logs for detailed error messages
- Review documentation files
- Verify all dependencies installed
- Ensure GROQ_API_KEY is set
- Test with `--test` flag

---

## ✅ Status

**RAG System**: ✅ Fully Operational  
**Documents**: 463 embedded and indexed  
**Sources**: FAO, PCAARRD, UC IPM, DA, UPLB, WorldVeg  
**Mode**: Hybrid (RAG + LLM with graceful fallback)  
**API Version**: 2.0.0  

---

**Built with ❤️ for sustainable agriculture**
