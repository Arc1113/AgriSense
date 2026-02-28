@echo off
REM AgriSense RAG Setup Script for Windows
REM Installs dependencies and initializes the vector store

echo ======================================================================
echo 🌱 AgriSense RAG System Setup
echo ======================================================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8 or higher.
    exit /b 1
)

echo.
echo 📦 Step 1: Installing Python dependencies...
echo ----------------------------------------------------------------------
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

echo.
echo ✅ Dependencies installed successfully

echo.
echo 🔍 Step 2: Checking for RAG documents...
echo ----------------------------------------------------------------------

set RAG_JSON=Web_Scraping_for_Agrisense\rag_pipeline\processed\rag_json\rag_combined.json

if not exist "%RAG_JSON%" (
    echo ❌ RAG documents not found at: %RAG_JSON%
    echo.
    echo Please ensure the RAG pipeline has been executed to generate documents.
    echo Run the following from Web_Scraping_for_Agrisense\rag_pipeline\:
    echo   python run_pipeline.py
    exit /b 1
)

echo ✅ RAG documents found

echo.
echo 🧠 Step 3: Initializing vector store...
echo ----------------------------------------------------------------------
echo ⏳ This will take 2-3 minutes to embed 463 documents...
echo.

python init_vector_store.py

if errorlevel 1 (
    echo ❌ Vector store initialization failed
    exit /b 1
)

echo.
echo ======================================================================
echo ✅ AgriSense RAG Setup Complete!
echo ======================================================================
echo.
echo 🚀 Next Steps:
echo    1. Set your GROQ_API_KEY in .env file:
echo       Create a file named .env and add:
echo       GROQ_API_KEY=your_key_here
echo.
echo    2. Start the backend:
echo       python main.py
echo.
echo    3. Test the API at http://localhost:8000/docs
echo.
echo 📚 Documentation: See RAG_SETUP.md for details
echo ======================================================================

pause
