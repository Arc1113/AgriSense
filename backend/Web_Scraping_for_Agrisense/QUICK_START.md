# 🚀 Quick Start - Using Your RAG Data

## ✅ Pipeline Complete!

Your RAG pipeline has successfully processed **463 documents** with rich metadata.

**Output File:** `rag_pipeline/processed/rag_json/rag_documents.json` (1.12 MB)

---

## 📊 Dataset Statistics

### Documents by Disease
- **Late Blight**: 32 documents (Phytophthora infestans)
- **Early Blight**: 26 documents (Alternaria solani)
- **Fusarium Wilt**: 23 documents (Fusarium oxysporum)
- **Tomato Mosaic Virus**: 14 documents
- **Verticillium Wilt**: 12 documents
- **Bacterial Speck**: 9 documents
- **TYLCV**: 9 documents
- **General/Other**: 324 documents

### Content Distribution
- **Treatment Guides**: 271 documents (58.5%)
- **Symptom Descriptions**: 80 documents (17.3%)
- **General Information**: 60 documents (13.0%)
- **Prevention Methods**: 52 documents (11.2%)

### Data Sources
- **FAO**: 335 documents (72.4%)
- **UC IPM**: 10 documents
- **PCAARRD**: 4 documents
- **DA (Dept of Agriculture)**: 3 documents
- **UPLB**: 2 documents
- **Unknown**: 109 documents

### Geographic Coverage
- **Global**: 450 documents
- **Philippines (PH)**: 13 documents

---

## 🔍 Sample Document Structure

```json
{
  "id": "avrdc_field_grown_tomato_production_guide_south_asia_chunk_66",
  "text": "Late blight (Phytophthora infestans) This will initially appear...",
  "metadata": {
    "crop": "Tomato",
    "disease": "Late Blight",
    "disease_scientific_name": "Phytophthora infestans",
    "disease_confidence": 1.0,
    "region": "Global",
    "source": "FAO",
    "content_type": "Treatment",
    "language": "English",
    "token_count": 478,
    "all_diseases_detected": [
      {"name": "Late Blight", "confidence": 1.0}
    ]
  }
}
```

---

## 💡 How to Use This Data

### 1. Load with Python

```python
import json

# Load RAG documents
with open('rag_pipeline/processed/rag_json/rag_documents.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total documents: {data['total_documents']}")
documents = data['documents']

# Filter by disease
late_blight_docs = [
    doc for doc in documents 
    if doc['metadata']['disease'] == 'Late Blight'
]
print(f"Late Blight documents: {len(late_blight_docs)}")

# Filter by content type
treatment_docs = [
    doc for doc in documents 
    if doc['metadata']['content_type'] == 'Treatment'
]
print(f"Treatment documents: {len(treatment_docs)}")

# Get high-confidence disease detections
high_conf = [
    doc for doc in documents 
    if doc['metadata']['disease_confidence'] >= 0.8
]
print(f"High confidence: {len(high_conf)}")
```

### 2. Use with LangChain

```python
from langchain.docstore.document import Document
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
import json

# Load your RAG data
with open('rag_pipeline/processed/rag_json/rag_documents.json', 'r', encoding='utf-8') as f:
    rag_data = json.load(f)

# Convert to LangChain documents
langchain_docs = []
for doc in rag_data['documents']:
    langchain_doc = Document(
        page_content=doc['text'],
        metadata=doc['metadata']
    )
    langchain_docs.append(langchain_doc)

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(langchain_docs, embeddings)

# Query
results = vectorstore.similarity_search(
    "How to treat late blight in tomatoes?", 
    k=5,
    filter={"disease": "Late Blight"}
)

for result in results:
    print(f"Disease: {result.metadata['disease']}")
    print(f"Source: {result.metadata['source']}")
    print(f"Text: {result.page_content[:200]}...")
    print()
```

### 3. Use with LlamaIndex

```python
from llama_index import Document, VectorStoreIndex
import json

# Load RAG data
with open('rag_pipeline/processed/rag_json/rag_documents.json', 'r', encoding='utf-8') as f:
    rag_data = json.load(f)

# Convert to LlamaIndex documents
documents = []
for doc in rag_data['documents']:
    llama_doc = Document(
        text=doc['text'],
        metadata=doc['metadata'],
        id_=doc['id']
    )
    documents.append(llama_doc)

# Create index
index = VectorStoreIndex.from_documents(documents)

# Query
query_engine = index.as_query_engine()
response = query_engine.query(
    "What are the symptoms of early blight in tomatoes?"
)
print(response)
```

### 4. Use with Chroma

