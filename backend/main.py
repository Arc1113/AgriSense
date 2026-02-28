"""
AgriSense Backend - FastAPI Server
RAG-Powered Treatment Advice API

Features:
- Multi-agent RAG system for treatment advice (CrewAI + Groq)
- Weather-aware treatment recommendations
- Comprehensive error handling and logging
- Response time tracking
- Structured API responses with Pydantic models

Note: Disease detection is handled on-device (Flutter TFLite).
      This backend focuses on RAG-powered advice generation.
"""

import os

# CRITICAL: Set these at the very top, before ANY imports
# Prevents transformers from trying to import TensorFlow
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['USE_TF'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import time
import logging
import asyncio
from datetime import datetime
from functools import lru_cache
from typing import Optional, Dict, Any, List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import ipaddress

from fastapi import FastAPI, HTTPException, Query, Request, Body, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from rag_agent import get_agri_advice
from weather_service import get_weather_forecast, get_api_usage_stats, geolocate_ip

# Deployment mode: 'rag_only' strips ML models (TF, YOLO, ESP32)
# Set via environment variable DEPLOY_MODE=rag_only
DEPLOY_MODE = os.getenv("DEPLOY_MODE", "full").lower().strip()
_is_rag_only = DEPLOY_MODE == "rag_only"

if not _is_rag_only:
    from esp32_client import ESP32Client
    from yolo_detector import YOLODetector
    from robotics_scanner import RoboticsScanner, ScanState
else:
    # Stubs so the rest of the file doesn't crash on references
    ESP32Client = None  # type: ignore
    YOLODetector = None  # type: ignore
    RoboticsScanner = None  # type: ignore
    ScanState = None  # type: ignore

# Thread pool for running blocking operations
_executor = ThreadPoolExecutor(max_workers=4)

# Load environment variables
load_dotenv()

logger_early = logging.getLogger("AgriSense")
if _is_rag_only:
    logger_early.info("🚀 DEPLOY_MODE=rag_only — ML models (TF, YOLO, ESP32) disabled")

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AgriSense")


# =============================================================================
# Pydantic Models for API Responses
# =============================================================================
class WeatherCondition(str, Enum):
    SUNNY = "Sunny"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    WINDY = "Windy"
    HUMID = "Humid"
    HOT = "Hot"
    COLD = "Cold"


# All 10 tomato disease classes (same as Flutter on-device model)
DISEASE_CLASSES = [
    "Bacterial Spot",
    "Early Blight",
    "Late Blight",
    "Leaf Mold",
    "Septoria Leaf Spot",
    "Spider Mites",
    "Target Spot",
    "Yellow Leaf Curl Virus",
    "Mosaic Virus",
    "Healthy"
]


class SourceDocument(BaseModel):
    """Source document citation"""
    doc_id: str = Field(default="unknown", description="Unique document chunk identifier for citation tracking")
    source: str = Field(..., description="Source organization (FAO, PCAARRD, UC IPM, etc.)")
    content_type: str = Field(..., description="Content type (Treatment, Symptoms, Prevention)")
    confidence: float = Field(..., ge=0, le=1, description="Document relevance confidence")


class LatencyBreakdown(BaseModel):
    """Component-level latency for evaluation"""
    retrieval_ms: float = Field(default=0.0, description="ChromaDB retrieval time")
    rerank_ms: float = Field(default=0.0, description="Cross-encoder reranking time")
    generation_ms: float = Field(default=0.0, description="LLM generation time")
    total_ms: float = Field(default=0.0, description="Total RAG pipeline time")


class TreatmentAdvice(BaseModel):
    """AI-generated treatment advice"""
    severity: str = Field(..., description="Disease severity: Low, Medium, High, or None")
    action_plan: str = Field(..., description="Recommended treatment actions")
    safety_warning: str = Field(..., description="Safety precautions and PPE requirements")
    weather_advisory: str = Field(..., description="Weather-specific recommendations")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents used")
    rag_enabled: bool = Field(default=False, description="Whether RAG retrieval was used")
    latency_breakdown: Optional[LatencyBreakdown] = Field(default=None, description="Component-level latency (for evaluation)")


class PredictionResponse(BaseModel):
    """Complete prediction response"""
    success: bool = Field(True, description="Whether the request was successful")
    disease: str = Field(..., description="Disease name (from on-device detection)")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence (from on-device model)")
    is_healthy: bool = Field(..., description="Whether the plant is healthy")
    model_used: str = Field(..., description="ML model used on-device (mobile/resnet)")
    weather: str = Field(..., description="Weather condition considered")
    advice: TreatmentAdvice = Field(..., description="AI-generated treatment advice")
    response_time_ms: float = Field(..., description="Total response time in milliseconds")
    timestamp: str = Field(..., description="ISO timestamp of prediction")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    rag_available: bool = Field(default=False, description="Whether RAG pipeline is ready")
    version: str = Field(..., description="API version")


class APIInfoResponse(BaseModel):
    """API information response"""
    name: str
    version: str
    description: str
    documentation: str
    endpoints: Dict[str, str]
    supported_models: List[str]
    supported_weather: List[str]


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: str


# =============================================================================
# Application State
# =============================================================================
_startup_time: Optional[float] = None


# =============================================================================
# Lifespan Handler
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - initialize RAG pipeline and robotics on startup"""
    global _startup_time
    _startup_time = time.time()

    logger.info("🌱 AgriSense API starting up...")

    # Initialize RAG vector store
    logger.info("🔍 Initializing RAG pipeline...")
    try:
        from rag_agent import get_rag_pipeline
        rag_pipeline = get_rag_pipeline()
        if rag_pipeline and rag_pipeline.is_ready:
            stats = rag_pipeline.get_stats()
            logger.info(f"✅ RAG Pipeline ready with {stats.get('document_count', 0)} chunks")
            logger.info(f"   Reranker: {'✅ Active' if stats.get('reranker_available') else '❌ Disabled'}")
            logger.info(f"   Format: {stats.get('format', 'unknown')}")
        else:
            logger.warning("⚠️ RAG Pipeline not available - using LLM knowledge only")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize RAG pipeline: {e}")
        logger.warning("   RAG functionality will be disabled")

    # ---------- ML model loading (skipped in rag_only mode) ----------
    if not _is_rag_only:
        # Initialize YOLO leaf detector (ONNX)
        logger.info("🔍 Loading YOLOv8s ONNX model for leaf detection...")
        yolo = YOLODetector()
        yolo_loaded = yolo.load()
        app.state.yolo = yolo
        if yolo_loaded:
            logger.info("✅ YOLO leaf detector loaded")
        else:
            logger.warning("⚠️ YOLO model not loaded - robotics scanning will be limited")

        # Initialize disease classification models (TensorFlow/Keras)
        logger.info("🔍 Loading disease classification models...")
        try:
            import vision_engine
            model_status = vision_engine.load_models()
            app.state.vision_engine = vision_engine
            logger.info(f"✅ Disease models loaded: {model_status}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load disease models: {e}")
            app.state.vision_engine = None

        # Initialize ESP32 client and robotics scanner
        esp32_client = ESP32Client()
        app.state.esp32_client = esp32_client

        classify_fn = None
        if app.state.vision_engine:
            classify_fn = app.state.vision_engine.predict_disease

        app.state.scanner = RoboticsScanner(
            esp32_client=esp32_client,
            yolo_detector=yolo,
            classify_fn=classify_fn,
            advice_fn=get_agri_advice,
            weather_fn=get_weather_forecast,
        )
        logger.info("✅ Robotics scanner initialized")
    else:
        # Stubs for rag_only mode
        app.state.yolo = None
        app.state.vision_engine = None
        app.state.esp32_client = None
        app.state.scanner = None
        logger.info("⏭️  Skipped ML model loading (DEPLOY_MODE=rag_only)")

    logger.info(f"🚀 AgriSense API ready to serve requests (mode={DEPLOY_MODE})")
    yield

    # Cleanup
    if not _is_rag_only and app.state.esp32_client and app.state.esp32_client.is_connected:
        await app.state.esp32_client.disconnect()
    logger.info("🛑 AgriSense API shutting down...")


# =============================================================================
# FastAPI App Initialization
# =============================================================================
app = FastAPI(
    title="AgriSense API",
    description="""
## 🌱 AgriSense - RAG-Powered Treatment Advice API

An intelligent API for generating treatment recommendations using a 
multi-agent AI system (CrewAI + Groq) with Retrieval-Augmented Generation.

### Architecture
- **Disease Detection**: Handled on-device via TFLite (Flutter mobile app)
- **Treatment Advice**: RAG-powered multi-agent system (this backend)
- **Weather Integration**: Auto-fetches conditions from Open-Meteo (free)

### Supported Diseases
- Bacterial Spot, Early Blight, Late Blight, Leaf Mold
- Septoria Leaf Spot, Spider Mites, Target Spot
- Yellow Leaf Curl Virus, Mosaic Virus
- ✅ Healthy (no disease detected)
    """,
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Service health and status endpoints"},
        {"name": "Prediction", "description": "Disease advice endpoints"},
        {"name": "Info", "description": "API information"},
        {"name": "Robotics", "description": "ESP32-CAM robotics scanning endpoints"}
    ]
)


# =============================================================================
# Custom Exception Handlers
# =============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler that safely serializes validation errors even when
    the request body contains raw binary data (e.g. image uploads sent
    to a JSON endpoint).  The default FastAPI handler calls bytes.decode()
    on every body fragment, which crashes with UnicodeDecodeError for
    non-UTF-8 payloads.
    """
    safe_errors = []
    for err in exc.errors():
        safe_err = dict(err)
        # Replace any bytes values with a placeholder string
        if "input" in safe_err and isinstance(safe_err["input"], bytes):
            safe_err["input"] = f"<binary data, {len(safe_err['input'])} bytes>"
        # Also sanitize nested ctx values
        if "ctx" in safe_err and isinstance(safe_err.get("ctx"), dict):
            for k, v in safe_err["ctx"].items():
                if isinstance(v, bytes):
                    safe_err["ctx"][k] = f"<binary data, {len(v)} bytes>"
        safe_errors.append(safe_err)

    return JSONResponse(
        status_code=422,
        content={"detail": safe_errors},
    )


# =============================================================================
# Middleware
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (time.time() - start_time) * 1000
    
    # Log request details
    logger.info(
        f"{request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Duration: {duration:.2f}ms"
    )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration:.2f}ms"
    
    return response


