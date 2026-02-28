# AgriSense RAG Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AgriSense RAG System                            │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   Frontend   │
│   (React)    │
└──────┬───────┘
       │ HTTP POST /predict
       │ (image + weather)
       ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Backend                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  main.py - API Endpoint Handler                                  │   │
│  └────────────────────┬─────────────────────────────────────────────┘   │
│                       │                                                   │
│                       ↓                                                   │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  vision_engine.py                                               │     │
│  │  ┌─────────────────┐  ┌─────────────────┐                      │     │
│  │  │  MobileNetV2    │  │    ResNet50     │                      │     │
│  │  │  (Fast)         │  │    (Accurate)   │                      │     │
│  │  └────────┬────────┘  └────────┬────────┘                      │     │
│  │           │                     │                                │     │
│  │           └──────────┬──────────┘                                │     │
│  │                      │                                           │     │
│  │                Disease Prediction                                │     │
│  │                "Early Blight" (94% confidence)                   │     │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           │                                               │
│                           ↓                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  rag_agent.py - Multi-Agent RAG System                          │    │
│  │                                                                   │    │
│  │  ┌───────────────────────────────────────────────────────┐      │    │
│  │  │  1. Retrieve Context (retrieve_context)               │      │    │
│  │  │     ↓                                                  │      │    │
│  │  │     Query: "treatment symptoms prevention Early..."   │      │    │
│  │  │     Disease Filter: "Early Blight"                    │      │    │
│  │  └────────────────────┬──────────────────────────────────┘      │    │
│  │                       │                                          │    │
│  │                       ↓                                          │    │
│  │  ┌────────────────────────────────────────────────────┐         │    │
│  │  │  vector_store_manager.py                           │         │    │
│  │  │                                                     │         │    │
│  │  │  ┌──────────────────────────────────────────┐     │         │    │
│  │  │  │  ChromaDB Vector Store                   │     │         │    │
│  │  │  │  ┌────────────────────────────────┐     │     │         │    │
│  │  │  │  │  463 Embedded Documents        │     │     │         │    │
│  │  │  │  │                                 │     │     │         │    │
│  │  │  │  │  ┌──────────┬──────────┬───┐  │     │     │         │    │
│  │  │  │  │  │ FAO (89) │PCAARRD   │...│  │     │     │         │    │
│  │  │  │  │  │          │  (142)   │   │  │     │     │         │    │
│  │  │  │  │  └──────────┴──────────┴───┘  │     │     │         │    │
│  │  │  │  └────────────────────────────────┘     │     │         │    │
│  │  │  │                                          │     │         │    │
│  │  │  │  Hybrid Search:                         │     │         │    │
│  │  │  │  • Semantic Similarity (embeddings)     │     │         │    │
│  │  │  │  • Exact Disease Filter                 │     │         │    │
│  │  │  │  • Metadata Filtering (source, type)    │     │         │    │
│  │  │  └──────────────────────────────────────────┘     │         │    │
│  │  │                                                     │         │    │
│  │  │  Returns Top-5 Documents:                          │         │    │
│  │  │  [                                                  │         │    │
│  │  │    {text: "...", source: "FAO", type: "Treatment"},│         │    │
│  │  │    {text: "...", source: "UC IPM", type: "Symp"}, │         │    │
│  │  │    ...                                              │         │    │
│  │  │  ]                                                  │         │    │
│  │  └────────────────────┬───────────────────────────────┘         │    │
│  │                       │                                          │    │
│  │                       ↓                                          │    │
│  │  ┌────────────────────────────────────────────────────┐         │    │
│  │  │  2. Context Injection                              │         │    │
│  │  │     ↓                                               │         │    │
│  │  │     Format documents into context string:          │         │    │
│  │  │     "=== RELEVANT AGRICULTURAL KNOWLEDGE ==="      │         │    │
│  │  │     "Source: FAO | Type: Treatment"                │         │    │
│  │  │     "Apply chlorothalonil fungicide..."            │         │    │
│  │  └────────────────────┬───────────────────────────────┘         │    │
│  │                       │                                          │    │
│  │                       ↓                                          │    │
│  │  ┌────────────────────────────────────────────────────┐         │    │
│  │  │  3. Multi-Agent LLM (CrewAI)                       │         │    │
│  │  │                                                     │         │    │
│  │  │  ┌────────────────────────────────────────┐       │         │    │
│  │  │  │  Senior Pathologist Agent              │       │         │    │
│  │  │  │  • Reads retrieved documents            │       │         │    │
│  │  │  │  • Analyzes disease                     │       │         │    │
│  │  │  │  • Identifies treatments                │       │         │    │
│  │  │  └────────────────┬───────────────────────┘       │         │    │
│  │  │                   │                                │         │    │
│  │  │                   ↓                                │         │    │
│  │  │  ┌────────────────────────────────────────┐       │         │    │
│  │  │  │  Field Specialist Agent                │       │         │    │
│  │  │  │  • Adapts for weather                   │       │         │    │
│  │  │  │  • Adds safety guidelines               │       │         │    │
│  │  │  │  • Provides timing advice               │       │         │    │
│  │  │  └────────────────┬───────────────────────┘       │         │    │
│  │  │                   │                                │         │    │
│  │  │                   ↓                                │         │    │
│  │  │         JSON Response Generated                    │         │    │
│  │  └────────────────────┬───────────────────────────────┘         │    │
│  │                       │                                          │    │
│  │                       ↓                                          │    │
│  │  ┌────────────────────────────────────────────────────┐         │    │
│  │  │  4. Add Source Citations                           │         │    │
│  │  │     ↓                                               │         │    │
│  │  │     Append metadata from retrieved documents:      │         │    │
│  │  │     sources: [                                      │         │    │
│  │  │       {source: "FAO", type: "Treatment", conf: .89}│         │    │
│  │  │     ]                                               │         │    │
│  │  │     rag_enabled: true                               │         │    │
│  │  └────────────────────┬───────────────────────────────┘         │    │
│  │                       │                                          │    │
│  │                       ↓                                          │    │
│  │           Complete Advice Response                              │    │
│  └───────────────────────┬──────────────────────────────────────────┘   │
│                          │                                               │
└──────────────────────────┼───────────────────────────────────────────────┘
                           │
                           ↓
                 ┌─────────────────────┐
                 │  JSON Response      │
                 │  {                  │
                 │    disease: "...",  │
                 │    confidence: ..., │
                 │    advice: {        │
                 │      severity: ..., │
                 │      action_plan,   │
                 │      sources: [...],│
                 │      rag_enabled    │
                 │    }                │
                 │  }                  │
                 └─────────┬───────────┘
                           │
                           ↓
                   ┌───────────────┐
                   │   Frontend    │
                   │   Displays    │
                   │   Results +   │
                   │   Citations   │
                   └───────────────┘
