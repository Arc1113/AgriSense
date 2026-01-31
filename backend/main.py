"""
AgriSense Backend - FastAPI Server
Tomato Disease Detection API Gateway
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AgriSense API",
    description="Tomato Disease Detection and Treatment Advice API",
    version="1.0.0"
)

# Configure CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/predict")
async def predict_disease(file: UploadFile = File(...)):
    """
    Predict tomato disease from uploaded image.
    
    Args:
        file: Image file (JPEG, PNG)
    
    Returns:
        Disease prediction with confidence and treatment advice
    """
    # TODO: Replace with actual model inference
    # TODO: Integrate CrewAI for treatment advice generation
    
    # Mock response for Phase 1
    return {
        "disease": "Mock Blight",
        "confidence": 0.99,
        "advice": {
            "severity": "Low",
            "organic_treatment": "Mock Organic",
            "chemical_treatment": "Mock Chemical"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
