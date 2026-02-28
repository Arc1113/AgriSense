# 2. Methodology

## 2.1 Research Design

This study follows an **applied research design** using a **developmental approach**, wherein a working Retrieval-Augmented Generation (RAG) AI assistant was designed, implemented, and evaluated for its ability to deliver accurate and context-aware treatment recommendations for tomato leaf diseases. The system augments a large language model (LLM) with a domain-specific agricultural knowledge base, ensuring that generated advice is grounded in verified, authoritative information rather than relying solely on the LLM's parametric knowledge.

The development process employed an **iterative prototyping methodology**, where each component of the RAG pipeline — data collection, text processing, vector storage, retrieval, reranking, and response generation — was built and tested incrementally. The system was designed to integrate with the broader AgriSense platform, which uses on-device computer vision (TFLite) for disease detection on a Flutter mobile application; however, this paper focuses exclusively on the RAG-based AI agent responsible for generating treatment recommendations once a disease has been identified.

## 2.2 Data Source

The knowledge base used by the RAG system was constructed from publicly accessible agricultural publications and extension materials from both international and Philippine institutions. The following sources were scraped and processed:

**Global Sources:**

- **FAO (Food and Agriculture Organization of the United Nations)** — PDF manuals and guidelines on tomato disease management.
- **UC IPM (University of California Integrated Pest Management)** — HTML-based pest management guidelines for tomato diseases.

**Philippine Sources:**

- **PCAARRD (Philippine Council for Agriculture, Aquatic and Natural Resources Research and Development)** — Research publications on tomato cultivation and disease management in the Philippine context.
- **DA (Department of Agriculture, Philippines)** — Agricultural extension materials and disease advisories.
- **UPLB (University of the Philippines Los Baños)** — Academic publications and technical bulletins on tomato pathology.

The collected data covers **12 tomato diseases**: Late Blight, Early Blight, Bacterial Spot, Bacterial Speck, Septoria Leaf Spot, Fusarium Wilt, Verticillium Wilt, Powdery Mildew, Tomato Mosaic Virus, Tomato Yellow Leaf Curl Virus, Anthracnose, and Gray Mold. Each document was enriched with metadata including disease name, source institution, content type (symptoms, treatment, or prevention), and region (Philippine or Global).

## 2.3 Tools and Technologies

The following tools, frameworks, and models were used in the development of the RAG AI assistant:

| Component | Technology | Purpose |
|---|---|---|
| **Backend Framework** | FastAPI (Python) | RESTful API server for handling client requests |
| **LLM Provider** | Groq Cloud (LLaMA 3.1 8B Instant) | Large language model for generating natural-language treatment advice |
| **Agent Framework** | CrewAI | Orchestrates a single-agent workflow with structured task prompting and JSON output parsing |
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace) | Converts text chunks into 384-dimensional dense vectors for semantic search |
| **Vector Database** | ChromaDB | Persistent local vector store for storing and querying document embeddings |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model for re-scoring retrieved candidates to improve precision |
| **Document Processing** | Custom Markdown loader with YAML frontmatter parsing | Loads structured Markdown knowledge base files with metadata |
| **Text Chunking** | Custom `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` | Two-stage header-aware chunking with 800-character chunks and 150-character overlap |
| **Web Scraping** | `requests`, `BeautifulSoup`, `pdfplumber` | Polite scraping of HTML pages and PDF extraction from agricultural sources |
| **Weather Integration** | Open-Meteo API (free, no API key) | Fetches real-time 7-day weather forecasts for weather-aware treatment timing |
| **Data Validation** | Pydantic v2 | Structured request/response validation for API endpoints |
| **Deployment** | Docker, Uvicorn | Containerized deployment with ASGI server |

## 2.4 Procedure / Process Flow

The RAG AI assistant follows a multi-stage pipeline that transforms a disease detection input into a comprehensive, weather-aware treatment recommendation. The end-to-end process flow consists of five major phases:

### Phase 1: Knowledge Base Construction (Offline / One-Time)

1. **Web Scraping** — Agricultural documents (HTML pages and PDFs) are scraped from FAO, UC IPM, PCAARRD, DA, and UPLB using polite scraping practices (2-second delays between requests, user-agent identification).
2. **Text Extraction** — Raw text is extracted from PDFs using `pdfplumber` and from HTML using `BeautifulSoup`, with removal of scripts, styles, and navigation elements.
3. **Text Cleaning** — Extracted text is normalized by removing page numbers, headers/footers, excessive whitespace, and special characters.
4. **Intelligent Chunking** — Cleaned documents are chunked using a two-stage strategy:
   - *Stage 1 (Header-Aware Splitting)*: Documents are split along Markdown headers (`#`, `##`, `###`), preserving the hierarchical structure so each chunk retains its section context.
   - *Stage 2 (Recursive Character Splitting)*: Oversized sections are further sub-split using a hierarchy of separators (paragraph → sentence → clause → word boundaries), with a target chunk size of **800 characters** and **150-character overlap** between consecutive chunks to prevent loss of context at chunk boundaries.