```

## Data Flow Sequence

```
1. Image Upload
   └─→ Vision Model (MobileNetV2/ResNet50)
       └─→ Prediction: "Early Blight" (0.94)

2. RAG Retrieval
   └─→ Query Construction:
       ├─ Semantic: "treatment symptoms prevention Early Blight"
       ├─ Disease Filter: "Early Blight"
       └─ Confidence: min 0.3
   
   └─→ Vector Store Search (ChromaDB):
       ├─ Embed query using HuggingFace
       ├─ Similarity search (HNSW index)
       ├─ Filter by metadata
       └─→ Top-5 Documents Retrieved:
           ├─ FAO: "Apply chlorothalonil..." (0.89)
           ├─ UC IPM: "Symptoms include..." (0.85)
           ├─ PCAARRD: "Prevention methods..." (0.82)
           └─ ...

3. Context Injection
   └─→ Format Documents:
       ├─ Add headers and separators
       ├─ Include source attribution
       └─→ Inject into Agent Prompts

4. Multi-Agent Generation
   └─→ Senior Pathologist:
       ├─ Reads retrieved context
       ├─ Analyzes disease severity
       └─→ Recommends treatments
   
   └─→ Field Specialist:
       ├─ Reviews pathologist advice
       ├─ Adapts for weather
       ├─ Adds safety guidelines
       └─→ Generates JSON response

5. Response Enhancement
   └─→ Add Source Citations:
       ├─ Extract metadata from docs
       ├─ Add confidence scores
       └─→ Set rag_enabled: true

6. Return to Frontend
   └─→ Complete Response:
       ├─ Disease prediction
       ├─ Treatment advice
       ├─ Source citations
       └─ RAG status indicator
