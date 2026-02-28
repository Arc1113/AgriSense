"""
Initialize AgriSense Vector Store (Industry-Standard Markdown Pipeline)
Setup script to build the RAG knowledge base from Markdown documents.

Workflow:
    1. Convert cleaned text → Markdown with YAML frontmatter (if needed)
    2. Load Markdown documents with metadata
    3. Chunk with header-aware splitting + overlap
    4. Embed with HuggingFace (sentence-transformers)
    5. Store in ChromaDB with cross-encoder reranking support

Run this script after installation to prepare the knowledge base:
    python init_vector_store.py

Options:
    --rebuild       Force rebuild even if vector store exists
    --test          Run test queries after initialization
    --convert-only  Only convert text to Markdown (skip embedding)
"""

import sys
import argparse
import logging
import os
from pathlib import Path

from markdown_rag_pipeline import MarkdownRAGPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VectorStoreInit")


def convert_text_to_markdown():
    """Convert cleaned text files to Markdown knowledge base format."""
    try:
        input_dir = Path(__file__).parent / "Web_Scraping_for_Agrisense" / "rag_pipeline" / "processed" / "cleaned_text"
        output_dir = Path(__file__).parent / "Web_Scraping_for_Agrisense" / "rag_pipeline" / "processed" / "markdown_kb"
        
        # Skip if markdown files already exist
        if output_dir.exists() and list(output_dir.rglob('*.md')):
            md_count = len(list(output_dir.rglob('*.md')))
            logger.info(f"✅ Markdown KB already exists ({md_count} files)")
            return True
            
        if not input_dir.exists():
            logger.error(f"❌ Cleaned text directory not found: {input_dir}")
            return False
        
        logger.info("📝 Converting cleaned text → Markdown knowledge base...")
        sys.path.insert(0, str(Path(__file__).parent / "Web_Scraping_for_Agrisense" / "rag_pipeline"))
        from convert_to_markdown import convert_all
        convert_all(str(input_dir), str(output_dir))
        return True
        
    except Exception as e:
        logger.error(f"❌ Markdown conversion failed: {e}")
        return False


def main():
    """Initialize the vector store using the industry-standard Markdown pipeline."""
    parser = argparse.ArgumentParser(
        description="Initialize AgriSense RAG Pipeline (Industry Standard)"
    )
    parser.add_argument(
        '--rebuild', 
        action='store_true',
        help='Force rebuild even if vector store exists'
    )
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Run test queries after initialization'
    )
    parser.add_argument(
        '--convert-only',
        action='store_true',
        help='Only convert text to Markdown, skip embedding'
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("🌱 AgriSense RAG Pipeline — Industry Standard (Markdown + Reranking)")
    print("=" * 70)
    
    # Step 1: Ensure Markdown knowledge base exists
    logger.info("\n📂 Step 1: Preparing Markdown Knowledge Base...")
    if not convert_text_to_markdown():
        logger.error("❌ Cannot prepare knowledge base")
        return 1
    
    if args.convert_only:
        logger.info("\n✅ Conversion complete (--convert-only mode)")
        return 0
    
    # Step 2: Build the industry-standard RAG pipeline
    logger.info("\n🏗️ Step 2: Building RAG Pipeline...")
    
    md_kb_path = Path(__file__).parent / "Web_Scraping_for_Agrisense" / "rag_pipeline" / "processed" / "markdown_kb"
    json_fallback = Path(__file__).parent / "Web_Scraping_for_Agrisense" / "rag_pipeline" / "processed" / "rag_json" / "rag_documents.json"
    
    persist_dir = os.environ.get("RAG_VECTOR_STORE_PATH", "./vector-store")
    pipeline = MarkdownRAGPipeline(
        persist_directory=persist_dir,
        collection_name="agrisense_v2",
        chunk_size=800,
        chunk_overlap=150,
    )
    
    # Build from Markdown (preferred) or JSON (fallback)
    if md_kb_path.exists() and list(md_kb_path.glob('*.md')):
        logger.info(f"📚 Building from Markdown KB: {md_kb_path}")
        success = pipeline.build(str(md_kb_path), force_rebuild=args.rebuild)
    elif json_fallback.exists():
        logger.info(f"📦 Markdown not found, using legacy JSON: {json_fallback}")
        success = pipeline.build_from_json_legacy(str(json_fallback), force_rebuild=args.rebuild)
    else:
        logger.error("❌ No knowledge base found. Run the scraping pipeline first.")
        return 1
    
    if not success:
        logger.error("\n❌ Pipeline initialization FAILED")
        return 1
    
    # Step 3: Show stats
    stats = pipeline.get_stats()
    logger.info("\n📊 Pipeline Statistics:")
    logger.info(f"   Status: {stats.get('status', 'unknown')}")
    logger.info(f"   Chunks: {stats.get('document_count', 0)}")
    logger.info(f"   Reranker: {'✅ Active' if stats.get('reranker_available') else '❌ Not available'}")
    logger.info(f"   Format: {stats.get('format', 'unknown')}")
    logger.info(f"   Version: {stats.get('version', 'unknown')}")
    
    # Step 4: Run test queries if requested
    if args.test:
        logger.info("\n" + "=" * 70)
        logger.info("🧪 Running Test Queries")
        logger.info("=" * 70)
        
        test_cases = [
            {
                "query": "How to treat early blight on tomatoes?",
                "disease": "Early Blight",
            },
            {
                "query": "Prevention methods for late blight",
                "disease": "Late Blight",
            },
            {
                "query": "Organic treatments for bacterial spot",
                "disease": "Bacterial Spot",
            },
        ]
        
        for i, test in enumerate(test_cases, 1):
            logger.info(f"\n🔍 Test {i}: {test['query']}")
            logger.info(f"   Disease Filter: {test['disease']}")
            
            context, results = pipeline.query(
                question=test['query'],
                disease=test['disease'],
                k=3,
            )
            
            logger.info(f"   ✅ Retrieved {len(results)} documents")
            for doc in results:
                score_info = f"Score: {doc['score']:.4f}"
                if doc.get('rerank_score') is not None:
                    score_info += f" → Reranked: {doc['rerank_score']:.4f}"
                logger.info(f"\n      📄 #{doc['rank']} [{doc['source']}] {doc['section']}")
                logger.info(f"         {score_info}")
                logger.info(f"         {doc['text'][:120]}...")
    
    print("\n" + "=" * 70)
    print("✅ Industry-Standard RAG Pipeline Ready!")
    print("=" * 70)
    print("\n📋 Pipeline Features:")
    print("   ✅ Markdown knowledge base with YAML frontmatter")
    print("   ✅ Header-aware chunking (respects document structure)")
    print("   ✅ Chunk overlap (150 chars) — prevents context loss")
    print("   ✅ Query expansion for better recall")
    print(f"   {'✅' if stats.get('reranker_available') else '❌'} Cross-encoder reranking for precision")
    print("   ✅ ChromaDB persistent vector store")
    print("\n💡 Next Steps:")
    print("   1. Start the backend: python main.py")
    print("   2. The RAG system will retrieve from the Markdown knowledge base")
    print("   3. Check logs for retrieval + reranking activity\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