5. **Metadata Enrichment** — Each chunk is annotated with metadata: disease name (inferred via keyword matching), source institution, content type (symptoms, treatment, or prevention), and region.
6. **Embedding and Indexing** — All chunks are embedded into 384-dimensional vectors using the `all-MiniLM-L6-v2` sentence transformer model and stored in a **ChromaDB** persistent vector store for fast similarity search.

### Phase 2: Request Reception

7. **Client Request** — The Flutter mobile application sends a POST request to the `/predict` endpoint containing the disease name and detection confidence (as determined by the on-device TFLite model), along with optional location coordinates.
8. **Weather Fetch** — The backend automatically resolves the user's location (via request coordinates, IP geolocation, or a default of Manila, Philippines) and fetches a 7-day weather forecast from the **Open-Meteo API**. This forecast is later injected into the agent's prompt so that treatment timing accounts for upcoming rainfall or adverse conditions.

### Phase 3: Retrieval and Reranking

9. **Query Expansion** — The user's disease name is expanded into a richer query (e.g., `"treatment symptoms prevention management Early Blight tomato"`) with domain-specific synonym terms (e.g., adding "fungicide," "fungal," "lesions" for blight diseases) to improve recall.
10. **Over-Fetching** — The expanded query is used to perform a similarity search against ChromaDB, retrieving **4× the target number of candidates** (e.g., 20 candidates for a target of 5), optionally filtered by disease metadata.
11. **Cross-Encoder Reranking** — The over-fetched candidates are re-scored using a cross-encoder model (`ms-marco-MiniLM-L-6-v2`), which evaluates query–document pairs jointly for higher precision than the bi-encoder embedding alone. The top-*k* results (default *k* = 5) after reranking are selected as the final context documents.

### Phase 4: Response Generation

12. **Context Injection** — The retrieved and reranked documents are formatted into a structured context block and injected into the LLM prompt as the `KNOWLEDGE BASE CONTEXT`, instructing the agent to use them as the primary source of information.
13. **Agent Execution** — A single CrewAI `Agent` (role: *Agricultural Treatment Advisor*) processes a unified `Task` that includes the disease name, current weather, 7-day forecast, and retrieved context. The agent is backed by the **LLaMA 3.1 8B Instant** model hosted on Groq, configured with `temperature=0` for deterministic output. A **30-second timeout** protects against API delays.
14. **Structured Output Parsing** — The agent is prompted to return a JSON object with four keys: `severity` (Low/Medium/High), `action_plan` (2–3 sentence treatment plan), `safety_warning` (PPE and harvest safety interval), and `weather_advisory` (weather-specific timing advice). The response is parsed with regex-based JSON extraction and validated; if parsing fails, a fallback knowledge base of hardcoded treatments is used.

### Phase 5: Response Delivery

15. **Source Citation** — The response is enriched with source citations listing the institution, content type, and confidence score for each retrieved document, along with a `rag_enabled` flag indicating whether the knowledge base was successfully used.
16. **API Response** — The complete `PredictionResponse` (disease name, confidence, treatment advice, weather data, source citations, and response time) is returned to the Flutter client as a structured JSON payload for display in the mobile application.

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AGRISENSE RAG PROCESS FLOW                       │
└─────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │  PHASE 1: KNOWLEDGE BASE CONSTRUCTION (Offline)              │
  │                                                              │
  │  FAO / UC IPM / PCAARRD / DA / UPLB                          │
  │       │                                                      │
  │       ▼                                                      │
  │  Web Scraping (HTML + PDF)                                   │
  │       │                                                      │
  │       ▼                                                      │
  │  Text Extraction → Cleaning → Header-Aware Chunking          │
  │  (800-char chunks, 150-char overlap)                         │
  │       │                                                      │
  │       ▼                                                      │
  │  Embedding (all-MiniLM-L6-v2) → ChromaDB Vector Store       │
  └──────────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  PHASE 2: REQUEST RECEPTION                                  │
  │                                                              │
  │  Flutter App ──POST /predict──▶ FastAPI Backend              │
  │  (disease name + confidence)                                 │
  │       │                                                      │
  │       ▼                                                      │
  │  Auto-fetch 7-day weather forecast (Open-Meteo API)          │
  └──────────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  PHASE 3: RETRIEVAL & RERANKING                              │
  │                                                              │
  │  Query Expansion → Over-fetch (4x) from ChromaDB            │
  │       │                                                      │
  │       ▼                                                      │
  │  Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)           │
  │       │                                                      │
  │       ▼                                                      │
  │  Top-5 Relevant Documents                                    │
  └──────────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  PHASE 4: RESPONSE GENERATION                                │
  │                                                              │
  │  Context + Weather + Disease ──▶ CrewAI Agent                │
  │       │                         (LLaMA 3.1 8B, Groq)        │
  │       ▼                                                      │
  │  Structured JSON: severity, action_plan,                     │
  │  safety_warning, weather_advisory                            │
  └──────────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  PHASE 5: RESPONSE DELIVERY                                  │
  │                                                              │
  │  Treatment Advice + Source Citations + Weather Data           │
  │       │                                                      │
  │       ▼                                                      │
  │  JSON Response ──▶ Flutter Mobile App                        │
  └──────────────────────────────────────────────────────────────┘
```
