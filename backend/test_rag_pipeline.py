"""Test script for the industry-standard Markdown RAG pipeline."""
import os
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def main():
    print("=" * 60)
    print("  AgriSense Industry-Standard RAG Pipeline Test")
    print("=" * 60)
    
    # Step 1: Import
    print("\n[Step 1] Importing MarkdownRAGPipeline...")
    try:
        from markdown_rag_pipeline import MarkdownRAGPipeline
        print("  OK - Pipeline imported successfully")
    except Exception as e:
        print(f"  FAIL - Import error: {e}")
        sys.exit(1)
    
    # Step 2: Create pipeline
    print("\n[Step 2] Creating pipeline instance...")
    pipeline = MarkdownRAGPipeline(
        persist_directory='./vector_store',
        collection_name='agrisense_v2'
    )
    print("  OK - Pipeline created")
    
    # Step 3: Check Markdown KB
    kb_path = './Web_Scraping_for_Agrisense/rag_pipeline/processed/markdown_kb'
    if os.path.exists(kb_path):
        md_files = [f for f in os.listdir(kb_path) if f.endswith('.md')]
        print(f"\n[Step 3] Markdown KB found: {len(md_files)} files")
    else:
        print(f"\n[Step 3] WARNING: Markdown KB not found at {kb_path}")
        print("  Run convert_to_markdown.py first")
        sys.exit(1)
    
    # Step 4: Build pipeline
    print("\n[Step 4] Building RAG pipeline (embedding documents)...")
    print("  This may take a minute on first run (downloading models)...")
    try:
        success = pipeline.build(kb_path, force_rebuild=True)
        if success:
            print("  OK - Pipeline built successfully!")
        else:
            print("  FAIL - Pipeline build returned False")
            sys.exit(1)
    except Exception as e:
        print(f"  FAIL - Build error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 5: Get stats
    print("\n[Step 5] Pipeline Statistics:")
    try:
        stats = pipeline.get_stats()
        print(f"  Total chunks:     {stats.get('document_count', 0)}")
        print(f"  Reranker:         {'Yes' if stats.get('reranker_available') else 'No (fallback mode)'}")
        print(f"  Format:           {stats.get('format', 'unknown')}")
        print(f"  Embedding model:  {stats.get('embedding_model', 'unknown')}")
        print(f"  Chunk size:       {stats.get('chunk_size', 'unknown')}")
        print(f"  Chunk overlap:    {stats.get('chunk_overlap', 'unknown')}")
    except Exception as e:
        print(f"  Warning: Could not get stats: {e}")
    
    # Step 6: Test queries
    test_queries = [
        ("How to treat early blight on tomatoes?", "Early Blight"),
        ("Prevention methods for late blight", "Late Blight"),
        ("What causes tomato leaf curl virus?", "Leaf Curl"),
        ("Organic treatment for septoria leaf spot", "Septoria Leaf Spot"),
        ("General tomato disease management", None),
    ]
    
    print("\n[Step 6] Running test queries...")
    print("-" * 60)
    
    for i, (query, disease) in enumerate(test_queries, 1):
        print(f"\n  Query {i}: \"{query}\"")
        if disease:
            print(f"  Disease filter: {disease}")
        
        try:
            context, docs = pipeline.query(query, disease=disease, k=3)
            print(f"  Results: {len(docs)} documents retrieved")
            
            for d in docs:
                rerank = ""
                if d.get('rerank_score') is not None:
                    rerank = f" | rerank={d['rerank_score']:.3f}"
                source = d.get('source', 'unknown')
                score = d.get('score', 0)
                rank = d.get('rank', '?')
                text_preview = d.get('text', '')[:100].replace('\n', ' ')
                print(f"    #{rank} [{source}] sim={score:.3f}{rerank}")
                print(f"       {text_preview}...")
            
            if not docs:
                print("    (no results)")
                
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Step 7: Verify integration with rag_agent
    print("\n" + "-" * 60)
    print("\n[Step 7] Testing rag_agent integration...")
    try:
        from rag_agent import get_rag_pipeline, retrieve_context
        pipeline_ref = get_rag_pipeline()
        if pipeline_ref and pipeline_ref.vector_store.vectorstore:
            print("  OK - rag_agent.get_rag_pipeline() works")
            
            # Test retrieve_context
            ctx = retrieve_context("early blight treatment", "Early Blight")
            if ctx and len(ctx) > 50:
                print(f"  OK - retrieve_context() returned {len(ctx)} chars")
                print(f"  Preview: {ctx[:150]}...")
            else:
                print(f"  WARNING - retrieve_context() returned short result: {len(ctx) if ctx else 0} chars")
        else:
            print("  WARNING - Pipeline reference or vectorstore is None")
    except Exception as e:
        print(f"  ERROR in rag_agent integration: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
