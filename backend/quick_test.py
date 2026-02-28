"""Quick test for rag_agent integration."""
import os
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['USE_TF'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from rag_agent import get_rag_pipeline, retrieve_context

print("Getting pipeline...")
p = get_rag_pipeline()
print(f"Pipeline ready: {p.is_ready}")

print("\nRetrieving context for Early Blight...")
ctx, docs = retrieve_context("Early Blight", k=5)
print(f"Context length: {len(ctx)}")
print(f"Documents retrieved: {len(docs)}")
print("\n--- CONTEXT PREVIEW ---")
print(ctx[:800] if ctx else "(empty)")
print("--- END ---")
