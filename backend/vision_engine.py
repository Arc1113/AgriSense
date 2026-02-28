"""
AgriSense Vision Engine - Production Ready
TensorFlow/Keras model loader and disease prediction

Features:
- Dual model support (MobileNetV2 / ResNet50)
- Robust image preprocessing pipeline
- Comprehensive logging and error handling
- Memory-efficient inference
- Model status monitoring

Configuration (from training metadata):
- Input Shape: 224 x 224 x 3
- Preprocessing: tf.keras.applications.[model].preprocess_input
- Classes: 10 tomato disease categories
"""

import os
import json
import logging
import time
from typing import Tuple, Optional, Dict, Any, List

import numpy as np
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VisionEngine")

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input as mobilenet_preprocess
from tensorflow.keras.applications.resnet50 import preprocess_input as resnet_preprocess

# ============================================================================
# CONFIGURATION - Extracted from training notebook/metadata
# ============================================================================

# Ordered list of class names (index 0-9)
CLASS_NAMES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy"
]

# Human-readable display names
DISPLAY_NAMES = {
    "Tomato___Bacterial_spot": "Bacterial Spot",
    "Tomato___Early_blight": "Early Blight",
    "Tomato___Late_blight": "Late Blight",
    "Tomato___Leaf_Mold": "Leaf Mold",
    "Tomato___Septoria_leaf_spot": "Septoria Leaf Spot",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Spider Mites (Two-spotted)",
    "Tomato___Target_Spot": "Target Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus": "Mosaic Virus",
    "Tomato___healthy": "Healthy"
}

# Input shape from training
IMG_SIZE = (224, 224)

# Model paths relative to this file's directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATHS = {
    "mobilenet": os.path.join(BACKEND_DIR, "models", "mobilenetv2", "mobilenetv2_finetuned.h5"),
    "resnet": os.path.join(BACKEND_DIR, "models", "resnet50", "resnet50_finetuned.h5")
}

# Preprocessing functions per model type
PREPROCESS_FN = {
    "mobilenet": mobilenet_preprocess,
    "resnet": resnet_preprocess
}

# ============================================================================
# MODEL STORAGE
# ============================================================================

_models: Dict[str, Optional[tf.keras.Model]] = {
    "mobilenet": None,
    "resnet": None
}

_load_status: Dict[str, bool] = {
    "mobilenet": False,
    "resnet": False
}


# ============================================================================
# MODEL LOADER
# ============================================================================

def load_models() -> Dict[str, bool]:
    """
    Load TensorFlow/Keras models from disk.
    Uses try/except to handle missing files gracefully.
    
    Returns:
        Dictionary indicating which models were successfully loaded
    """
    global _models, _load_status
    
    for model_type, model_path in MODEL_PATHS.items():
        try:
            if os.path.exists(model_path):
                logger.info(f"🔄 Loading {model_type} model from: {model_path}")
                start_time = time.time()
                
                _models[model_type] = tf.keras.models.load_model(model_path, compile=False)
                _load_status[model_type] = True
                
                load_time = time.time() - start_time
                logger.info(f"✅ {model_type} model loaded in {load_time:.2f}s")
                logger.info(f"   Input shape: {_models[model_type].input_shape}")
                logger.info(f"   Output shape: {_models[model_type].output_shape}")
            else:
                _load_status[model_type] = False
                logger.warning(f"⚠️  Model file not found: {model_path}")
        except Exception as e:
            _load_status[model_type] = False
            logger.error(f"❌ Failed to load {model_type} model: {str(e)}")
    
    return _load_status.copy()


# ============================================================================
# IMAGE PREPROCESSING
# ============================================================================

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def validate_image_bytes(image_bytes: bytes) -> bool:
    """
    Validate that bytes represent a valid image.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        True if valid image, False otherwise
    """
    if not image_bytes or len(image_bytes) < 100:
        return False
    
    # Check magic bytes for common formats
    magic_bytes = {
        b'\xff\xd8\xff': 'JPEG',
        b'\x89PNG': 'PNG',
        b'RIFF': 'WebP',
        b'BM': 'BMP'
    }
    
    for magic, fmt in magic_bytes.items():
        if image_bytes[:len(magic)] == magic:
            return True
    
    return False


