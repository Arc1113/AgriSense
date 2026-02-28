"""
Example Usage: Loading RAG Data into Vector Stores
Demonstrates how to use the pipeline output with popular RAG frameworks.
"""

import json
from pathlib import Path

# Example 1: Load the RAG data
print("=" * 70)
print("LOADING RAG DATA")
print("=" * 70)

rag_file = Path('processed/rag_json/rag_documents.json')

if rag_file.exists():
    with open(rag_file, 'r', encoding='utf-8') as f:
        rag_data = json.load(f)
    
    print(f"Loaded {rag_data['total_documents']} documents")
    print(f"Created: {rag_data['created_at']}")
    print(f"Version: {rag_data['version']}")
    
    # Show first document
    if rag_data['documents']:
        first_doc = rag_data['documents'][0]
        print("\n" + "=" * 70)
        print("SAMPLE DOCUMENT")
        print("=" * 70)
        print(f"ID: {first_doc['id']}")
        print(f"Text: {first_doc['text'][:200]}...")
        print(f"Metadata: {json.dumps(first_doc['metadata'], indent=2)}")
else:
    print(f"RAG file not found: {rag_file}")
    print("Please run the pipeline first: python run_pipeline.py")
    exit(1)

print("\n" + "=" * 70)
print("USAGE EXAMPLES")
print("=" * 70)

# Example 2: Filter by disease
print("\n1. Filter documents by disease:")
print("-" * 70)
disease_filter = "Late Blight"
filtered_docs = [
    doc for doc in rag_data['documents']
    if doc['metadata']['disease'] == disease_filter
]
print(f"Found {len(filtered_docs)} documents about {disease_filter}")

# Example 3: Filter by content type
print("\n2. Filter by content type:")
print("-" * 70)
treatment_docs = [
    doc for doc in rag_data['documents']
    if doc['metadata']['content_type'] == 'Treatment'
]
print(f"Found {len(treatment_docs)} treatment documents")

# Example 4: Filter by region
print("\n3. Filter by region:")
print("-" * 70)
ph_docs = [
    doc for doc in rag_data['documents']
    if doc['metadata']['region'] == 'PH'
]
print(f"Found {len(ph_docs)} Philippines-specific documents")

# Example 5: Statistics by source
print("\n4. Documents by source:")
print("-" * 70)
sources = {}
for doc in rag_data['documents']:
    source = doc['metadata']['source']
    sources[source] = sources.get(source, 0) + 1

for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
    print(f"  {source}: {count}")

# Example 6: LangChain integration (commented - uncomment if using LangChain)
print("\n5. LangChain Integration Example:")
print("-" * 70)
print("""
# Uncomment and install: pip install langchain

from langchain.docstore.document import Document
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

# Convert to LangChain documents
documents = [
    Document(
        page_content=doc['text'],
        metadata=doc['metadata']
    )
    for doc in rag_data['documents']
]

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(documents, embeddings)

# Query
query = "How to treat late blight in tomatoes?"
results = vectorstore.similarity_search(query, k=5)
""")

# Example 7: LlamaIndex integration (commented)
print("\n6. LlamaIndex Integration Example:")
print("-" * 70)
print("""
# Uncomment and install: pip install llama-index

from llama_index.core import Document, VectorStoreIndex

# Convert to LlamaIndex documents
documents = [
    Document(
        text=doc['text'],
        metadata=doc['metadata'],
        doc_id=doc['id']
    )
    for doc in rag_data['documents']
]

# Create index
index = VectorStoreIndex.from_documents(documents)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What are symptoms of early blight?")
print(response)
""")

# Example 8: Chroma integration (commented)
print("\n7. Chroma Integration Example:")
print("-" * 70)
print("""
# Uncomment and install: pip install chromadb

import chromadb
from chromadb.utils import embedding_functions

# Initialize Chroma
client = chromadb.Client()
collection = client.create_collection(
    name="tomato_diseases",
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

# Add documents
texts = [doc['text'] for doc in rag_data['documents']]
metadatas = [doc['metadata'] for doc in rag_data['documents']]
ids = [doc['id'] for doc in rag_data['documents']]

collection.add(
    documents=texts,
    metadatas=metadatas,
    ids=ids
)

# Query
results = collection.query(
    query_texts=["How to prevent tomato diseases?"],
    n_results=5
)
""")

print("\n" + "=" * 70)
print("READY FOR RAG!")
print("=" * 70)
print("Your data is now ready to use with any RAG framework.")
print("Choose your preferred framework and follow the examples above.")
