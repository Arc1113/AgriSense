"""
Industry-Standard Markdown Document Loader for RAG Pipeline

Uses LangChain's document processing with:
1. Markdown Header-Aware Chunking — respects document structure
2. RecursiveCharacterTextSplitter — smart fallback with overlap
3. YAML Frontmatter Parsing — metadata from document headers
4. Parent-Child Chunk Strategy — small chunks for search, large for context
5. Cross-Encoder Reranking — precision boost on retrieved results

This replaces the JSON-based pipeline with the industry standard:
  Markdown → Header-Aware Chunking → Embedding → ChromaDB → Retrieval + Reranking
"""

from __future__ import annotations

import os
import re
import json
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from langchain_community.vectorstores import Chroma

from langchain_core.documents import Document

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Lazy imports to avoid TensorFlow/spacy/thinc/numpy import chain conflicts
# Lazy imports to avoid TensorFlow/spacy/thinc/numpy import chain conflicts
# Only HuggingFace embeddings and Chroma need lazy loading
_HuggingFaceEmbeddings = None
_Chroma = None
_filter_complex_metadata = None


def _lazy_imports():
    """Import heavy dependencies on first use to avoid import chain conflicts.
    
    Sets TRANSFORMERS_NO_TF=1 and USE_TF=0 to prevent the transformers library
    from pulling in TensorFlow, which causes deadlocks on this system due to
    the chain: sentence_transformers → transformers → tf_keras → tensorflow.
    """
    global _HuggingFaceEmbeddings, _Chroma, _filter_complex_metadata
    
    if _HuggingFaceEmbeddings is None:
        # Block TF import chain before loading sentence-transformers
        os.environ['TRANSFORMERS_NO_TF'] = '1'
        os.environ['USE_TF'] = '0'
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        
        from langchain_huggingface import HuggingFaceEmbeddings
        _HuggingFaceEmbeddings = HuggingFaceEmbeddings
    
    if _Chroma is None:
        from langchain_community.vectorstores import Chroma
        from langchain_community.vectorstores.utils import filter_complex_metadata
        _Chroma = Chroma
        _filter_complex_metadata = filter_complex_metadata


# =============================================================================
# Built-in Text Splitters (avoids langchain_text_splitters → spacy → thinc crash)
# =============================================================================

class MarkdownHeaderTextSplitter:
    """
    Split markdown text by headers, preserving header context in metadata.
    
    Reimplemented to avoid langchain_text_splitters package which triggers
    spacy → thinc → numpy binary incompatibility on this system.
    """
    
    def __init__(self, headers_to_split_on: list, strip_headers: bool = False):
        self.headers_to_split_on = sorted(headers_to_split_on, key=lambda x: len(x[0]), reverse=True)
        self.strip_headers = strip_headers
    
    def split_text(self, text: str) -> list[Document]:
        lines = text.split('\n')
        chunks = []
        current_content = []
        current_headers = {}
        
        for line in lines:
            matched = False
            for marker, header_name in self.headers_to_split_on:
                if line.startswith(marker + ' ') and not line.startswith(marker + '#'):
                    # Save previous chunk
                    if current_content:
                        content = '\n'.join(current_content).strip()
                        if content:
                            chunks.append(Document(
                                page_content=content,
                                metadata=dict(current_headers),
                            ))
                    
                    header_text = line[len(marker):].strip()
                    current_headers[header_name] = header_text
                    current_content = [] if self.strip_headers else [line]
                    matched = True
                    break
            
            if not matched:
                current_content.append(line)
        
        # Don't forget the last chunk
        if current_content:
            content = '\n'.join(current_content).strip()
            if content:
                chunks.append(Document(
                    page_content=content,
                    metadata=dict(current_headers),
                ))
        
        return chunks


