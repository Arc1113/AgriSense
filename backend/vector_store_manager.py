"""
AgriSense Vector Store Manager
Handles document embedding, retrieval, and semantic search for RAG pipeline

Features:
- ChromaDB for persistent vector storage
- Hybrid search: exact disease matching + semantic similarity
- Metadata filtering by disease, source, content type
- Automatic initialization from processed RAG documents
- Query caching for performance
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Disable ChromaDB telemetry (prevents connection errors)
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_community.vectorstores.utils import filter_complex_metadata

logger = logging.getLogger("VectorStore")


class VectorStoreManager:
    """Manages vector store operations for agricultural knowledge retrieval"""
    
    def __init__(
        self, 
        persist_directory: str = "./vector_store",
        collection_name: str = "agrisense_kb",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize Vector Store Manager
        
        Args:
            persist_directory: Directory to store ChromaDB data
            collection_name: Name of the ChromaDB collection
            embedding_model: HuggingFace embedding model name
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Initialize embeddings
        logger.info(f"🧠 Loading embedding model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize vector store
        self.vectorstore: Optional[Chroma] = None
        self._query_cache: Dict[str, List[Document]] = {}
        
    def initialize_from_json(self, json_path: str, force_rebuild: bool = False) -> bool:
        """
        Load RAG documents from JSON and create/update vector store
        
        Args:
            json_path: Path to rag_documents.json file
            force_rebuild: If True, rebuild even if vectorstore exists
            
        Returns:
            True if successful, False otherwise
        """
        # Check if vector store already exists
        persist_path = Path(self.persist_directory)
        if persist_path.exists() and not force_rebuild:
            logger.info(f"✅ Loading existing vector store from {self.persist_directory}")
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            doc_count = self.vectorstore._collection.count()
            logger.info(f"📚 Vector store loaded with {doc_count} documents")
            return True
        
        # Load RAG JSON
        if not os.path.exists(json_path):
            logger.error(f"❌ RAG JSON not found at: {json_path}")
            return False
        
        logger.info(f"📖 Loading RAG documents from: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                rag_data = json.load(f)
            
            documents = rag_data.get('documents', [])
            if not documents:
                logger.error("❌ No documents found in RAG JSON")
                return False
            
            logger.info(f"📄 Found {len(documents)} documents to embed")
            
            # Convert to LangChain Document objects
            langchain_docs = []
            for doc in documents:
                # Extract metadata
                metadata = doc.get('metadata', {})
                metadata['doc_id'] = doc.get('id', 'unknown')
                
                # Create Document
                langchain_docs.append(Document(
                    page_content=doc.get('text', ''),
                    metadata=metadata
                ))
            
            # Filter complex metadata (remove lists, dicts, etc.)
            logger.info("🧹 Filtering complex metadata for ChromaDB compatibility...")
            langchain_docs = filter_complex_metadata(langchain_docs)
            
            # Create vector store
            logger.info("🔄 Embedding documents and creating vector store...")
            logger.info("⏳ This may take 2-3 minutes for 463 documents...")
            
            self.vectorstore = Chroma.from_documents(
                documents=langchain_docs,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )
            
            doc_count = self.vectorstore._collection.count()
            logger.info(f"✅ Vector store created with {doc_count} documents")
            logger.info(f"💾 Persisted to: {self.persist_directory}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing vector store: {e}")
            return False
    
    def retrieve_documents(
        self, 
        query: str, 
        disease_filter: Optional[str] = None,
        k: int = 5,
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents using hybrid search
        
        Args:
            query: Search query (e.g., "treatment for early blight")
            disease_filter: Optional disease name to filter by (e.g., "Early Blight")
            k: Number of documents to retrieve
            min_confidence: Minimum disease confidence score (0-1)
            
        Returns:
            List of documents with text, metadata, and relevance scores
        """
        if not self.vectorstore:
            logger.warning("⚠️ Vector store not initialized")
            return []
        
        # Check cache
        cache_key = f"{query}:{disease_filter}:{k}"
        if cache_key in self._query_cache:
            logger.info(f"📦 Using cached results for: {query[:50]}...")
            return self._format_documents(self._query_cache[cache_key])
        
        try:
            # Build metadata filter
            filter_dict = {}
            if disease_filter:
                # Normalize disease name for matching
                disease_normalized = self._normalize_disease_name(disease_filter)
                filter_dict['disease'] = disease_normalized
            
            # Perform similarity search
            if filter_dict:
                logger.info(f"🔍 Searching with filter: {filter_dict}")
                docs = self.vectorstore.similarity_search(
                    query, 
                    k=k * 2,  # Get more results for filtering
                    filter=filter_dict
                )
            else:
                logger.info(f"🔍 Searching: {query[:50]}...")
                docs = self.vectorstore.similarity_search(query, k=k)
            
            # Filter by confidence if specified
            if min_confidence > 0:
                filtered_docs = []
                for doc in docs:
                    confidence = doc.metadata.get('disease_confidence', 1.0)
                    if confidence >= min_confidence:
                        filtered_docs.append(doc)
                docs = filtered_docs[:k]
            else:
                docs = docs[:k]
            
            # Cache results
            self._query_cache[cache_key] = docs
            
            logger.info(f"✅ Retrieved {len(docs)} relevant documents")
            
            return self._format_documents(docs)
            
        except Exception as e:
            logger.error(f"❌ Error retrieving documents: {e}")
            return []
    
    def _normalize_disease_name(self, disease: str) -> str:
        """
        Normalize disease name for consistent matching
        
        Args:
            disease: Original disease name (e.g., "Tomato___Early_blight")
            
        Returns:
            Normalized name (e.g., "Early Blight")
        """
        # Remove "Tomato___" prefix if present
        disease = disease.replace("Tomato___", "")
        
        # Replace underscores with spaces
        disease = disease.replace("_", " ")
        
        # Capitalize properly
        disease = disease.title()
        
        return disease
    
    def _format_documents(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """Format retrieved documents for response"""
        formatted = []
        for i, doc in enumerate(docs):
            formatted.append({
                'rank': i + 1,
                'text': doc.page_content,
                'metadata': doc.metadata,
                'source': doc.metadata.get('source', 'Unknown'),
                'disease': doc.metadata.get('disease', 'Unknown'),
                'content_type': doc.metadata.get('content_type', 'Unknown'),
                'confidence': doc.metadata.get('disease_confidence', 1.0)
            })
        return formatted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.vectorstore:
            return {"status": "not_initialized"}
        
        try:
            count = self.vectorstore._collection.count()
            return {
                "status": "ready",
                "document_count": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def search_by_metadata(
        self, 
        disease: Optional[str] = None,
        content_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search documents by metadata only (no semantic search)
        
        Args:
            disease: Filter by disease name
            content_type: Filter by content type (Treatment, Symptoms, Prevention)
            source: Filter by source (FAO, PCAARRD, DA, UC IPM)
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        if not self.vectorstore:
            logger.warning("⚠️ Vector store not initialized")
            return []
        
        try:
            # Build filter
            filter_dict = {}
            if disease:
                filter_dict['disease'] = self._normalize_disease_name(disease)
            if content_type:
                filter_dict['content_type'] = content_type
            if source:
                filter_dict['source'] = source
            
            if not filter_dict:
                logger.warning("⚠️ No filters provided for metadata search")
                return []
            
            # Use similarity search with filter (will return most relevant by default)
            docs = self.vectorstore.similarity_search(
                "",  # Empty query to get documents by filter only
                k=limit,
                filter=filter_dict
            )
            
            return self._format_documents(docs)
            
        except Exception as e:
            logger.error(f"❌ Error in metadata search: {e}")
            return []


# =============================================================================
# Test Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Testing AgriSense Vector Store Manager")
    print("=" * 70)
    
    # Initialize manager
    manager = VectorStoreManager()
    
    # Path to RAG JSON
    rag_json_path = "./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_documents.json"
    
    # Initialize vector store
    print("\n📚 Initializing vector store...")
    success = manager.initialize_from_json(rag_json_path, force_rebuild=False)
    
    if not success:
        print("❌ Failed to initialize vector store")
        exit(1)
    
    # Get stats
    print("\n📊 Vector Store Stats:")
    stats = manager.get_stats()
    print(json.dumps(stats, indent=2))
    
    # Test retrieval
    print("\n🔍 Testing retrieval for 'Early Blight'...")
    results = manager.retrieve_documents(
        query="How to treat early blight on tomatoes?",
        disease_filter="Early Blight",
        k=3
    )
    
    print(f"\n✅ Retrieved {len(results)} documents:")
    for doc in results:
        print(f"\n  📄 Rank {doc['rank']}")
        print(f"     Source: {doc['source']}")
        print(f"     Content Type: {doc['content_type']}")
        print(f"     Confidence: {doc['confidence']:.2f}")
        print(f"     Text: {doc['text'][:150]}...")
    
    print("\n" + "=" * 70)
    print("✅ Test Complete!")
    print("=" * 70)