def preprocess_image(image_bytes: bytes, model_type: str = "mobilenet") -> np.ndarray:
    """
    Preprocess image bytes for model inference.
    Replicates the exact preprocessing from the training notebook.
    
    Steps:
    1. Decode bytes to numpy array (OpenCV)
    2. Convert BGR to RGB
    3. Resize to 224x224
    4. Apply model-specific preprocessing (tf.keras.applications.[model].preprocess_input)
    5. Add batch dimension
    
    Args:
        image_bytes: Raw image bytes (JPEG/PNG)
        model_type: 'mobilenet' or 'resnet' (determines preprocessing function)
    
    Returns:
        Preprocessed numpy array ready for model inference
        Shape: (1, 224, 224, 3)
        
    Raises:
        ValueError: If image cannot be decoded or processed
    """
    # Decode image bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        logger.error("Failed to decode image bytes")
        raise ValueError("Failed to decode image. Please provide a valid JPEG, PNG, or WebP file.")
    
    # Convert BGR (OpenCV default) to RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Resize to target size (224x224)
    img = cv2.resize(img, IMG_SIZE, interpolation=cv2.INTER_AREA)
    
    # Convert to float32
    img = img.astype(np.float32)
    
    # Apply model-specific preprocessing
    # MobileNetV2: scales pixels to [-1, 1]
    # ResNet50: zero-centers each color channel with respect to ImageNet
    preprocess_fn = PREPROCESS_FN.get(model_type, mobilenet_preprocess)
    img = preprocess_fn(img)
    
    # Add batch dimension: (224, 224, 3) -> (1, 224, 224, 3)
    img = np.expand_dims(img, axis=0)
    
    return img


# ============================================================================
# PREDICTION
# ============================================================================

def predict_disease(image_bytes: bytes, model_type: str = "mobilenet") -> Dict[str, Any]:
    """
    Predict tomato disease from image bytes.
    
    Args:
        image_bytes: Raw image bytes (JPEG/PNG)
        model_type: 'mobilenet' or 'resnet'
    
    Returns:
        Dictionary with:
        - 'class': Human-readable disease name
        - 'confidence': Float 0-1
        - 'raw_class': Original class name
        - 'all_predictions': Dict of all class probabilities
        - 'inference_time_ms': Inference time in milliseconds
    """
    start_time = time.time()
    
    # Normalize model_type input
    model_type = model_type.lower().strip()
    if model_type == "mobile":
        model_type = "mobilenet"
    
    # Validate model type
    if model_type not in _models:
        raise ValueError(f"Invalid model type: '{model_type}'. Use 'mobilenet' or 'resnet'.")
    
    # Check if model is loaded
    model = _models.get(model_type)
    if model is None:
        logger.warning(f"⚠️  Model '{model_type}' not loaded, returning fallback response")
        return {
            "class": "Model Not Loaded",
            "confidence": 0.0,
            "raw_class": None,
            "all_predictions": None,
            "inference_time_ms": 0
        }
    
    # Preprocess image with the correct preprocessing function
    processed_img = preprocess_image(image_bytes, model_type=model_type)
    
    # Run inference
    inference_start = time.time()
    predictions = model.predict(processed_img, verbose=0)
    inference_time = (time.time() - inference_start) * 1000
    
    # Get predicted class index and confidence
    predicted_idx = int(np.argmax(predictions[0]))
    confidence = float(predictions[0][predicted_idx])
    
    # Map index to class name
    raw_class_name = CLASS_NAMES[predicted_idx]
    display_name = DISPLAY_NAMES.get(raw_class_name, raw_class_name)
    
    # Log prediction
    logger.info(f"🎯 Prediction: {display_name} ({confidence:.2%}) in {inference_time:.1f}ms")
    
    # Build sorted predictions (highest first)
    all_preds = {
        DISPLAY_NAMES.get(CLASS_NAMES[i], CLASS_NAMES[i]): round(float(predictions[0][i]), 4)
        for i in range(len(CLASS_NAMES))
    }
    sorted_preds = dict(sorted(all_preds.items(), key=lambda x: x[1], reverse=True))
    
    # Build response
    total_time = (time.time() - start_time) * 1000
    result = {
        "class": display_name,
        "confidence": round(confidence, 4),
        "raw_class": raw_class_name,
        "all_predictions": sorted_preds,
        "inference_time_ms": round(inference_time, 2),
        "total_time_ms": round(total_time, 2)
    }
    
    return result


# ============================================================================
# STATUS & UTILITY
# ============================================================================

def get_model_status() -> Dict[str, Any]:
    """
    Get the current status of loaded models.
    
    Returns:
        Dictionary with model loading status and metadata
    """
    status = {}
    for model_type, model in _models.items():
        if model is not None:
            status[model_type] = {
                "loaded": True,
                "path": MODEL_PATHS[model_type],
                "input_shape": str(model.input_shape),
                "output_classes": len(CLASS_NAMES)
            }
        else:
            status[model_type] = {
                "loaded": False,
                "path": MODEL_PATHS[model_type],
                "exists": os.path.exists(MODEL_PATHS[model_type])
            }
    return status


def get_class_names() -> list:
    """Return the list of class names in order"""
    return [DISPLAY_NAMES.get(c, c) for c in CLASS_NAMES]


# ============================================================================
# TEST / CLI
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AgriSense Vision Engine - Self Test")
    print("=" * 60)
    
    # Load models
    print("\n📦 Loading models...")
    status = load_models()
    print(f"\nLoad status: {status}")
    
    # Show model status
    print("\n📊 Model Status:")
    for name, info in get_model_status().items():
        print(f"  {name}: {info}")
    
    # Show classes
    print(f"\n🏷️  Classes ({len(CLASS_NAMES)}):")
    for i, name in enumerate(get_class_names()):
        print(f"  {i}: {name}")