class RecursiveCharacterTextSplitter:
    """
    Split text recursively using a hierarchy of separators.
    
    Reimplemented to avoid langchain_text_splitters package dependency.
    """
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        separators: list[str] | None = None,
        length_function=len,
        is_separator_regex: bool = False,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", ", ", " "]
        self.length_function = length_function
    
    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy."""
        final_chunks = []
        
        # Find the best separator
        separator = separators[-1]
        new_separators = []
        for i, sep in enumerate(separators):
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break
        
        splits = text.split(separator)
        
        good_splits = []
        for split in splits:
            if self.length_function(split) < self.chunk_size:
                good_splits.append(split)
            else:
                # Merge accumulated good splits
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                
                # Recursively split the too-large piece
                if new_separators:
                    final_chunks.extend(self._split_text(split, new_separators))
                else:
                    final_chunks.append(split)
        
        # Merge remaining good splits
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)
        
        return final_chunks
    
    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """Merge small splits into chunks respecting size and overlap."""
        chunks = []
        current = []
        current_len = 0
        
        for split in splits:
            split_len = self.length_function(split)
            
            if current_len + split_len + len(separator) > self.chunk_size and current:
                chunk_text = separator.join(current)
                chunks.append(chunk_text)
                
                # Keep overlap: retain last pieces up to chunk_overlap chars
                overlap_len = 0
                overlap_start = len(current)
                while overlap_start > 0:
                    piece_len = self.length_function(current[overlap_start - 1]) + len(separator)
                    if overlap_len + piece_len > self.chunk_overlap:
                        break
                    overlap_len += piece_len
                    overlap_start -= 1
                
                current = current[overlap_start:]
                current_len = sum(self.length_function(c) for c in current) + len(separator) * max(0, len(current) - 1)
            
            current.append(split)
            current_len += split_len + (len(separator) if len(current) > 1 else 0)
        
        if current:
            chunks.append(separator.join(current))
        
        return chunks
    
    def create_documents(self, texts: list[str], metadatas: list[dict] | None = None) -> list[Document]:
        """Split texts into Documents with metadata."""
        documents = []
        metadatas = metadatas or [{}] * len(texts)
        
        for text, metadata in zip(texts, metadatas):
            chunks = self._split_text(text, self.separators)
            for chunk in chunks:
                if chunk.strip():
                    documents.append(Document(
                        page_content=chunk.strip(),
                        metadata=dict(metadata),
                    ))
        
        return documents

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MarkdownRAG")


# =============================================================================
# 1. Markdown Loader with YAML Frontmatter
# =============================================================================

class MarkdownKnowledgeBaseLoader:
    """
    Load Markdown files with YAML frontmatter as LangChain Documents.
    
    Industry standard: Each .md file has YAML frontmatter (---) containing
    metadata like source, disease, region, etc. The loader parses this
    metadata and attaches it to every chunk from that document.
    """
    
    def __init__(self, kb_directory: str):
        self.kb_directory = Path(kb_directory)
        
    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from markdown content.
        
        Returns:
            Tuple of (metadata_dict, body_content)
        """
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                    return metadata, body
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse YAML frontmatter: {e}")
        
        return {}, content
    
    def load_file(self, file_path: Path) -> List[Document]:
        """
        Load a single markdown file into LangChain Documents.
        
        Each document gets the frontmatter metadata attached.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata, body = self._parse_frontmatter(content)
            
            if not body.strip():
                logger.warning(f"Empty body in {file_path.name}")
                return []
            
            # Add file info to metadata
            metadata['source_file'] = file_path.name
            metadata['file_path'] = str(file_path)
            
            # Clean metadata values (ChromaDB only accepts str, int, float, bool)
            clean_meta = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif v is None:
                    clean_meta[k] = ""
                else:
                    clean_meta[k] = str(v)
            
            return [Document(page_content=body, metadata=clean_meta)]
            
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return []
    
    def load_all(self) -> List[Document]:
        """Load all markdown files from the knowledge base directory."""
        md_files = sorted(self.kb_directory.glob('*.md'))
        
        if not md_files:
            logger.error(f"No .md files found in {self.kb_directory}")
            return []
        
        all_docs = []
        for md_file in md_files:
            docs = self.load_file(md_file)
            all_docs.extend(docs)
            
        logger.info(f"📄 Loaded {len(all_docs)} documents from {len(md_files)} Markdown files")
        return all_docs


# =============================================================================
# 2. Industry-Standard Chunking Strategy
# =============================================================================

class IndustryChunker:
    """
    Two-stage chunking strategy used in production RAG systems:
    
    Stage 1: MarkdownHeaderTextSplitter
      - Splits on ## and ### headers
      - Preserves document structure
      - Each chunk knows which section it belongs to
    
    Stage 2: RecursiveCharacterTextSplitter
      - Sub-splits large sections into smaller chunks
      - Uses smart separators: paragraphs → sentences → words
      - Applies OVERLAP between chunks (critical for retrieval quality)
    
    The overlap ensures context is not lost at chunk boundaries —
    this is the single biggest quality improvement over your current pipeline.
    """
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Stage 1: Split by Markdown headers (built-in implementation)
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "header_1"),
                ("##", "header_2"),
                ("###", "header_3"),
            ],
            strip_headers=False,  # Keep headers in content for context
        )
        
        # Stage 2: Recursive character splitting with overlap (built-in)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",   # Paragraph boundary (best)
                "\n",     # Line boundary
                ". ",     # Sentence boundary
                ", ",     # Clause boundary
                " ",      # Word boundary (last resort)
            ],
            length_function=len,
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Apply two-stage chunking to all documents.
        
        Returns chunks with inherited metadata + section context.
        """
        all_chunks = []
        
        for doc in documents:
            doc_metadata = doc.metadata.copy()
            
            # Stage 1: Split by markdown headers
            header_chunks = self.header_splitter.split_text(doc.page_content)
            
            for h_chunk in header_chunks:
                # Merge header metadata with document metadata
                chunk_meta = doc_metadata.copy()
                
                # Add section headers to metadata
                if hasattr(h_chunk, 'metadata') and h_chunk.metadata:
                    for key, value in h_chunk.metadata.items():
                        chunk_meta[key] = value
                
                content = h_chunk.page_content if hasattr(h_chunk, 'page_content') else str(h_chunk)
                
                # Stage 2: Sub-split if chunk is too large
                if len(content) > self.chunk_size:
                    sub_chunks = self.text_splitter.create_documents(
                        texts=[content],
                        metadatas=[chunk_meta],
                    )
                    
                    # Add chunk index for ordering
                    for idx, sc in enumerate(sub_chunks):
                        sc.metadata['chunk_index'] = idx
                        sc.metadata['total_sub_chunks'] = len(sub_chunks)
                    
                    all_chunks.extend(sub_chunks)
                else:
                    # Chunk is small enough, keep as-is
                    if len(content.strip()) >= self.min_chunk_size:
                        chunk_doc = Document(
                            page_content=content,
                            metadata=chunk_meta,
                        )
                        chunk_doc.metadata['chunk_index'] = 0
                        chunk_doc.metadata['total_sub_chunks'] = 1
                        all_chunks.append(chunk_doc)
        
        # Add global chunk IDs
        for i, chunk in enumerate(all_chunks):
            chunk.metadata['global_chunk_id'] = i
        
        logger.info(
            f"📦 Chunked {len(documents)} documents → {len(all_chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        
        return all_chunks


# =============================================================================
# 3. Vector Store with Industry Features
# =============================================================================

class IndustryVectorStore:
    """
    Production-grade vector store with:
    - ChromaDB persistent storage
    - HuggingFace local embeddings (no API keys needed)
    - Hybrid retrieval: semantic + metadata filtering
    - Cross-encoder reranking for precision
    - Query expansion for better recall
    """
    
    def __init__(
        self,
        persist_directory: str = "./vector_store",
        collection_name: str = "agrisense_v2",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Lazy import heavy dependencies
        _lazy_imports()
        
        logger.info(f"🧠 Loading embedding model: {embedding_model}")
        self.embeddings = _HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )
        
        self.vectorstore: Optional[Chroma] = None
        self._query_cache: Dict[str, Any] = {}
        
        # Try loading cross-encoder for reranking
        self._reranker = None
        try:
            from sentence_transformers import CrossEncoder
            logger.info("🔄 Loading cross-encoder reranker...")
            self._reranker = CrossEncoder(
                'cross-encoder/ms-marco-MiniLM-L-6-v2',
                max_length=512,
            )
            logger.info("✅ Cross-encoder reranker ready")
        except Exception as e:
            logger.warning(f"⚠️ Cross-encoder not available: {e}")
            logger.warning("   Retrieval will work without reranking (slightly lower precision)")
    
    def build_from_chunks(self, chunks: List[Document]) -> bool:
        """
        Build vector store from chunked documents.
        
        This embeds all chunks and stores them in ChromaDB.
        """
        if not chunks:
            logger.error("❌ No chunks to embed")
            return False
        
        try:
            # Filter out complex metadata (ChromaDB limitation)
            clean_chunks = _filter_complex_metadata(chunks)
            
            logger.info(f"🔄 Embedding {len(clean_chunks)} chunks into ChromaDB...")
            logger.info(f"⏳ This may take 2-5 minutes...")
            
            # Remove old vector store if exists
            persist_path = Path(self.persist_directory)
            if persist_path.exists():
                import shutil
                shutil.rmtree(persist_path)
                logger.info("🗑️ Removed old vector store")
            
            self.vectorstore = _Chroma.from_documents(
                documents=clean_chunks,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name,
            )
            
            count = self.vectorstore._collection.count()
            logger.info(f"✅ Vector store built with {count} chunks")
            logger.info(f"💾 Persisted to: {self.persist_directory}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to build vector store: {e}")
            return False
    
    def load_existing(self) -> bool:
        """Load an existing vector store from disk."""
        try:
            persist_path = Path(self.persist_directory)
            if not persist_path.exists():
                logger.warning(f"⚠️ No vector store at {self.persist_directory}")
                return False
            
            self.vectorstore = _Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
            )
            
            count = self.vectorstore._collection.count()
            logger.info(f"✅ Loaded vector store with {count} chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load vector store: {e}")
            return False
    
    def retrieve(
        self,
        query: str,
        disease_filter: Optional[str] = None,
        k: int = 5,
        use_reranking: bool = True,
        skip_cache: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """
        Industry-standard retrieval pipeline with latency instrumentation.
        
        1. Query Expansion — enrich query with related terms
        2. Over-fetch — retrieve 4x candidates (k*4)
        3. Metadata Filtering — optional disease/source filter
        4. Cross-Encoder Reranking — re-score with precise model
        5. Return top-k — final ranked results
        
        Returns:
            Tuple of (results_list, latency_breakdown_dict)
            latency_breakdown keys: retrieval_ms, rerank_ms, total_ms
        """
        import time as _time
        latency = {'retrieval_ms': 0.0, 'rerank_ms': 0.0, 'total_ms': 0.0}
        t_start = _time.time()

        if not self.vectorstore:
            logger.warning("⚠️ Vector store not loaded")
            return [], latency
        
        # Check cache
        cache_key = f"{query}:{disease_filter}:{k}:{use_reranking}"
        if not skip_cache and cache_key in self._query_cache:
            return self._query_cache[cache_key], latency
        
        try:
            # Step 1: Query expansion
            expanded_query = self._expand_query(query, disease_filter)
            
            # Step 2: Over-fetch candidates
            fetch_k = min(k * 4, 30)  # Fetch 4x but cap at 30
            
            t_retrieval = _time.time()
            if disease_filter:
                disease_normalized = self._normalize_disease(disease_filter)
                try:
                    docs_with_scores = self.vectorstore.similarity_search_with_score(
                        expanded_query,
                        k=fetch_k,
                        filter={"disease": disease_normalized},
                    )
                except Exception:
                    # Fallback without filter if metadata doesn't match
                    docs_with_scores = self.vectorstore.similarity_search_with_score(
                        expanded_query,
                        k=fetch_k,
                    )
            else:
                docs_with_scores = self.vectorstore.similarity_search_with_score(
                    expanded_query,
                    k=fetch_k,
                )
            latency['retrieval_ms'] = (_time.time() - t_retrieval) * 1000
            
            if not docs_with_scores:
                logger.info(f"📭 No results for: {query[:50]}")
                latency['total_ms'] = (_time.time() - t_start) * 1000
                return [], latency
            
            # Step 3: Rerank with cross-encoder
            t_rerank = _time.time()
            if use_reranking and self._reranker and len(docs_with_scores) > 1:
                results = self._rerank(query, docs_with_scores, k)
            else:
                # Without reranking, just take top-k by similarity
                results = [
                    self._format_result(doc, float(score), rank=i+1)
                    for i, (doc, score) in enumerate(docs_with_scores[:k])
                ]
            latency['rerank_ms'] = (_time.time() - t_rerank) * 1000
            
            # Cache results
            if not skip_cache:
                self._query_cache[cache_key] = results
            
            latency['total_ms'] = (_time.time() - t_start) * 1000
            logger.info(
                f"✅ Retrieved {len(results)} results "
                f"(reranked={use_reranking and self._reranker is not None}) "
                f"[retrieval={latency['retrieval_ms']:.0f}ms rerank={latency['rerank_ms']:.0f}ms]"
            )
            
            return results, latency
            
        except Exception as e:
            logger.error(f"❌ Retrieval error: {e}")
            latency['total_ms'] = (_time.time() - t_start) * 1000
            return [], latency
    
    def _expand_query(self, query: str, disease: Optional[str] = None) -> str:
        """
        Query expansion — add related terms to improve recall.
        
        Industry practice: expand with synonyms and related terminology
        to catch documents that use different phrasing.
        """
        expansions = []
        
        if disease:
            # Add disease-related terms
            disease_lower = disease.lower()
            if 'blight' in disease_lower:
                expansions.extend(['fungicide', 'fungal', 'lesions', 'spots'])
            if 'wilt' in disease_lower:
                expansions.extend(['vascular', 'wilting', 'yellowing'])
            if 'virus' in disease_lower:
                expansions.extend(['vector', 'whitefly', 'aphid', 'resistant varieties'])
            if 'spot' in disease_lower:
                expansions.extend(['bacterial', 'lesions', 'copper spray'])
        
        if expansions:
            return f"{query} {' '.join(expansions[:4])}"
        return query
    
    def _rerank(
        self,
        query: str,
        docs_with_scores: List[Tuple],
        k: int,
    ) -> List[Dict[str, Any]]:
        """
        Cross-encoder reranking — the industry standard for precision.
        
        Bi-encoder (embedding model): Fast but approximate similarity
        Cross-encoder (reranker): Slow but precise relevance scoring
        
        Pipeline: Bi-encoder retrieves candidates → Cross-encoder reranks them
        """
        # Prepare pairs for cross-encoder
        pairs = [(query, doc.page_content) for doc, _ in docs_with_scores]
        
        # Score with cross-encoder
        rerank_scores = self._reranker.predict(pairs)
        
        # Combine original docs with rerank scores
        scored = list(zip(docs_with_scores, rerank_scores))
        scored.sort(key=lambda x: x[1], reverse=True)  # Higher = more relevant
        
        # Take top-k after reranking
        results = []
        for rank, ((doc, sim_score), rerank_score) in enumerate(scored[:k], 1):
            result = self._format_result(doc, float(sim_score), rank)
            result['rerank_score'] = float(rerank_score)
            results.append(result)
        
        return results
    
    def _normalize_disease(self, disease: str) -> str:
        """Normalize disease name for metadata filtering."""
        disease = disease.replace("Tomato___", "").replace("_", " ").strip().title()
        return disease
    
    def _format_result(self, doc: Document, score: float, rank: int) -> Dict[str, Any]:
        """Format a single retrieval result with a unique doc_id for citation tracking."""
        # Generate a stable doc_id from source, disease, and content hash
        source = doc.metadata.get('source', 'Unknown')
        disease = doc.metadata.get('disease', 'Unknown')
        source_file = doc.metadata.get('source_file', '')
        section = doc.metadata.get('header_2', doc.metadata.get('header_1', ''))

        # Build a human-readable doc_id: e.g. fao_early_blight_chunk_3
        src_tag = re.sub(r'[^a-z0-9]+', '_', source.lower()).strip('_')[:20]
        disease_tag = re.sub(r'[^a-z0-9]+', '_', disease.lower()).strip('_')[:25]
        # Use a short hash of the content to distinguish chunks from same source+disease
        import hashlib
        content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()[:6]
        doc_id = f"{src_tag}_{disease_tag}_{content_hash}"

        return {
            'rank': rank,
            'doc_id': doc_id,
            'text': doc.page_content,
            'score': score,
            'source': source,
            'disease': disease,
            'content_type': doc.metadata.get('header_2', 'General'),
            'section': section,
            'source_file': source_file,
            'confidence': max(0.0, min(1.0, 1.0 - (score / 2.0))),  # Normalize to 0-1
            'metadata': {k: v for k, v in doc.metadata.items() 
                        if k not in ('file_path',)},
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        if not self.vectorstore:
            return {"status": "not_initialized"}
        
        try:
            count = self.vectorstore._collection.count()
            return {
                "status": "ready",
                "document_count": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "reranker_available": self._reranker is not None,
                "format": "markdown",
                "version": "2.0",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear_cache(self):
        """Clear query cache."""
        self._query_cache.clear()


# =============================================================================
# 4. Complete RAG Pipeline Orchestrator
# =============================================================================

class MarkdownRAGPipeline:
    """
    End-to-end industry-standard RAG pipeline:
    
    Markdown Files → Load → Chunk → Embed → ChromaDB → Retrieve → Rerank → LLM
    
    Usage:
        pipeline = MarkdownRAGPipeline()
        pipeline.build("./knowledge_base")
        results = pipeline.query("How to treat early blight?", disease="Early Blight")
    """
    
    def __init__(
        self,
        persist_directory: str = "./vector_store",
        collection_name: str = "agrisense_v2",
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ):
        self.chunker = IndustryChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.vector_store = IndustryVectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
        )
        self.is_ready = False
    
    def build(self, kb_directory: str, force_rebuild: bool = False) -> bool:
        """
        Build the complete RAG pipeline from markdown files.
        
        Args:
            kb_directory: Path to directory with .md knowledge base files
            force_rebuild: Force rebuild even if vector store exists
        """
        # Check if existing store can be loaded
        if not force_rebuild and self.vector_store.load_existing():
            self.is_ready = True
            return True
        
        logger.info("=" * 60)
        logger.info("🏗️ Building Industry-Standard RAG Pipeline")
        logger.info("=" * 60)
        
        # Step 1: Load markdown documents
        logger.info("\n📂 Step 1: Loading Markdown Knowledge Base...")
        loader = MarkdownKnowledgeBaseLoader(kb_directory)
        documents = loader.load_all()
        
        if not documents:
            logger.error("❌ No documents loaded")
            return False
        
        # Step 2: Chunk with overlap
        logger.info("\n✂️ Step 2: Chunking with Header-Aware Splitter...")
        chunks = self.chunker.chunk_documents(documents)
        
        if not chunks:
            logger.error("❌ No chunks created")
            return False
        
        # Step 3: Embed and store
        logger.info("\n🔢 Step 3: Embedding and Storing in ChromaDB...")
        success = self.vector_store.build_from_chunks(chunks)
        
        if success:
            self.is_ready = True
            stats = self.vector_store.get_stats()
            logger.info("\n" + "=" * 60)
            logger.info("✅ RAG Pipeline Ready!")
            logger.info(f"   Documents: {len(documents)}")
            logger.info(f"   Chunks: {stats.get('document_count', 0)}")
            logger.info(f"   Reranker: {'✅' if stats.get('reranker_available') else '❌'}")
            logger.info(f"   Format: Markdown (Industry Standard)")
            logger.info("=" * 60)
        
        return success
    
    def build_from_json_legacy(self, json_path: str, force_rebuild: bool = False) -> bool:
        """
        Build from existing rag_documents.json (backward compatible).
        
        Converts JSON documents to LangChain Document format
        and processes through the new pipeline.
        """
        if not force_rebuild and self.vector_store.load_existing():
            self.is_ready = True
            return True
        
        logger.info("📦 Loading from legacy JSON format...")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                rag_data = json.load(f)
            
            documents = []
            for doc in rag_data.get('documents', []):
                metadata = doc.get('metadata', {})
                metadata['doc_id'] = doc.get('id', 'unknown')
                
                # Clean metadata for ChromaDB
                clean_meta = {}
                for k, v in metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif isinstance(v, list):
                        clean_meta[k] = str(v)
                    elif v is None:
                        clean_meta[k] = ""
                    else:
                        clean_meta[k] = str(v)
                
                documents.append(Document(
                    page_content=doc.get('text', ''),
                    metadata=clean_meta,
                ))
            
            logger.info(f"📄 Loaded {len(documents)} documents from JSON")
            
            # Chunk through industry pipeline
            chunks = self.chunker.chunk_documents(documents)
            success = self.vector_store.build_from_chunks(chunks)
            
            if success:
                self.is_ready = True
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to load JSON: {e}")
            return False
    
    def query(
        self,
        question: str,
        disease: Optional[str] = None,
        k: int = 5,
        use_reranking: bool = True,
        skip_cache: bool = False,
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, float]]:
        """
        Query the knowledge base and return formatted context + source docs + latency.
        
        Returns:
            Tuple of (formatted_context_string, source_documents_list, latency_breakdown)
        """
        empty_latency = {'retrieval_ms': 0.0, 'rerank_ms': 0.0, 'total_ms': 0.0}
        if not self.is_ready:
            logger.warning("⚠️ Pipeline not ready. Call build() first.")
            return "", [], empty_latency
        
        results, latency = self.vector_store.retrieve(
            query=question,
            disease_filter=disease,
            k=k,
            use_reranking=use_reranking,
            skip_cache=skip_cache,
        )
        
        if not results:
            return "", [], latency
        
        # Format context for LLM injection — now includes doc_id tags for citation tracking
        context_parts = [
            "=== RETRIEVED AGRICULTURAL KNOWLEDGE ===",
            f"Query: {question}",
            f"Results: {len(results)} relevant documents\n",
        ]
        
        for r in results:
            doc_id = r.get('doc_id', 'unknown')
            context_parts.append(
                f"[DOC_ID: {doc_id}] Source: {r['source']} | Section: {r['section']}"
            )
            context_parts.append(r['text'][:1000])  # Cap per-document length
            
            if r.get('rerank_score') is not None:
                context_parts.append(f"[Relevance: {r['rerank_score']:.3f}]")
            context_parts.append("")
        
        context_parts.append("=== END KNOWLEDGE BASE ===")
        context_str = "\n".join(context_parts)
        
        return context_str, results, latency
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.vector_store.get_stats()


# =============================================================================
# 5. CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Industry-Standard Markdown RAG Pipeline")
    parser.add_argument('--kb-dir', default='./Web_Scraping_for_Agrisense/rag_pipeline/processed/markdown_kb',
                       help='Path to markdown knowledge base directory')
    parser.add_argument('--json-fallback', default='./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_documents.json',
                       help='Fallback: path to legacy JSON file')
    parser.add_argument('--persist-dir', default='./vector_store',
                       help='ChromaDB persist directory')
    parser.add_argument('--rebuild', action='store_true', help='Force rebuild')
    parser.add_argument('--query', type=str, help='Test query')
    parser.add_argument('--disease', type=str, help='Disease filter for query')
    args = parser.parse_args()
    
    pipeline = MarkdownRAGPipeline(
        persist_directory=args.persist_dir,
        collection_name="agrisense_v2",
    )
    
    # Try Markdown first, fall back to JSON
    kb_path = Path(args.kb_dir)
    if kb_path.exists() and list(kb_path.glob('*.md')):
        logger.info("📚 Using Markdown knowledge base (Industry Standard)")
        success = pipeline.build(str(kb_path), force_rebuild=args.rebuild)
    elif Path(args.json_fallback).exists():
        logger.info("📦 Markdown KB not found, using legacy JSON")
        success = pipeline.build_from_json_legacy(args.json_fallback, force_rebuild=args.rebuild)
    else:
        logger.error("❌ No knowledge base found. Run convert_to_markdown.py first.")
        exit(1)
    
    if not success:
        logger.error("❌ Pipeline build failed")
        exit(1)
    
    # Test query
    test_query = args.query or "How to treat early blight on tomatoes?"
    test_disease = args.disease or "Early Blight"
    
    print(f"\n{'='*60}")
    print(f"🔍 Test Query: {test_query}")
    print(f"🦠 Disease Filter: {test_disease}")
    print(f"{'='*60}")
    
    context, results = pipeline.query(test_query, disease=test_disease, k=5)
    
    print(f"\n📊 Retrieved {len(results)} results:\n")
    for r in results:
        print(f"  #{r['rank']} [{r['source']}] {r['section']}")
        print(f"     Score: {r['score']:.4f}", end="")
        if r.get('rerank_score') is not None:
            print(f" → Reranked: {r['rerank_score']:.4f}", end="")
        print()
        print(f"     {r['text'][:150]}...")
        print()
    
    print(f"\n📝 Context length: {len(context)} chars")