```

## Vector Store Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   ChromaDB Vector Store                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Collection: agrisense_kb                                │  │
│  │                                                           │  │
│  │  Documents: 463                                          │  │
│  │  Dimensions: 384 (sentence-transformers/all-MiniLM-L6-v2)│  │
│  │  Index: HNSW (fast approximate search)                   │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Document Structure:                               │  │  │
│  │  │                                                     │  │  │
│  │  │  {                                                  │  │  │
│  │  │    id: "chunk_001",                                │  │  │
│  │  │    embedding: [0.23, -0.15, ..., 0.08],  // 384-d │  │  │
│  │  │    text: "Early blight is caused by...",           │  │  │
│  │  │    metadata: {                                      │  │  │
│  │  │      disease: "Early Blight",                      │  │  │
│  │  │      source: "FAO",                                │  │  │
│  │  │      content_type: "Treatment",                    │  │  │
│  │  │      confidence: 0.89,                             │  │  │
│  │  │      region: "Global"                              │  │  │
│  │  │    }                                                │  │  │
│  │  │  }                                                  │  │  │
│  │  │                                                     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  Query Process:                                           │  │
│  │  1. Embed query text → 384-d vector                      │  │
│  │  2. HNSW search for similar vectors                      │  │
│  │  3. Filter by metadata (disease, source, etc.)           │  │
│  │  4. Return top-k results sorted by similarity            │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Persistence: ./vector_store/                                   │
│  ├── chroma.sqlite3          (metadata database)                │
│  └── collections/             (embedded vectors)                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Embedding Pipeline

```
Document Text
    ↓
┌───────────────────────────────────────────┐
│  Sentence Transformers                    │
│  Model: all-MiniLM-L6-v2                  │
│  Size: ~80 MB                              │
│  Speed: ~1000 docs/second                  │
└───────────────┬───────────────────────────┘
                ↓
        384-dimensional vector
        [0.23, -0.15, 0.08, ..., 0.12]
                ↓
        Stored in ChromaDB
                ↓
        Indexed with HNSW
                ↓
        Fast similarity search
```

## Hybrid Search Strategy

```
User Query: "How to treat early blight?"
         ↓
┌─────────────────────────────────────────────┐
│  1. Semantic Search                         │
│     • Embed query → 384-d vector            │
│     • Find similar document vectors         │
│     • Cosine similarity ranking             │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  2. Exact Disease Filter                    │
│     • Metadata filter: disease="Early..."  │
│     • Ensures relevant disease documents    │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  3. Confidence Threshold                    │
│     • Filter: confidence >= 0.3             │
│     • Removes low-quality matches           │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  4. Top-K Selection                         │
│     • Sort by similarity score              │
│     • Return top 5 documents                │
└─────────────────┬───────────────────────────┘
                  ↓
          Relevant Documents
```

## Graceful Degradation

```
                 ┌─────────────────┐
                 │  API Request    │
                 └────────┬────────┘
                          │
                          ↓
              ┌───────────────────────┐
              │  Vector Store Check   │
              └───────┬───────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
    Available              Unavailable
          │                       │
          ↓                       ↓
┌─────────────────────┐  ┌──────────────────────┐
│  RAG Mode           │  │  Fallback Mode       │
│  • Retrieve docs    │  │  • Use LLM only      │
│  • Inject context   │  │  • Log warning       │
│  • Add citations    │  │  • Continue normally │
│  rag_enabled: true  │  │  rag_enabled: false  │
└─────────┬───────────┘  └──────────┬───────────┘
          │                         │
          └───────────┬─────────────┘
                      │
                      ↓
              ┌───────────────┐
              │   Response    │
              │   Generated   │
              └───────────────┘
```

## Cache Layers

```
┌─────────────────────────────────────────────────────────┐
│  Request: disease="Early Blight", weather="Sunny"      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  Advice Cache Check  │  <-- In-memory cache
              └──────┬───────────────┘
                     │
         ┌───────────┴─────────────┐
         │                         │
    Cache HIT                 Cache MISS
         │                         │
         ↓                         ↓
    Return cached          ┌──────────────────┐
    result (<1ms)          │  Query Cache     │  <-- Vector store cache
                           └──────┬───────────┘
                                  │
                      ┌───────────┴─────────────┐
                      │                         │
                 Cache HIT                 Cache MISS
                      │                         │
                      ↓                         ↓
              Return cached             Perform vector
              documents (10ms)          search (1-2s)
                      │                         │
                      └────────────┬────────────┘
                                   │
                                   ↓
                          Generate LLM response
                          Cache result
                          Return (<5s)
```

---

**Legend:**
- `┌─┐ └─┘` = Components/Modules
- `→ ↓` = Data flow
- `...` = Processing steps