# =============================================================================
# Exception Handlers
# =============================================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured response"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=f"Request to {request.url.path} failed",
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if app.debug else None,
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_model=APIInfoResponse, tags=["Health"])
async def root():
    """
    Root endpoint with comprehensive API information.
    
    Returns API metadata, available endpoints, and supported options.
    """
    return APIInfoResponse(
        name="AgriSense API",
        version="3.0.0",
        description="RAG-Powered Treatment Advice API (disease detection on-device)",
        documentation="/docs",
        endpoints={
            "GET /": "API information and documentation links",
            "GET /health": "Detailed health check with uptime and RAG status",
            "GET /classes": "List all detectable disease classes",
            "GET /weather/usage": "Open-Meteo API usage statistics",
            "POST /predict": "Get RAG-powered treatment advice for a detected disease"
        },
        supported_models=["mobile", "resnet"],
        supported_weather=[w.value for w in WeatherCondition]
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns service status, uptime, and RAG pipeline availability.
    Useful for load balancers and monitoring systems.
    """
    global _startup_time
    
    uptime = time.time() - _startup_time if _startup_time else 0
    
    # Check RAG pipeline status
    rag_ready = False
    try:
        from rag_agent import get_rag_pipeline
        rag_pipeline = get_rag_pipeline()
        rag_ready = rag_pipeline is not None and rag_pipeline.is_ready
    except Exception:
        pass
    
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(uptime, 2),
        rag_available=rag_ready,
        version="3.0.0"
    )


@app.get("/debug/rag_stats", tags=["Health"])
async def debug_rag_stats():
    """Temporary debug endpoint: return RAG pipeline and vector-store status.

    Intended for troubleshooting only. Returns pipeline `is_ready`, stats from
    `get_rag_pipeline().get_stats()` and a listing of files under `/app/vector_store`.
    """
    try:
        from rag_agent import get_rag_pipeline

        pipeline = get_rag_pipeline()
        if not pipeline:
            return JSONResponse(status_code=200, content={
                "pipeline": None,
                "message": "RAG pipeline not initialized or no KB found"
            })

        stats = {}
        try:
            stats = pipeline.get_stats() if hasattr(pipeline, 'get_stats') else {}
        except Exception as e:
            stats = {"error_getting_stats": str(e)}

        # Attempt to list files in the mounted vector_store path
        import os
        vector_files = []
        try:
            mount_path = "/app/vector_store"
            if os.path.exists(mount_path) and os.path.isdir(mount_path):
                for root, dirs, files in os.walk(mount_path):
                    for f in files:
                        # provide relative paths to avoid leaking absolute host info
                        rel = os.path.relpath(os.path.join(root, f), mount_path)
                        vector_files.append(rel)
            else:
                vector_files = None
        except Exception as e:
            vector_files = {"error_listing": str(e)}

        return JSONResponse(status_code=200, content={
            "pipeline": True,
            "is_ready": getattr(pipeline, 'is_ready', None),
            "stats": stats,
            "vector_store_files": vector_files,
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/debug/inspect_vector_store", tags=["Health"])
async def debug_inspect_vector_store():
    """Temporary debug endpoint: try to load Chroma directly and return exception text.

    This endpoint attempts to instantiate the production `IndustryVectorStore` and
    —if loading fails— directly constructs a `Chroma` instance to capture the
    underlying exception message. It also lists files under `/app/vector_store`.
    """
    result = {
        "vector_store_path": "/app/vector_store",
        "files": None,
        "load_result": None,
        "direct_chroma_error": None,
    }

    # List files under the mounted vector_store
    try:
        import os
        mount_path = "/app/vector_store"
        if os.path.exists(mount_path) and os.path.isdir(mount_path):
            files = []
            for root, dirs, files_list in os.walk(mount_path):
                for f in files_list:
                    rel = os.path.relpath(os.path.join(root, f), mount_path)
                    files.append(rel)
            result["files"] = files
        else:
            result["files"] = []
    except Exception as e:
        result["files"] = {"error": str(e)}

    # Try to load via IndustryVectorStore first to follow runtime behavior
    try:
        from markdown_rag_pipeline import IndustryVectorStore

        ivs = IndustryVectorStore(persist_directory="/app/vector_store", collection_name="agrisense_v2")
        try:
            ok = ivs.load_existing()
            result["load_result"] = {"loaded": bool(ok), "collection_name": ivs.collection_name}
            if ok and getattr(ivs, "vectorstore", None):
                try:
                    cnt = ivs.vectorstore._collection.count()
                    result["load_result"]["count"] = int(cnt)
                except Exception:
                    result["load_result"]["count"] = None
        except Exception as e:
            result["load_result"] = {"error": str(e)}

        # If load_existing returned False, attempt to instantiate Chroma directly
        if not result.get("load_result") or not result["load_result"].get("loaded"):
            try:
                # Lazy import Chroma from langchain_community
                from langchain_community.vectorstores import Chroma
                ch = Chroma(persist_directory="/app/vector_store", embedding_function=ivs.embeddings, collection_name=ivs.collection_name)
                try:
                    cnt = ch._collection.count()
                    result["direct_chroma_error"] = {"loaded": True, "count": int(cnt)}
                except Exception:
                    result["direct_chroma_error"] = {"loaded": True, "count": None}
            except Exception as e:
                result["direct_chroma_error"] = {"error": str(e)}

    except Exception as e:
        result["load_result"] = {"error": str(e)}

    return JSONResponse(status_code=200, content=result)


@app.get("/classes", tags=["Info"])
async def get_classes():
    """
    Get list of all detectable disease classes.
    
    Returns the 10 tomato conditions that the on-device model can detect,
    including the "Healthy" class.
    """
    return {
        "classes": DISEASE_CLASSES,
        "total": len(DISEASE_CLASSES),
        "healthy_class": "Healthy"
    }


@app.get("/weather/usage", tags=["Health"])
async def weather_api_usage():
    """
    Get current Open-Meteo API usage statistics.
    
    Returns:
    - Calls made today
    - Daily limit (9,500 with safety buffer, max 10,000)
    - Remaining calls
    - Usage percentage
    
    Note: Open-Meteo is completely FREE with no API key required!
    """
    stats = get_api_usage_stats()
    return {
        "status": "ok",
        "api": "Open-Meteo (Free)",
        "calls_today": stats["calls_today"],
        "daily_limit": stats["limit"],
        "remaining": stats["remaining"],
        "percentage_used": round(stats["percentage_used"], 2),
        "date": stats["date"],
        "note": "Open-Meteo is free - no API key needed!",
        "warning": "Approaching limit" if stats["remaining"] < 500 else None
    }


class PredictRequest(BaseModel):
    """Request body for /predict endpoint"""
    disease: str = Field(..., description="Disease name detected on-device (e.g., 'Early Blight')")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence from on-device model (0-1)")
    model_used: str = Field(default="mobile", description="On-device model used: 'mobile' or 'resnet'")
    weather: Optional[str] = Field(default=None, description="Current weather condition (optional - auto-fetched if not provided)")
    forecast: Optional[str] = Field(default=None, description="7-day weather forecast (optional - auto-fetched if not provided)")
    latitude: Optional[float] = Field(default=None, description="Latitude for weather lookup (defaults to Davao City)", ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, description="Longitude for weather lookup (defaults to Davao City)", ge=-180, le=180)


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(request: PredictRequest, http_request: Request):
    """
    🔍 Get RAG-powered treatment advice for a detected disease.
    
    The Flutter mobile app detects the disease on-device using TFLite,
    then sends the result here to get AI-generated treatment advice
    from the multi-agent RAG system.
    
    This endpoint:
    1. Receives disease name + confidence from on-device detection
    2. Auto-fetches current weather and 7-day forecast (if not provided)
    3. Generates AI treatment advice using multi-agent RAG system
    4. Considers weather forecast for optimal treatment timing
    5. Returns comprehensive results with source citations
    
    ### Request (JSON body)
    - **disease**: Disease name from on-device TFLite model (required)
    - **confidence**: Detection confidence 0-1 (required)
    - **model_used**: Which on-device model was used - 'mobile' or 'resnet'
    - **weather** (optional): Current weather - auto-fetched if not provided
    - **forecast** (optional): 7-day forecast - auto-fetched if not provided
    - **latitude** (optional): Location for weather - defaults to Davao City
    - **longitude** (optional): Location for weather - defaults to Davao City
    
    ### Example
    ```bash
    curl -X POST "http://localhost:8000/predict" \\
      -H "Content-Type: application/json" \\
      -d '{
        "disease": "Early Blight",
        "confidence": 0.92,
        "model_used": "mobile",
        "latitude": 7.0731,
        "longitude": 125.6128
      }'
    ```
    """
    start_time = time.time()
    
    # Validate disease name
    if request.disease not in DISEASE_CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown disease '{request.disease}'. Valid classes: {DISEASE_CLASSES}"
        )
    
    try:
        disease_name = request.disease
        confidence = request.confidence
        is_healthy = disease_name.lower() == "healthy"
        
        logger.info(f"📱 On-device detection: {disease_name} ({confidence:.2%}) via {request.model_used}")
        
        # Fetch weather data if not provided
        current_weather = request.weather
        weather_forecast = request.forecast

        # Resolve location: prefer request lat/lon, else geolocate client IP, else default
        resolved_lat = request.latitude
        resolved_lon = request.longitude
        resolved_label = "Davao City (default)"

        if resolved_lat is None or resolved_lon is None:
            client_ip = http_request.headers.get("x-forwarded-for")
            if client_ip:
                client_ip = client_ip.split(",")[0].strip()
            else:
                client_ip = http_request.client.host if http_request.client else None

            if client_ip:
                try:
                    ip_obj = ipaddress.ip_address(client_ip)
                    if ip_obj.is_global:
                        geo = geolocate_ip(client_ip)
                        if geo:
                            resolved_lat, resolved_lon, resolved_label = geo
                            logger.info(f"📍 Auto-located user via IP {client_ip}: {resolved_label} ({resolved_lat},{resolved_lon})")
                except ValueError:
                    pass  # Ignore invalid IPs

        if not current_weather or not weather_forecast:
            location_str = resolved_label if (resolved_lat is not None and resolved_lon is not None) else "Davao City (default)"
            logger.info(f"🌤️ Auto-fetching weather for {location_str}...")
            
            api_weather, api_forecast = get_weather_forecast(
                lat=resolved_lat,
                lon=resolved_lon,
                location_name=location_str
            )
            
            if not current_weather and api_weather:
                current_weather = api_weather
                logger.info(f"   ✅ Current weather: {current_weather}")
            
            if not weather_forecast and api_forecast:
                weather_forecast = api_forecast
                logger.info(f"   ✅ Forecast retrieved")
        
        # Get AI-generated treatment advice with weather forecast (in thread pool)
        logger.info(f"🤖 Generating RAG treatment advice for {disease_name}...")
        loop = asyncio.get_event_loop()
        advice_dict = await loop.run_in_executor(
            _executor,
            lambda: get_agri_advice(
                disease_name, 
                weather_condition=current_weather,
                weather_forecast=weather_forecast
            )
        )
        
        # Extract latency_breakdown before constructing Pydantic model
        latency_raw = advice_dict.pop('latency_breakdown', None)
        advice = TreatmentAdvice(**advice_dict)
        if latency_raw:
            advice.latency_breakdown = LatencyBreakdown(**latency_raw)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        logger.info(f"✅ Advice generated in {response_time:.0f}ms (RAG: {advice.rag_enabled})")
        
        return PredictionResponse(
            success=True,
            disease=disease_name,
            confidence=confidence,
            is_healthy=is_healthy,
            model_used=request.model_used,
            weather=current_weather,
            advice=advice,
            response_time_ms=round(response_time, 2),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Advice generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Advice generation failed: {str(e)}"
        )


@app.post("/predict/image", response_model=PredictionResponse, tags=["Prediction"])
async def predict_image(
    http_request: Request,
    file: UploadFile = File(..., description="Plant leaf image (JPEG/PNG)"),
    model_type: str = Query(default="mobilenet", description="Classification model: 'mobilenet' or 'resnet'"),
    weather: Optional[str] = Query(default=None, description="Current weather condition"),
    latitude: Optional[float] = Query(default=None, description="Latitude for weather lookup", ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, description="Longitude for weather lookup", ge=-180, le=180),
):
    # Guard: not available in rag_only deployment
    if _is_rag_only:
        raise HTTPException(
            status_code=501,
            detail="Image classification is not available in RAG-only deployment. "
                   "Use POST /predict with on-device detection results instead."
        )
    """
    \U0001f4f7 Upload a plant leaf image for server-side disease classification + RAG advice.

    This endpoint:
    1. Receives a JPEG/PNG image from the web frontend
    2. Classifies the disease using MobileNetV2 or ResNet50 (TensorFlow/Keras)
    3. Auto-fetches weather data
    4. Generates RAG-powered treatment advice
    5. Returns comprehensive results with source citations

    ### Example (curl)
    ```bash
    curl -X POST "http://localhost:8000/predict/image" \\
      -F "file=@leaf.jpg" \\
      -G -d "model_type=mobilenet"
    ```
    """
    start_time = time.time()

    # --- 1. Validate vision engine ---
    vision = app.state.vision_engine
    if vision is None:
        raise HTTPException(
            status_code=503,
            detail="Disease classification models are not loaded. Please try again later."
        )

    # --- 2. Read & validate image bytes ---
    image_bytes = await file.read()
    if not image_bytes or len(image_bytes) < 100:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or too small.")

    content_type = file.content_type or ""
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Expected an image file, got '{content_type}'.")

    # --- 3. Classify image (blocking → run in thread pool) ---
    try:
        loop = asyncio.get_event_loop()
        classification = await loop.run_in_executor(
            _executor,
            lambda: vision.predict_disease(image_bytes, model_type=model_type)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Classification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Image classification failed: {e}")

    disease_name = classification["class"]
    confidence = classification["confidence"]
    is_healthy = disease_name.lower() == "healthy"

    logger.info(
        f"\U0001f4f7 Server-side classification: {disease_name} ({confidence:.2%}) "
        f"via {model_type} in {classification.get('inference_time_ms', 0):.0f}ms"
    )

    # --- 4. Fetch weather ---
    current_weather = weather
    weather_forecast = None

    resolved_lat = latitude
    resolved_lon = longitude
    resolved_label = "Davao City (default)"

    if resolved_lat is None or resolved_lon is None:
        client_ip = http_request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = http_request.client.host if http_request.client else None

        if client_ip:
            try:
                ip_obj = ipaddress.ip_address(client_ip)
                if ip_obj.is_global:
                    geo = geolocate_ip(client_ip)
                    if geo:
                        resolved_lat, resolved_lon, resolved_label = geo
            except ValueError:
                pass

    if not current_weather or not weather_forecast:
        try:
            api_weather, api_forecast = get_weather_forecast(
                lat=resolved_lat, lon=resolved_lon, location_name=resolved_label
            )
            if not current_weather and api_weather:
                current_weather = api_weather
            if not weather_forecast and api_forecast:
                weather_forecast = api_forecast
        except Exception as e:
            logger.warning(f"Weather fetch failed: {e}")
            current_weather = current_weather or "Unknown"

    # --- 5. Generate RAG advice (blocking → thread pool) ---
    try:
        advice_dict = await loop.run_in_executor(
            _executor,
            lambda: get_agri_advice(
                disease_name,
                weather_condition=current_weather,
                weather_forecast=weather_forecast
            )
        )
        # Extract latency_breakdown before constructing Pydantic model
        latency_raw = advice_dict.pop('latency_breakdown', None)
        advice = TreatmentAdvice(**advice_dict)
        if latency_raw:
            advice.latency_breakdown = LatencyBreakdown(**latency_raw)
    except Exception as e:
        logger.error(f"RAG advice generation failed: {e}", exc_info=True)
        advice = TreatmentAdvice(
            severity="Unknown",
            action_plan=f"Disease detected: {disease_name}. Please consult a local agronomist for treatment.",
            safety_warning="Wear gloves and wash hands after handling infected plants.",
            weather_advisory=f"Current weather: {current_weather or 'Unknown'}",
            sources=[],
            rag_enabled=False
        )

    response_time = (time.time() - start_time) * 1000
    logger.info(f"\u2705 Image prediction complete in {response_time:.0f}ms")

    return PredictionResponse(
        success=True,
        disease=disease_name,
        confidence=confidence,
        is_healthy=is_healthy,
        model_used=model_type,
        weather=current_weather or "Unknown",
        advice=advice,
        response_time_ms=round(response_time, 2),
        timestamp=datetime.utcnow().isoformat(),
    )


# =============================================================================
# ESP32-CAM Robotics Endpoints
# =============================================================================

class MotorDirection(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    CENTER = "center"
    STOP = "stop"


class ESP32ConnectRequest(BaseModel):
    """Request to connect to an ESP32-CAM device"""
    ip_address: str = Field(..., description="ESP32-CAM IP address (e.g., '192.168.1.100')")
    port: int = Field(default=80, description="ESP32-CAM HTTP port")


class MotorControlRequest(BaseModel):
    """Motor control command for pan-tilt servos"""
    direction: MotorDirection = Field(..., description="Direction: left, right, up, down, center, or stop")
    step: int = Field(default=5, ge=1, le=45, description="Step size in degrees (1-45)")


class AutoScanRequest(BaseModel):
    """Auto-scan configuration for raster pattern"""
    model_type: str = Field(default="mobilenet", description="Classification model: 'mobilenet' or 'resnet'")
    detection_confidence: float = Field(default=0.25, ge=0.1, le=1.0, description="YOLO detection confidence threshold")
    pan_min: int = Field(default=0, ge=0, le=180, description="Minimum pan angle")
    pan_max: int = Field(default=180, ge=0, le=180, description="Maximum pan angle")
    tilt_min: int = Field(default=30, ge=0, le=180, description="Minimum tilt angle")
    tilt_max: int = Field(default=120, ge=0, le=180, description="Maximum tilt angle")
    step_size: int = Field(default=15, ge=5, le=45, description="Degrees between scan positions")


class SetPositionRequest(BaseModel):
    """Absolute servo positioning"""
    pan: int = Field(..., ge=0, le=180, description="Pan angle in degrees (0-180)")
    tilt: int = Field(..., ge=0, le=180, description="Tilt angle in degrees (0-180)")


class DetectionResultModel(BaseModel):
    """Single YOLO detection bounding box"""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str = "Tomato_Leaf"


def _guard_robotics():
    """Raise 501 if in rag_only mode (robotics not available)."""
    if _is_rag_only:
        raise HTTPException(
            status_code=501,
            detail="Robotics endpoints are not available in RAG-only deployment."
        )


@app.post("/esp32/connect", tags=["Robotics"])
async def connect_esp32(request: ESP32ConnectRequest):
    """Connect to an ESP32-CAM device over WiFi."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    connected = await esp32.connect(request.ip_address, request.port)
    if connected:
        return {"success": True, "message": f"Connected to ESP32-CAM at {request.ip_address}:{request.port}"}
    raise HTTPException(status_code=503, detail=f"Cannot reach ESP32-CAM at {request.ip_address}:{request.port}")


@app.post("/esp32/disconnect", tags=["Robotics"])
async def disconnect_esp32():
    """Disconnect from ESP32-CAM."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    await esp32.disconnect()
    return {"success": True, "message": "Disconnected from ESP32-CAM"}


@app.get("/esp32/status", tags=["Robotics"])
async def esp32_status():
    """Get ESP32-CAM connection and scanner status."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    scanner: RoboticsScanner = app.state.scanner
    yolo: YOLODetector = app.state.yolo

    result = {
        "connected": esp32.is_connected,
        "ip_address": esp32.base_url,
        "scan_state": scanner.state.value,
        "yolo_loaded": yolo.is_loaded,
        "vision_engine_loaded": app.state.vision_engine is not None,
        "scan_results_count": len(scanner.scan_results),
    }

    if esp32.is_connected:
        try:
            device_status = await esp32.get_status()
            result["device"] = device_status
        except Exception:
            result["device"] = None

    return result


@app.post("/esp32/motor", tags=["Robotics"])
async def control_motor(request: MotorControlRequest):
    """Send motor control command to ESP32-CAM pan-tilt servos."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    if not esp32.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")

    if request.direction == MotorDirection.LEFT:
        ok = await esp32.motor_left(request.step)
    elif request.direction == MotorDirection.RIGHT:
        ok = await esp32.motor_right(request.step)
    elif request.direction == MotorDirection.UP:
        ok = await esp32.motor_up(request.step)
    elif request.direction == MotorDirection.DOWN:
        ok = await esp32.motor_down(request.step)
    elif request.direction == MotorDirection.CENTER:
        ok = await esp32.motor_center()
    else:
        ok = await esp32.motor_stop()

    if ok:
        return {"success": True, "direction": request.direction.value, "step": request.step}
    raise HTTPException(status_code=500, detail="Motor command failed")


@app.post("/esp32/motor/position", tags=["Robotics"])
async def set_servo_position(request: SetPositionRequest):
    """Set absolute servo positions."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    if not esp32.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")

    ok = await esp32.set_position(request.pan, request.tilt)
    if ok:
        return {"success": True, "pan": request.pan, "tilt": request.tilt}
    raise HTTPException(status_code=500, detail="Position command failed")


