"""
AgriSense Multi-Agent RAG System
CrewAI-based treatment advice generation using Groq + Local HuggingFace Embeddings

Features:
- Single unified agent for fast response
- Weather-aware treatment recommendations
- Safety-first approach with PPE guidance
- Robust error handling with fallback responses
- Configurable LLM backend (Groq)
- Timeout protection for API calls

Compatible with CrewAI 1.9.x
"""

import os

# CRITICAL: Set these BEFORE importing transformers/sentence-transformers
# to prevent TensorFlow import chain deadlock on systems with TF installed
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['USE_TF'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Disable CrewAI telemetry (prevents timeout errors connecting to telemetry.crewai.com)
os.environ['CREWAI_TELEMETRY_OPT_OUT'] = 'true'
os.environ['OTEL_SDK_DISABLED'] = 'true'

import json
import re
import logging
import time
import asyncio
import concurrent.futures
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGAgent")

# Load environment variables BEFORE importing crewai
load_dotenv()

# CrewAI imports
from crewai import Agent, Task, Crew, Process, LLM

# Industry-Standard Markdown RAG Pipeline (replaces legacy JSON pipeline)
from markdown_rag_pipeline import MarkdownRAGPipeline


# =============================================================================
# LLM Configuration (The Brain)
# =============================================================================

# Cache for LLM instance
_llm_instance: Optional[LLM] = None


def get_llm() -> LLM:
    """
    Initialize Groq LLM using CrewAI's native LLM class.
    CrewAI 1.9.x uses its own LLM wrapper for provider integrations.
    
    Returns:
        Configured LLM instance
        
    Raises:
        ValueError: If GROQ_API_KEY is not set
    """
    global _llm_instance
    
    # Return cached instance if available
    if _llm_instance is not None:
        return _llm_instance
    
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        raise ValueError(
            "GROQ_API_KEY not found. Please set your Groq API key in the .env file. "
            "Get your free API key at: https://console.groq.com"
        )
    
    logger.info("🧠 Initializing Groq LLM (llama-3.1-8b-instant)")
    
    # CrewAI native LLM configuration for Groq - using faster 8B model
    _llm_instance = LLM(
        model="groq/llama-3.1-8b-instant",
        api_key=api_key,
        temperature=0
    )
    
    return _llm_instance


# Global RAG pipeline instance (industry-standard Markdown-based)
_rag_pipeline: Optional[MarkdownRAGPipeline] = None


def get_rag_pipeline() -> Optional[MarkdownRAGPipeline]:
    """
    Get or initialize the industry-standard Markdown RAG pipeline.
    
    Pipeline: Markdown KB → Header-Aware Chunking → ChromaDB → Retrieve → Rerank
    
    Returns None if pipeline is not available.
    """
    global _rag_pipeline
    
    if _rag_pipeline is not None and _rag_pipeline.is_ready:
        return _rag_pipeline
    
    try:
        logger.info("🔍 Initializing Industry-Standard Markdown RAG Pipeline...")
        _rag_pipeline = MarkdownRAGPipeline(
            persist_directory="./vector_store",
            collection_name="agrisense_v2",
            chunk_size=800,
            chunk_overlap=150,
        )
        
        # Try Markdown knowledge base first (industry standard)
        md_kb_path = "./Web_Scraping_for_Agrisense/rag_pipeline/processed/markdown_kb"
        json_fallback = "./Web_Scraping_for_Agrisense/rag_pipeline/processed/rag_json/rag_documents.json"
        
        from pathlib import Path
        md_path = Path(md_kb_path)
        
        if md_path.exists() and list(md_path.glob('*.md')):
            logger.info("📚 Using Markdown knowledge base (Industry Standard)")
            success = _rag_pipeline.build(md_kb_path, force_rebuild=False)
        elif Path(json_fallback).exists():
            logger.info("📦 Markdown KB not found, using legacy JSON (run convert_to_markdown.py to upgrade)")
            success = _rag_pipeline.build_from_json_legacy(json_fallback, force_rebuild=False)
        else:
            logger.warning("⚠️ No knowledge base found - will use LLM knowledge only")
            _rag_pipeline = None
            return None
        
        if success:
            stats = _rag_pipeline.get_stats()
            logger.info(f"✅ RAG Pipeline ready with {stats.get('document_count', 0)} chunks")
            logger.info(f"   Reranker: {'✅ Active' if stats.get('reranker_available') else '❌ Not available'}")
            logger.info(f"   Format: {stats.get('format', 'unknown')}")
            return _rag_pipeline
        else:
            logger.warning("⚠️ RAG Pipeline initialization failed - will use LLM knowledge only")
            _rag_pipeline = None
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ RAG Pipeline unavailable: {e}")
        logger.warning("   Falling back to LLM-only mode (no document retrieval)")
        _rag_pipeline = None
        return None


def retrieve_context(disease_name: str, k: int = 5, use_reranker: bool = True, skip_cache: bool = False) -> tuple[str, list[dict], dict]:
    """
    Retrieve relevant agricultural documents using the industry-standard pipeline.
    
    Pipeline: Query → Expand → Over-fetch → Rerank → Top-K
    
    Args:
        disease_name: Name of the disease to search for
        k: Number of documents to retrieve
        use_reranker: Whether to apply cross-encoder reranking (False for ablation)
        skip_cache: Whether to bypass the result cache (True for evaluation runs)
        
    Returns:
        Tuple of (formatted_context_string, source_documents_list, latency_breakdown)
    """
    empty_latency = {'retrieval_ms': 0.0, 'rerank_ms': 0.0, 'total_ms': 0.0}
    pipeline = get_rag_pipeline()
    
    if not pipeline:
        logger.info("📚 No RAG pipeline available - using LLM knowledge only")
        return "", [], empty_latency
    
    try:
        # Use the pipeline's query method with disease filtering
        query = f"treatment symptoms prevention management {disease_name} tomato"
        context_str, docs, latency = pipeline.query(
            question=query,
            disease=disease_name,
            k=k,
            use_reranking=use_reranker,
            skip_cache=skip_cache,
        )
        
        if not docs:
            logger.info(f"📚 No documents found for {disease_name} - using LLM knowledge")
            return "", [], latency
        
        logger.info(f"✅ Retrieved {len(docs)} documents (reranker={'ON' if use_reranker else 'OFF'}) for context injection")
        
        return context_str, docs, latency
        
    except Exception as e:
        logger.error(f"❌ Error retrieving context: {e}")
        return "", [], empty_latency


# =============================================================================
# Agent Definitions (The Crew)
# =============================================================================

def create_agents(llm):
    """Create the single unified agent for agricultural advice"""
    
    # Single unified agent combining pathology and field expertise
    advisor = Agent(
        role='Agricultural Treatment Advisor',
        goal='Provide complete disease treatment advice with weather-aware safety recommendations',
        backstory='''You are an expert agricultural advisor combining deep knowledge of 
        tomato plant pathology with practical field experience. You provide evidence-based 
        treatment recommendations (both organic and chemical), adapt them for current weather 
        conditions, and always include critical safety protocols including PPE requirements 
        and harvest safety intervals. You deliver concise, actionable advice.''',
        allow_delegation=False,
        verbose=False,
        llm=llm
    )
    
    return advisor


# =============================================================================
# Task Definitions
# =============================================================================

def create_tasks(advisor, disease_name: str, weather: str, retrieved_context: str = "", weather_forecast: str = ""):
    """Create single unified task for the advisor agent"""
    
    # Build context-aware description
    context_section = ""
    if retrieved_context:
        context_section = f"""
        
KNOWLEDGE BASE CONTEXT:
{retrieved_context}

Use the above retrieved documents as your PRIMARY source of information.
"""
    
    # Build weather context
    weather_context = f"Current weather: {weather}"
    if weather_forecast:
        weather_context += f"\n\n7-DAY WEATHER FORECAST:\n{weather_forecast}"
    
    # Single unified task
    task_advise = Task(
        description=f'''You are advising on the specific tomato disease "{disease_name}". 
Your treatment MUST be specific to THIS disease — do NOT give generic advice.
{context_section}
{weather_context}

CRITICAL DISEASE-SPECIFIC RULES:
- For FUNGAL diseases (Early Blight, Late Blight, Leaf Mold, Septoria Leaf Spot, Target Spot): recommend appropriate FUNGICIDES with exact product names and dosages specific to the pathogen
- For BACTERIAL diseases (Bacterial Spot): recommend copper-based bactericides, NOT fungicides
- For VIRAL diseases (Yellow Leaf Curl Virus, Mosaic Virus): there is NO chemical cure — recommend removing infected plants, controlling insect vectors (whiteflies/aphids), and using resistant varieties
- For PEST infestations (Spider Mites): recommend miticides or insecticidal soap, NOT fungicides
- For Healthy plants: no treatment needed, just maintenance tips
- NEVER recommend chlorothalonil for viral diseases or pest infestations

Provide a comprehensive but CONCISE response covering:
1. Disease severity (Low/Medium/High)
2. Top 2 treatment options specific to "{disease_name}" with exact product names and dosages
3. SPECIFIC DAY RECOMMENDATION using the relative day labels from the forecast (today, tomorrow, day after tomorrow, or actual day name with date). Tell the farmer WHEN to act relative to NOW.
4. Required PPE and harvest safety interval specific to the products recommended
5. Best time of day to apply (early morning or late afternoon)

IMPORTANT FORMATTING RULES for action_plan:
- Write EXACTLY 3-4 numbered TREATMENT steps, then add a line "PREVENTION:", then 2-3 numbered PREVENTION steps
- Treatment steps: specific actions to address "{disease_name}" NOW
- One treatment step MUST use relative day references like "tomorrow", "today", or "day after tomorrow" — e.g., "Apply Mancozeb tomorrow (Wednesday) morning when dry conditions are expected" or "Best to start treatment today since weather is clear"
- Prevention steps: long-term measures specific to preventing "{disease_name}" recurrence
- NEVER repeat the same step in both sections
- Keep each step as ONE complete sentence
- NEVER split a step across lines

IMPORTANT FORMATTING RULES for weather_advisory:
- MUST use relative references: "today", "tomorrow", "the day after tomorrow", then day names for further days
- Example style: "The weather looks good tomorrow (Wednesday), you can proceed with treatment in the early morning. Avoid spraying on Friday as heavy rain is expected. Reapply next Monday if needed."
- Make it conversational and easy for a farmer to understand
- State which days are safe for treatment and which to avoid

OUTPUT FORMAT: Respond with ONLY a valid JSON object (no markdown, no code fences):
{{"severity": "Low|Medium|High", "action_plan": "1. First treatment step\\n2. Second treatment step\\n3. Third treatment step\\nPREVENTION:\\n1. First prevention step\\n2. Second prevention step", "safety_warning": "PPE and safety notes in one paragraph", "weather_advisory": "Day-specific weather timing advice referencing the forecast"}}''',
        expected_output='A JSON object with severity, action_plan, safety_warning, and weather_advisory keys.',
        agent=advisor
    )
    
    return [task_advise]


# =============================================================================
# Main Interface Function
# =============================================================================

# Treatment response cache for common diseases
_advice_cache: Dict[str, Dict[str, Any]] = {}


def get_agri_advice(
    disease_name: str, 
    weather_condition: str = "Partly Cloudy",
    weather_forecast: Optional[str] = None,
    rag_enabled: bool = True,
    use_reranker: bool = True,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Get agricultural treatment advice using CrewAI agent with RAG retrieval.
    
    Uses a single unified agent with fast 8B model for quick, comprehensive
    weather-aware treatment recommendations for detected tomato diseases.
    
    Args:
        disease_name: The detected disease name from vision model
        weather_condition: Current weather (e.g., 'Sunny', 'Rainy', 'Cloudy', 'Windy')
        weather_forecast: Optional 7-day forecast string
        rag_enabled: If False, skip retrieval entirely (LLM-only baseline for ablation)
        use_reranker: If False, skip cross-encoder reranking (ablation experiment)
        use_cache: If False, bypass response cache (for evaluation runs)
    
    Returns:
        Dictionary with:
        - severity, action_plan, safety_warning, weather_advisory
        - sources: List of source documents used (if RAG retrieval succeeded)
        - rag_enabled: Boolean indicating if RAG retrieval was successful
        - latency_breakdown: Dict with retrieval_ms, rerank_ms, generation_ms, total_ms
    """
    start_time = time.time()
    latency = {'retrieval_ms': 0.0, 'rerank_ms': 0.0, 'generation_ms': 0.0, 'total_ms': 0.0}
    
    # Normalize inputs
    disease_name = disease_name.strip()
    weather_condition = weather_condition.strip()
    
    # Check cache first (skip if use_cache=False for eval runs)
    cache_key = f"{disease_name.lower()}:{weather_condition.lower()}"
    if use_cache and cache_key in _advice_cache:
        logger.info(f"📦 Returning cached advice for: {disease_name}")
        return _advice_cache[cache_key]
    
    # Handle healthy plants - no need to invoke agents
    if disease_name.lower() == "healthy" or disease_name == "Model Not Loaded":
        response = {
            "severity": "None",
            "action_plan": "No treatment needed. Your tomato plant appears healthy! Continue regular care including adequate watering, proper spacing for air circulation, and monitoring for early signs of disease.",
            "safety_warning": "Maintain good garden hygiene. Remove any fallen leaves or debris to prevent disease. Inspect plants weekly for early detection.",
            "weather_advisory": f"Current weather: {weather_condition}. Adjust watering schedule based on conditions - water deeply but less frequently in humid weather.",
            "latency_breakdown": latency,
        }
        if use_cache:
            _advice_cache[cache_key] = response
        return response
    
    try:
        logger.info(f"🌱 Generating treatment advice for: {disease_name}")
        logger.info(f"🌤️  Weather condition: {weather_condition}")
        logger.info(f"⚙️  Config: rag_enabled={rag_enabled}, use_reranker={use_reranker}, use_cache={use_cache}")
        
        # Retrieve relevant documents from knowledge base (skip if rag_enabled=False)
        retrieved_context = ""
        source_docs = []
        if rag_enabled:
            retrieved_context, source_docs, retrieval_latency = retrieve_context(
                disease_name, k=5,
                use_reranker=use_reranker,
                skip_cache=not use_cache,
            )
            latency['retrieval_ms'] = retrieval_latency.get('retrieval_ms', 0.0)
            latency['rerank_ms'] = retrieval_latency.get('rerank_ms', 0.0)
        else:
            logger.info("📚 RAG disabled (LLM-only baseline mode)")
        
        # Initialize LLM
        llm = get_llm()
        
        # Create single unified agent
        advisor = create_agents(llm)
        
        # Create task with retrieved context and forecast
        tasks = create_tasks(advisor, disease_name, weather_condition, retrieved_context, weather_forecast or "")
        
        # Assemble the Crew
        crew = Crew(
            agents=[advisor],
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
        )
        
        # Execute the crew with timeout protection (30 seconds max)
        logger.info("⏳ Executing crew (30s timeout)...")
        t_gen_start = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(crew.kickoff)
            try:
                result = future.result(timeout=30)  # 30 second timeout
            except concurrent.futures.TimeoutError:
                logger.error("❌ Crew execution timed out after 30 seconds")
                latency['generation_ms'] = (time.time() - t_gen_start) * 1000
                latency['total_ms'] = (time.time() - start_time) * 1000
                fb = get_fallback_advice(disease_name, weather_condition)
                fb['latency_breakdown'] = latency
                return fb
        latency['generation_ms'] = (time.time() - t_gen_start) * 1000
        
        # Parse the result
        result_text = str(result).strip()
        response = parse_crew_response(result_text, disease_name, weather_condition)
        
        # Add source citations if available (now includes doc_id)
        if source_docs:
            response['sources'] = [
                {
                    'doc_id': doc.get('doc_id', 'unknown'),
                    'source': doc['source'],
                    'content_type': doc['content_type'],
                    'confidence': doc['confidence'],
                }
                for doc in source_docs
            ]
            response['rag_enabled'] = True
        else:
            response['sources'] = []
            response['rag_enabled'] = False
        
        latency['total_ms'] = (time.time() - start_time) * 1000
        response['latency_breakdown'] = latency
        
        # Cache successful response
        if use_cache:
            _advice_cache[cache_key] = response
        
        logger.info(
            f"✅ Advice generated in {latency['total_ms']:.0f}ms "
            f"(retrieval={latency['retrieval_ms']:.0f}ms "
            f"rerank={latency['rerank_ms']:.0f}ms "
            f"generation={latency['generation_ms']:.0f}ms "
            f"RAG={'ON' if source_docs else 'OFF'})"
        )
        
        return response
        
    except ValueError as e:
        # API key issues
        logger.error(f"Configuration error: {str(e)}")
        latency['total_ms'] = (time.time() - start_time) * 1000
        return {
            "severity": "Unknown",
            "action_plan": f"AI advisor unavailable: {str(e)}. Please consult a local agricultural extension service for treatment of {disease_name}.",
            "safety_warning": "Always wear protective equipment when handling any pesticides or fungicides.",
            "weather_advisory": f"Current weather: {weather_condition}. Monitor conditions before applying any treatments.",
            "latency_breakdown": latency,
        }
    except Exception as e:
        # Other errors - provide helpful fallback
        logger.error(f"❌ CrewAI error: {str(e)}")
        latency['total_ms'] = (time.time() - start_time) * 1000
        fb = get_fallback_advice(disease_name, weather_condition)
        fb['latency_breakdown'] = latency
        return fb


def get_fallback_advice(disease_name: str, weather_condition: str) -> Dict[str, Any]:
    """
    Provide fallback treatment advice when AI system is unavailable.
    
    Uses a knowledge base of common tomato diseases to provide
    basic treatment recommendations.
    """
    # Basic treatment knowledge base
    treatments = {
        "bacterial spot": {
            "severity": "Medium",
            "action": "Apply copper-based bactericide. Remove and destroy infected leaves. Avoid overhead watering.",
        },
        "early blight": {
            "severity": "Medium", 
            "action": "Apply fungicide containing chlorothalonil or copper. Remove lower infected leaves. Mulch around plants.",
        },
        "late blight": {
            "severity": "High",
            "action": "Apply fungicide immediately (chlorothalonil or mancozeb). Remove infected plants. Do not compost infected material.",
        },
        "leaf mold": {
            "severity": "Low",
            "action": "Improve air circulation. Reduce humidity. Apply sulfur-based fungicide if needed.",
        },
        "septoria leaf spot": {
            "severity": "Medium",
            "action": "Remove infected leaves. Apply fungicide. Avoid wetting foliage when watering.",
        },
        "spider mites": {
            "severity": "Medium",
            "action": "Spray with insecticidal soap or neem oil. Increase humidity. Introduce predatory mites.",
        },
        "target spot": {
            "severity": "Medium",
            "action": "Apply fungicide (chlorothalonil). Remove infected leaves. Rotate crops next season.",
        },
        "yellow leaf curl virus": {
            "severity": "High",
            "action": "Remove infected plants immediately. Control whitefly vectors. Use resistant varieties.",
        },
        "mosaic virus": {
            "severity": "High",
            "action": "Remove and destroy infected plants. Control aphids. Disinfect tools between plants.",
        },
    }
    
    # Find matching treatment
    disease_lower = disease_name.lower()
    treatment = None
    
    for key, value in treatments.items():
        if key in disease_lower or disease_lower in key:
            treatment = value
            break
    
    if treatment:
        return {
            "severity": treatment["severity"],
            "action_plan": treatment["action"],
            "safety_warning": "Always wear gloves and protective eyewear when handling fungicides or pesticides. Follow product label instructions carefully.",
            "weather_advisory": f"Current weather: {weather_condition}. Apply treatments in calm conditions, preferably early morning or evening."
        }
    else:
        return {
            "severity": "Unknown",
            "action_plan": f"For {disease_name}, consult your local agricultural extension office or a plant pathologist for specific treatment recommendations.",
            "safety_warning": "Always follow product label instructions for any treatments.",
            "weather_advisory": f"Current weather: {weather_condition}. Conditions may affect treatment timing and efficacy."
        }


def parse_crew_response(text: str, disease: str, weather: str) -> dict:
    """Parse CrewAI crew output to extract JSON advice.
    
    Handles common LLM quirks:
    - Markdown code fences (```json ... ```)
    - Nested/malformed JSON
    - Plain-text fallback when JSON extraction fails
    """
    # Strip markdown code fences first (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r'```(?:json)?\s*', '', text).strip()
    cleaned = cleaned.rstrip('`').strip()

    # Helper: validate and fill missing keys
    def _validate(parsed: dict) -> dict | None:
        if all(k in parsed for k in ['severity', 'action_plan', 'safety_warning']):
            if 'weather_advisory' not in parsed:
                parsed['weather_advisory'] = f"Current weather: {weather}"
            return parsed
        return None

    # 1. Try the cleaned text as complete JSON
    for candidate in [cleaned, text]:
        try:
            parsed = json.loads(candidate)
            result = _validate(parsed)
            if result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # 2. Find the outermost { ... } pair (handles nested braces)
    brace_start = cleaned.find('{')
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(cleaned)):
            if cleaned[i] == '{':
                depth += 1
            elif cleaned[i] == '}':
                depth -= 1
                if depth == 0:
                    json_str = cleaned[brace_start:i + 1]
                    try:
                        parsed = json.loads(json_str)
                        result = _validate(parsed)
                        if result:
                            return result
                    except json.JSONDecodeError:
                        # Try fixing common issues: unquoted keys, trailing commas
                        try:
                            fixed = re.sub(r'(\w+)\s*:', r'"\1":', json_str)
                            fixed = re.sub(r',\s*}', '}', fixed)
                            parsed = json.loads(fixed)
                            result = _validate(parsed)
                            if result:
                                return result
                        except json.JSONDecodeError:
                            pass
                    break

    # 3. Try key-value extraction as last structured attempt
    kv_result = {}
    for key in ['severity', 'action_plan', 'safety_warning', 'weather_advisory']:
        # Match patterns like:  "action_plan": "..." or action_plan: ...
        pattern = rf'["\']?{key}["\']?\s*:\s*["\']?(.*?)(?:["\']?\s*,\s*["\']?\w+["\']?\s*:|["\']?\s*\}}|$)'
        m = re.search(pattern, cleaned, re.DOTALL | re.IGNORECASE)
        if m:
            val = m.group(1).strip().strip('"\'').strip(',').strip()
            if val:
                kv_result[key] = val
    if _validate(kv_result):
        return kv_result

    # 4. Final fallback: structured response from plain text
    severity = "Medium"
    if "severe" in text.lower() or "high" in text.lower():
        severity = "High"
    elif "mild" in text.lower() or "low" in text.lower():
        severity = "Low"
    
    # Clean up text for action plan — remove JSON artifacts but keep content
    action_text = text[:800] if len(text) > 800 else text
    action_text = re.sub(r'```(?:json)?', '', action_text)
    action_text = re.sub(r'[{}]', '', action_text)
    action_text = re.sub(r'"?\w+"?\s*:', '', action_text)  # Remove key: patterns
    action_text = re.sub(r'["\']', '', action_text)
    action_text = re.sub(r'\s+', ' ', action_text).strip()
    
    return {
        "severity": severity,
        "action_plan": action_text if len(action_text) > 20 else f"Consult a local agronomist for {disease} treatment.",
        "safety_warning": "Always wear protective gloves, goggles, and long sleeves when handling treatments. Observe a minimum 3-day pre-harvest interval.",
        "weather_advisory": f"Current weather: {weather}. Check conditions before applying treatments."
    }


# =============================================================================
# Test Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing AgriSense Multi-Agent RAG System")
    print("=" * 60)
    
    # Test with a disease
    test_disease = "Early Blight"
    test_weather = "Sunny"
    
    print(f"\n📋 Test Case: {test_disease} in {test_weather} weather\n")
    
    result = get_agri_advice(test_disease, test_weather)
    
    print("\n" + "=" * 60)
    print("📄 Final Result:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
