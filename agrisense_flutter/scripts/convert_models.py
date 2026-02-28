"""
Model Converter Script for AgriSense Flutter
Converts Keras .h5 models to TFLite format for on-device mobile inference.

Usage:
    cd agrisense_flutter/scripts
    pip install tensorflow
    python convert_models.py
"""

import os
import sys
import tensorflow as tf

# Paths relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_MODELS = os.path.join(PROJECT_ROOT, '..', 'backend', 'models')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'assets', 'models')

MODELS = {
    'mobilenetv2': {
        'input': os.path.join(BACKEND_MODELS, 'mobilenetv2', 'mobilenetv2_finetuned.h5'),
        'output': os.path.join(OUTPUT_DIR, 'mobilenetv2.tflite'),
    },
    'resnet50': {
        'input': os.path.join(BACKEND_MODELS, 'resnet50', 'resnet50_finetuned.h5'),
        'output': os.path.join(OUTPUT_DIR, 'resnet50.tflite'),
    }
}


def convert_model(name: str, input_path: str, output_path: str, quantize: bool = False):
    """Convert a Keras .h5 model to TFLite format."""
    print(f"\n{'='*60}")
    print(f"Converting {name}")
    print(f"{'='*60}")

    if not os.path.exists(input_path):
        print(f"  ❌ Input model not found: {input_path}")
        return False

    print(f"  📂 Loading model from: {input_path}")
    model = tf.keras.models.load_model(input_path, compile=False)

    print(f"  📐 Input shape:  {model.input_shape}")
    print(f"  📐 Output shape: {model.output_shape}")
    print(f"  📊 Parameters:   {model.count_params():,}")

    # Convert to TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    if quantize:
        print("  ⚡ Applying dynamic range quantization...")
        converter.optimizations = [tf.lite.Optimize.DEFAULT]

    print("  🔄 Converting to TFLite...")
    tflite_model = converter.convert()

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  ✅ Saved to: {output_path}")
    print(f"  📦 Size: {size_mb:.2f} MB")

    return True


def main():
    print("🌱 AgriSense Model Converter")
    print("Converting Keras .h5 models to TFLite for mobile inference\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = {}
    for name, paths in MODELS.items():
        # Convert without quantization (full precision)
        success = convert_model(name, paths['input'], paths['output'], quantize=False)
        results[name] = success

        # Also create a quantized version for comparison
        quantized_output = paths['output'].replace('.tflite', '_quantized.tflite')
        convert_model(f"{name} (quantized)", paths['input'], quantized_output, quantize=True)

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {name}: {status}")

    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    print("Copy these .tflite files to agrisense_flutter/assets/models/")


if __name__ == '__main__':
    main()