@app.get("/esp32/motor/position", tags=["Robotics"])
async def get_servo_position():
    """Get current servo positions."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    if not esp32.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")

    return await esp32.get_position()


@app.get("/esp32/stream", tags=["Robotics"])
async def proxy_esp32_stream():
    """Proxy the ESP32-CAM MJPEG video stream."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    if not esp32.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")

    return StreamingResponse(
        esp32.proxy_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/esp32/capture", tags=["Robotics"])
async def capture_esp32_still():
    """Capture a single high-resolution still from ESP32-CAM."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    if not esp32.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")

    try:
        image_bytes = await esp32.capture_still()
        from fastapi.responses import Response
        return Response(content=image_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capture failed: {e}")


@app.post("/esp32/detect", tags=["Robotics"])
async def detect_leaves():
    """Capture frame from ESP32-CAM and run YOLO leaf detection."""
    _guard_robotics()
    esp32: ESP32Client = app.state.esp32_client
    yolo: YOLODetector = app.state.yolo

    if not esp32.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")
    if not yolo.is_loaded:
        raise HTTPException(status_code=503, detail="YOLO model not loaded")

    try:
        image_bytes = await esp32.capture_still()
        detections, inference_ms = yolo.detect_with_timing(image_bytes)
        return {
            "detections": [d.to_dict() for d in detections],
            "count": len(detections),
            "inference_time_ms": round(inference_ms, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")


@app.post("/esp32/classify", tags=["Robotics"])
async def classify_from_esp32(model_type: str = "mobilenet"):
    """Capture still from ESP32-CAM, classify disease, and get RAG advice."""
    _guard_robotics()
    scanner: RoboticsScanner = app.state.scanner

    if not app.state.esp32_client.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")
    if app.state.vision_engine is None:
        raise HTTPException(status_code=503, detail="Disease classification models not loaded")

    try:
        result = await scanner.manual_classify(model_type=model_type)
        return result
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {e}")


@app.post("/esp32/scan/start", tags=["Robotics"])
async def start_auto_scan(request: AutoScanRequest):
    """Start automated ESP32-CAM scanning: motor moves, YOLO detects, classify on detection."""
    _guard_robotics()
    scanner: RoboticsScanner = app.state.scanner

    if not app.state.esp32_client.is_connected:
        raise HTTPException(status_code=503, detail="ESP32-CAM not connected")
    if not app.state.yolo.is_loaded:
        raise HTTPException(status_code=503, detail="YOLO model not loaded")
    if scanner.state == ScanState.SCANNING:
        raise HTTPException(status_code=409, detail="Auto-scan already running")

    try:
        await scanner.start_auto_scan(
            model_type=request.model_type,
            detection_confidence=request.detection_confidence,
            pan_min=request.pan_min,
            pan_max=request.pan_max,
            tilt_min=request.tilt_min,
            tilt_max=request.tilt_max,
            step_size=request.step_size,
        )
        return {"success": True, "message": "Raster scan started", "state": scanner.state.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {e}")


@app.post("/esp32/scan/stop", tags=["Robotics"])
async def stop_auto_scan():
    """Stop automated ESP32-CAM scanning."""
    _guard_robotics()
    scanner: RoboticsScanner = app.state.scanner
    await scanner.stop_scan()
    return {"success": True, "message": "Auto-scan stopped", "state": scanner.state.value}


@app.get("/esp32/scan/results", tags=["Robotics"])
async def get_scan_results():
    """Get all results from the current/last scan session."""
    _guard_robotics()
    scanner: RoboticsScanner = app.state.scanner
    return {
        "results": scanner.scan_results,
        "count": len(scanner.scan_results),
        "state": scanner.state.value,
    }


@app.websocket("/ws/scan")
async def scan_websocket(websocket: WebSocket):
    """
    WebSocket for real-time ESP32-CAM scan events.

    Pushes events: state_change, detection, classification, advice, frame, error.
    Accepts commands: start_scan, stop_scan, motor_left, motor_right, motor_stop.
    """
    if _is_rag_only:
        await websocket.close(code=4001, reason="Robotics not available in RAG-only deployment")
        return
    await websocket.accept()
    scanner: RoboticsScanner = app.state.scanner
    esp32: ESP32Client = app.state.esp32_client

    queue = scanner.subscribe()

    async def send_events():
        """Forward scan events to the WebSocket client."""
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event.to_dict() if hasattr(event, 'to_dict') else event)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    sender_task = asyncio.create_task(send_events())

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command", "")

            if command == "start_scan":
                model_type = data.get("model_type", "mobilenet")
                confidence = data.get("detection_confidence", 0.25)
                try:
                    await scanner.start_auto_scan(model_type=model_type, detection_confidence=confidence)
                    await websocket.send_json({"type": "ack", "command": command, "success": True})
                except Exception as e:
                    await websocket.send_json({"type": "ack", "command": command, "success": False, "error": str(e)})

            elif command == "stop_scan":
                await scanner.stop_scan()
                await websocket.send_json({"type": "ack", "command": command, "success": True})

            elif command == "motor_left":
                step = data.get("step", 5)
                ok = await esp32.motor_left(step) if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            elif command == "motor_right":
                step = data.get("step", 5)
                ok = await esp32.motor_right(step) if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            elif command == "motor_up":
                step = data.get("step", 5)
                ok = await esp32.motor_up(step) if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            elif command == "motor_down":
                step = data.get("step", 5)
                ok = await esp32.motor_down(step) if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            elif command == "motor_center":
                ok = await esp32.motor_center() if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            elif command == "motor_stop":
                ok = await esp32.motor_stop() if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            elif command == "set_position":
                pan = data.get("pan", 90)
                tilt = data.get("tilt", 75)
                ok = await esp32.set_position(pan, tilt) if esp32.is_connected else False
                await websocket.send_json({"type": "ack", "command": command, "success": ok})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown command: {command}"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        sender_task.cancel()
        scanner.unsubscribe(queue)


# =============================================================================
# Development Server
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AgriSense API in development mode...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
