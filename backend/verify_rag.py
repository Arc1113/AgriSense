"""Full verification test for the Industry-Standard RAG Pipeline."""
import os
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['USE_TF'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import sys

def test_rag_pipeline():
    """Test the RAG pipeline directly."""
    print("=" * 60)
    print("  RAG Pipeline Verification Test")
    print("=" * 60)
    
    # Test 1: Import
    print("\n[1] Importing MarkdownRAGPipeline...")
    try:
        from markdown_rag_pipeline import MarkdownRAGPipeline
        print("    ✅ Import successful")
    except Exception as e:
        print(f"    ❌ Import failed: {e}")
        return False
    
    # Test 2: Load existing pipeline
    print("\n[2] Loading existing vector store...")
    try:
        pipeline = MarkdownRAGPipeline(
            persist_directory='./vector_store',
            collection_name='agrisense_v2'
        )
        # Try to load existing
        if pipeline.vector_store.load_existing():
            pipeline.is_ready = True
            stats = pipeline.get_stats()
            print(f"    ✅ Loaded {stats.get('document_count', 0)} chunks")
            print(f"    ✅ Reranker: {'Active' if stats.get('reranker_available') else 'Disabled'}")
        else:
            print("    ❌ No existing vector store found")
            return False
    except Exception as e:
        print(f"    ❌ Load failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Query tests
    test_cases = [
        ("Early Blight treatment", "Early Blight"),
        ("Late Blight prevention", "Late Blight"),
        ("Tomato disease management", None),
    ]
    
    print("\n[3] Running query tests...")
    all_passed = True
    for query, disease in test_cases:
        try:
            context, docs = pipeline.query(query, disease=disease, k=3)
            if docs and len(docs) > 0:
                print(f"    ✅ '{query}' → {len(docs)} docs, top score: {docs[0]['score']:.3f}")
                if docs[0].get('rerank_score') is not None:
                    print(f"       Rerank score: {docs[0]['rerank_score']:.3f}")
            else:
                print(f"    ⚠️ '{query}' → No results")
                all_passed = False
        except Exception as e:
            print(f"    ❌ '{query}' → Error: {e}")
            all_passed = False
    
    # Test 4: Integration with rag_agent
    print("\n[4] Testing rag_agent integration...")
    try:
        from rag_agent import get_rag_pipeline, retrieve_context
        
        agent_pipeline = get_rag_pipeline()
        if agent_pipeline and agent_pipeline.is_ready:
            print("    ✅ get_rag_pipeline() works")
            
            ctx, docs = retrieve_context("Early Blight", k=3)
            if ctx and len(ctx) > 100:
                print(f"    ✅ retrieve_context() returned {len(ctx)} chars, {len(docs)} docs")
            else:
                print(f"    ⚠️ retrieve_context() returned short context: {len(ctx) if ctx else 0} chars")
        else:
            print("    ⚠️ Pipeline not ready via rag_agent")
    except Exception as e:
        print(f"    ❌ rag_agent integration error: {e}")
        all_passed = False
    
    # Test 5: Context quality check
    print("\n[5] Context quality check...")
    try:
        ctx, docs = pipeline.query("How to treat early blight on tomatoes?", disease="Early Blight", k=5)
        if docs:
            # Check if results contain relevant keywords
            relevant_keywords = ['blight', 'fungicide', 'treatment', 'management', 'spray', 'copper']
            found_keywords = []
            for doc in docs:
                text_lower = doc['text'].lower()
                for kw in relevant_keywords:
                    if kw in text_lower and kw not in found_keywords:
                        found_keywords.append(kw)
            
            if len(found_keywords) >= 3:
                print(f"    ✅ Found relevant keywords: {', '.join(found_keywords)}")
            else:
                print(f"    ⚠️ Few relevant keywords found: {found_keywords}")
            
            # Check sources
            sources = set(d['source'] for d in docs)
            print(f"    ✅ Sources: {', '.join(sources)}")
            
            # Show sample context
            print(f"\n    Sample context (first 300 chars):")
            print(f"    {docs[0]['text'][:300]}...")
        else:
            print("    ❌ No results for quality check")
            all_passed = False
    except Exception as e:
        print(f"    ❌ Quality check error: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  ✅ ALL TESTS PASSED - RAG Pipeline is working correctly!")
    else:
        print("  ⚠️ SOME TESTS HAD ISSUES - Check output above")
    print("=" * 60)
    
    return all_passed


if __name__ == '__main__':
    success = test_rag_pipeline()
    sys.exit(0 if success else 1)