```python
import chromadb
from chromadb.config import Settings
import json

# Initialize Chroma
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

# Create collection
collection = client.create_collection(
    name="tomato_diseases",
    metadata={"description": "Tomato disease treatment RAG data"}
)

# Load data
with open('rag_pipeline/processed/rag_json/rag_documents.json', 'r', encoding='utf-8') as f:
    rag_data = json.load(f)

# Add to Chroma
for doc in rag_data['documents']:
    collection.add(
        ids=[doc['id']],
        documents=[doc['text']],
        metadatas=[doc['metadata']]
    )

# Query
results = collection.query(
    query_texts=["fungicide for late blight"],
    n_results=5,
    where={"disease": "Late Blight"}
)

for i, result in enumerate(results['documents'][0]):
    print(f"{i+1}. {result[:200]}...")
    print(f"   Source: {results['metadatas'][0][i]['source']}")
    print()
```

---

## 🔎 Common Query Examples

### By Disease
```python
# Get all Late Blight documents
late_blight = [d for d in documents if d['metadata']['disease'] == 'Late Blight']

# Get multiple diseases
fungal_diseases = [
    d for d in documents 
    if d['metadata']['disease'] in ['Late Blight', 'Early Blight', 'Fusarium Wilt']
]
```

### By Content Type
```python
# Get treatment information
treatments = [d for d in documents if d['metadata']['content_type'] == 'Treatment']

# Get symptoms
symptoms = [d for d in documents if d['metadata']['content_type'] == 'Symptoms']
```

### By Source
```python
# Get FAO documents
fao_docs = [d for d in documents if d['metadata']['source'] == 'FAO']

# Get Philippine-specific
ph_docs = [d for d in documents if d['metadata']['region'] == 'PH']
```

### By Confidence
```python
# High-confidence detections only
high_conf = [
    d for d in documents 
    if d['metadata']['disease_confidence'] >= 0.8 
    and d['metadata']['disease'] != 'General'
]
```

---

## 🎯 Building a RAG Chatbot

```python
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
import json

# 1. Load data
with open('rag_pipeline/processed/rag_json/rag_documents.json', 'r', encoding='utf-8') as f:
    rag_data = json.load(f)

# 2. Create documents
from langchain.docstore.document import Document
docs = [
    Document(page_content=d['text'], metadata=d['metadata'])
    for d in rag_data['documents']
]

# 3. Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(docs, embeddings)

# 4. Create QA chain
llm = ChatOpenAI(temperature=0)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
)

# 5. Ask questions!
questions = [
    "What are the symptoms of late blight in tomatoes?",
    "How do I treat early blight?",
    "What fungicides work for Phytophthora infestans?",
    "What are prevention methods for tomato diseases?"
]

for question in questions:
    print(f"\nQ: {question}")
    answer = qa_chain.run(question)
    print(f"A: {answer}")
```

---

## 📈 Next Steps

1. **Test RAG Application**
   - Load data into your preferred vector database
   - Test semantic search with sample queries
   - Evaluate retrieval accuracy

2. **Add More Data**
   - Edit `scrape_html.py` to add more URLs
   - Edit `scrape_pdfs.py` to add PDF sources
   - Run: `py run_pipeline.py` (without --skip-scraping)

3. **Customize Metadata**
   - Edit `add_metadata.py` to add custom fields
   - Modify `disease_detector.py` to add more diseases
   - Adjust confidence thresholds

4. **Deploy**
   - Build a chatbot interface
   - Create an API endpoint
   - Integrate with existing systems

---

## 🛠️ Troubleshooting

### Issue: Too many "General" documents
**Solution:** Documents without clear disease mentions are tagged as "General". To improve:
- Add more disease keywords to `disease_detector.py`
- Lower confidence threshold in metadata enrichment
- Filter out General documents in your application

### Issue: Need more Philippines-specific data
**Solution:** 
- Add Philippine sources (DA, PCAARRD, BAR, UPLB) to scrapers
- Tag documents with region metadata
- Use geographic filters in queries

### Issue: Want scientific names for all diseases
**Solution:** All detected diseases include scientific names in metadata when available:
```python
# Access scientific name
doc['metadata']['disease_scientific_name']  # e.g., "Phytophthora infestans"
```

---

## 📚 Documentation

- **Full Pipeline Guide**: `rag_pipeline/README.md`
- **Architecture Details**: `rag_pipeline/ARCHITECTURE.md`
- **Getting Started**: `rag_pipeline/GETTING_STARTED.md`
- **Refactoring Features**: `rag_pipeline/REFACTORING_GUIDE.md`

---

## ✨ Your Data is Ready!

You now have **463 production-ready RAG documents** with:
- ✅ Rich metadata (disease, source, region, content type)
- ✅ Scientific names for diseases
- ✅ Confidence scores
- ✅ Token counts
- ✅ Multi-disease detection
- ✅ Optimized chunk sizes (~478 tokens average)

**Start building your RAG application now!** 🚀
