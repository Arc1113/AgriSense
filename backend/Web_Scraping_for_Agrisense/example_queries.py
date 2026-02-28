"""
Simple Example - Query Your RAG Data
Demonstrates basic filtering and querying of the RAG documents.
"""

import json
from pathlib import Path
from collections import Counter

# Load the RAG data
data_path = Path('rag_pipeline/processed/rag_json/rag_documents.json')
with open(data_path, 'r', encoding='utf-8') as f:
    rag_data = json.load(f)

documents = rag_data['documents']
print(f"📚 Loaded {len(documents)} documents")
print("=" * 70)

# Example 1: Filter by disease
print("\n🔍 Example 1: Find Late Blight treatment documents")
print("-" * 70)
late_blight_treatments = [
    doc for doc in documents
    if doc['metadata']['disease'] == 'Late Blight'
    and doc['metadata']['content_type'] == 'Treatment'
]
print(f"Found {len(late_blight_treatments)} Late Blight treatment documents")
if late_blight_treatments:
    sample = late_blight_treatments[0]
    print(f"\nSample:")
    print(f"  ID: {sample['id']}")
    print(f"  Disease: {sample['metadata']['disease']}")
    print(f"  Scientific Name: {sample['metadata'].get('disease_scientific_name', 'N/A')}")
    print(f"  Confidence: {sample['metadata']['disease_confidence']}")
    print(f"  Source: {sample['metadata']['source']}")
    print(f"  Text: {sample['text'][:200]}...")

# Example 2: Get high-confidence disease detections
print("\n\n🎯 Example 2: High-confidence disease detections (>= 0.9)")
print("-" * 70)
high_confidence = [
    doc for doc in documents
    if doc['metadata']['disease_confidence'] >= 0.9
    and doc['metadata']['disease'] != 'General'
]
print(f"Found {len(high_confidence)} high-confidence documents")

# Count diseases
disease_counts = Counter(doc['metadata']['disease'] for doc in high_confidence)
for disease, count in disease_counts.most_common(5):
    print(f"  {disease}: {count}")

# Example 3: Search by keyword
print("\n\n🔎 Example 3: Search for 'fungicide' mentions")
print("-" * 70)
fungicide_docs = [
    doc for doc in documents
    if 'fungicide' in doc['text'].lower()
]
print(f"Found {len(fungicide_docs)} documents mentioning fungicides")

# Group by disease
fungicide_by_disease = {}
for doc in fungicide_docs:
    disease = doc['metadata']['disease']
    if disease not in fungicide_by_disease:
        fungicide_by_disease[disease] = []
    fungicide_by_disease[disease].append(doc)

print("\nFungicide mentions by disease:")
for disease, docs in sorted(fungicide_by_disease.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
    print(f"  {disease}: {len(docs)} documents")

# Example 4: FAO vs Other sources
print("\n\n📊 Example 4: Source comparison")
print("-" * 70)
source_counts = Counter(doc['metadata']['source'] for doc in documents)
for source, count in source_counts.most_common():
    percentage = (count / len(documents)) * 100
    print(f"  {source}: {count} documents ({percentage:.1f}%)")

# Example 5: Philippine-specific content
print("\n\n🇵🇭 Example 5: Philippine-specific documents")
print("-" * 70)
ph_docs = [
    doc for doc in documents
    if doc['metadata']['region'] == 'PH'
]
print(f"Found {len(ph_docs)} Philippines-specific documents")

if ph_docs:
    ph_sources = Counter(doc['metadata']['source'] for doc in ph_docs)
    print("\nPhilippine sources:")
    for source, count in ph_sources.most_common():
        print(f"  {source}: {count}")

# Example 6: Multi-disease documents
print("\n\n🔬 Example 6: Documents with multiple diseases detected")
print("-" * 70)
multi_disease = [
    doc for doc in documents
    if len(doc['metadata'].get('all_diseases_detected', [])) > 1
]
print(f"Found {len(multi_disease)} documents with multiple diseases")

if multi_disease:
    sample = multi_disease[0]
    print(f"\nSample:")
    print(f"  ID: {sample['id']}")
    print(f"  Primary: {sample['metadata']['disease']}")
    print(f"  All detected:")
    for disease in sample['metadata']['all_diseases_detected']:
        print(f"    - {disease['name']} (confidence: {disease['confidence']})")

# Example 7: Token statistics
print("\n\n📏 Example 7: Token statistics")
print("-" * 70)
tokens = [doc['metadata']['token_count'] for doc in documents]
avg_tokens = sum(tokens) / len(tokens)
min_tokens = min(tokens)
max_tokens = max(tokens)
print(f"Average tokens per chunk: {avg_tokens:.1f}")
print(f"Min tokens: {min_tokens}")
print(f"Max tokens: {max_tokens}")

# Example 8: Create a simple query function
def query_documents(query_text, filters=None, top_k=5):
    """
    Simple keyword-based document search.
    In production, use vector similarity search.
    """
    results = []
    query_lower = query_text.lower()
    
    for doc in documents:
        # Apply filters
        if filters:
            skip = False
            for key, value in filters.items():
                if doc['metadata'].get(key) != value:
                    skip = True
                    break
            if skip:
                continue
        
        # Simple keyword matching
        text_lower = doc['text'].lower()
        if query_lower in text_lower:
            # Count occurrences as a simple relevance score
            score = text_lower.count(query_lower)
            results.append((score, doc))
    
    # Sort by score and return top_k
    results.sort(reverse=True, key=lambda x: x[0])
    return [doc for score, doc in results[:top_k]]

print("\n\n🔍 Example 8: Query function test")
print("-" * 70)
query_results = query_documents(
    "copper fungicide",
    filters={'content_type': 'Treatment'},
    top_k=3
)
print(f"Query: 'copper fungicide' (Treatment documents only)")
print(f"Results: {len(query_results)}")
for i, doc in enumerate(query_results, 1):
    print(f"\n{i}. {doc['id']}")
    print(f"   Disease: {doc['metadata']['disease']}")
    print(f"   Source: {doc['metadata']['source']}")
    print(f"   Preview: {doc['text'][:150]}...")

print("\n" + "=" * 70)
print("✅ Examples complete! Your data is ready for RAG applications.")
print("=" * 70)
