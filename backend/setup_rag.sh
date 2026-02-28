#!/bin/bash

# AgriSense RAG Setup Script
# Installs dependencies and initializes the vector store

set -e  # Exit on error

echo "======================================================================"
echo "🌱 AgriSense RAG System Setup"
echo "======================================================================"

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo ""
echo "📦 Step 1: Installing Python dependencies..."
echo "----------------------------------------------------------------------"
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed successfully"

echo ""
echo "🔍 Step 2: Checking for RAG documents..."
echo "----------------------------------------------------------------------"

RAG_JSON="./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_combined.json"

if [ ! -f "$RAG_JSON" ]; then
    echo "❌ RAG documents not found at: $RAG_JSON"
    echo ""
    echo "Please ensure the RAG pipeline has been executed to generate documents."
    echo "Run the following from Web_Scraping_for_Agrisense/rag_pipeline/:"
    echo "  python run_pipeline.py"
    exit 1
fi

echo "✅ RAG documents found ($(wc -l < "$RAG_JSON") lines)"

echo ""
echo "🧠 Step 3: Initializing vector store..."
echo "----------------------------------------------------------------------"
echo "⏳ This will take 2-3 minutes to embed 463 documents..."
echo ""

$PYTHON_CMD init_vector_store.py

echo ""
echo "======================================================================"
echo "✅ AgriSense RAG Setup Complete!"
echo "======================================================================"
echo ""
echo "🚀 Next Steps:"
echo "   1. Set your GROQ_API_KEY in .env file:"
echo "      echo 'GROQ_API_KEY=your_key_here' > .env"
echo ""
echo "   2. Start the backend:"
echo "      python main.py"
echo "      # or"
echo "      uvicorn main:app --reload"
echo ""
echo "   3. Test the API at http://localhost:8000/docs"
echo ""
echo "📚 Documentation: See RAG_SETUP.md for details"
echo "======================================================================"
