"""
Unified TFLite Conversion Script for AgriSense Research
========================================================
Converts trained Keras models (.keras) to TFLite format in three quantization variants:
  1. float32 (fp32) — full precision baseline
  2. float16 — reduced precision, ~50% smaller, negligible accuracy loss
  3. int8 — full integer quantization, smallest, requires calibration subset

No retraining is required. This is a post-training conversion process.

Usage:
    cd AgriSense/backend
    pip install tensorflow pillow numpy
    python convert_to_tflite.py

Outputs:
    ../agrisense_flutter/assets/models/
        mobilenetv2_fp32.tflite
        mobilenetv2_float16.tflite
        mobilenetv2_int8.tflite
        resnet50_fp32.tflite
        resnet50_float16.tflite
        resnet50_int8.tflite

References:
    - Research Paper Section 4.2: On-device performance metrics (float32, float16, int8 variants)
    - Methodology: Post-training quantization calibration using representative dataset
"""

import os
import sys
import json
import hashlib
import tempfile
import shutil
import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

# Force float32 policy to avoid mixed-precision issues during conversion
tf.keras.mixed_precision.set_global_policy('float32')

# === CONFIGURATION ===

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FINAL_MODELS_DIR = os.path.join(SCRIPT_DIR, 'Final Models')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'agrisense_flutter', 'assets', 'models')
METADATA_PATH = os.path.join(FINAL_MODELS_DIR, 'metadata.json')

# Model definitions
MODELS = {
    'mobilenetv2': {
        'keras_path': os.path.join(FINAL_MODELS_DIR, 'mobilenetv2', 'mobilenetv2_finetuned.keras'),
        'h5_path': os.path.join(FINAL_MODELS_DIR, 'mobilenetv2', 'mobilenetv2_finetuned.h5'),
        'preprocess': 'mobilenetv2',  # [-1, 1] normalization
    },
    'resnet50': {
        'keras_path': os.path.join(FINAL_MODELS_DIR, 'resnet50', 'resnet50_finetuned.keras'),
        'h5_path': os.path.join(FINAL_MODELS_DIR, 'resnet50', 'resnet50_finetuned.h5'),
        'preprocess': 'resnet50',  # Caffe mean subtraction
    },
}

INPUT_SHAPE = (224, 224, 3)
NUM_CALIBRATION_SAMPLES = 200  # For int8 quantization

# Calibration dataset path (test set or training subset)
# Will try multiple locations
CALIBRATION_DIRS = [
    os.path.join(SCRIPT_DIR, '..', '..', 'Downloads', 'demo_test_set (5)'),
    os.path.join(SCRIPT_DIR, 'models', 'calibration_data'),
    os.path.join(SCRIPT_DIR, 'calibration_data'),
]


def md5_checksum(filepath):
    """Compute MD5 checksum of a file for reproducibility."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _build_model_architecture(model_name):
    """Build model architecture from scratch in pure float32.
    
    This avoids mixed-precision graph issues that occur when loading
    models trained with tf.keras.mixed_precision.
    """
    input_layer = tf.keras.layers.Input(shape=INPUT_SHAPE, name='input_layer')
    
    if model_name == 'mobilenetv2':
        base = tf.keras.applications.MobileNetV2(
            weights=None,   # No weights - we'll load them
            include_top=False,
            input_tensor=input_layer,
            input_shape=INPUT_SHAPE,
        )
        x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
        x = tf.keras.layers.Dense(512, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.Dropout(0.4)(x)
        x = tf.keras.layers.Dense(256, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.Dropout(0.4)(x)
        output = tf.keras.layers.Dense(10, activation='softmax', name='output_logits_mobilenetv2')(x)
        
    elif model_name == 'resnet50':
        base = tf.keras.applications.ResNet50(
            weights=None,
            include_top=False,
            input_tensor=input_layer,
            input_shape=INPUT_SHAPE,
        )
        x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
        x = tf.keras.layers.Dense(512, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.Dropout(0.5)(x)
        x = tf.keras.layers.Dense(256, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.Dropout(0.5)(x)
        output = tf.keras.layers.Dense(10, activation='softmax', name='output_logits')(x)
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    model = tf.keras.Model(inputs=input_layer, outputs=output)
    return model


def load_keras_model(model_name, config):
    """Load a Keras model by rebuilding architecture in float32 and loading weights.
    
    This avoids mixed-precision MLIR conversion issues by ensuring the entire
    computation graph is in float32.
    """
    # Step 1: Build fresh architecture in float32
    print(f"  Building {model_name} architecture in float32...")
    model = _build_model_architecture(model_name)
    
    # Step 2: Load weights from .h5 file (preferred) or .keras file
    for key in ['h5_path', 'keras_path']:
        path = config[key]
        if os.path.exists(path):
            print(f"  Loading weights from: {path}")
            try:
                # Load the original model to extract weights
                original = tf.keras.models.load_model(path, compile=False)
                # Transfer weights by name matching
                weights_loaded = 0
                for layer in model.layers:
                    try:
                        orig_layer = original.get_layer(layer.name)
                        orig_weights = orig_layer.get_weights()
                        if orig_weights:
                            # Cast all weights to float32
                            f32_weights = [w.astype(np.float32) if hasattr(w, 'astype') else w 
                                          for w in orig_weights]
                            layer.set_weights(f32_weights)
                            weights_loaded += 1
                    except (ValueError, KeyError):
                        continue
                
                print(f"  Loaded weights for {weights_loaded} layers")
                del original  # Free memory
                break
            except Exception as e:
                print(f"  Warning: Weight loading via name-matching failed: {e}")
                print(f"  Trying direct load_weights...")
                try:
                    model.load_weights(path)
                    print(f"  Direct weight loading succeeded.")
                    break
                except Exception as e2:
                    print(f"  Direct load also failed: {e2}")
                    continue
    else:
        raise FileNotFoundError(
            f"No model file found for {model_name}. Checked:\n"
            f"  - {config['keras_path']}\n"
            f"  - {config['h5_path']}"
        )
    
    print(f"  Input shape:  {model.input_shape}")
    print(f"  Output shape: {model.output_shape}")
    print(f"  Total params: {model.count_params():,}")
    
    # Verify all weights are float32
    for layer in model.layers:
        for w in layer.get_weights():
            assert w.dtype == np.float32, f"Layer {layer.name} has {w.dtype} weights!"
    print(f"  All weights verified as float32.")
    
    return model


def find_calibration_images():
    """Find calibration images from available directories."""
    image_paths = []
    
    for cal_dir in CALIBRATION_DIRS:
        if not os.path.isdir(cal_dir):
            continue
        print(f"  Scanning calibration dir: {cal_dir}")
        for root, dirs, files in os.walk(cal_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    image_paths.append(os.path.join(root, f))
        if image_paths:
            break
    
    if not image_paths:
        print("  WARNING: No calibration images found. Using random data for int8 calibration.")
        return None
    
    # Limit to NUM_CALIBRATION_SAMPLES
    if len(image_paths) > NUM_CALIBRATION_SAMPLES:
        np.random.seed(42)
        indices = np.random.choice(len(image_paths), NUM_CALIBRATION_SAMPLES, replace=False)
        image_paths = [image_paths[i] for i in indices]
    
    print(f"  Found {len(image_paths)} calibration images")
    return image_paths


def preprocess_image(image_path, preprocess_type):
    """Load and preprocess a single image matching model-specific pipeline."""
    img = tf.io.read_file(image_path)
    img = tf.image.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, [224, 224])
    img = tf.cast(img, tf.float32)
    
    if preprocess_type == 'mobilenetv2':
        # Scale to [-1, 1]
        img = (img / 127.5) - 1.0
    elif preprocess_type == 'resnet50':
        # Caffe-style: channel mean subtraction (RGB order)
        img = img - [123.68, 116.779, 103.939]
    
    return img


def make_representative_dataset(image_paths, preprocess_type):
    """Create a generator for int8 calibration representative dataset."""
    def representative_dataset():
        if image_paths is None:
            # Fallback: generate random calibration data
            for _ in range(NUM_CALIBRATION_SAMPLES):
                data = np.random.rand(1, 224, 224, 3).astype(np.float32)
                if preprocess_type == 'mobilenetv2':
                    data = (data * 2.0) - 1.0  # [-1, 1]
                elif preprocess_type == 'resnet50':
                    data = data * 255.0
                    data[..., 0] -= 123.68
                    data[..., 1] -= 116.779
                    data[..., 2] -= 103.939
                yield [data]
        else:
            for path in image_paths:
                try:
                    img = preprocess_image(path, preprocess_type)
                    img = tf.expand_dims(img, 0)
                    yield [img.numpy()]
                except Exception as e:
                    continue
    
    return representative_dataset


def _get_concrete_function(model):
    """Get a concrete function from the model for TFLite conversion.
    
    This avoids the SavedModel serialization issues with Keras 3 + TF 2.20.
    """
    input_shape = model.input_shape
    # Build a concrete function with fixed input shape
    @tf.function(input_signature=[tf.TensorSpec(shape=input_shape, dtype=tf.float32)])
    def serving_fn(x):
        return model(x, training=False)
    
    concrete_fn = serving_fn.get_concrete_function()
    return concrete_fn


def _get_converter(model):
    """Create TFLiteConverter using concrete function (Keras 3 safe)."""
    concrete_fn = _get_concrete_function(model)
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_fn])
    return converter


def convert_fp32(model, output_path, **kwargs):
    """Convert to float32 TFLite (full precision)."""
    converter = _get_converter(model)
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
    tflite_model = converter.convert()
    
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    return len(tflite_model)


def convert_float16(model, output_path, **kwargs):
    """Convert to float16 TFLite (~50% smaller, negligible accuracy loss)."""
    converter = _get_converter(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_model = converter.convert()
    
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    return len(tflite_model)


def convert_int8(model, output_path, representative_dataset_gen, **kwargs):
    """Convert to int8 TFLite (smallest, requires calibration)."""
    converter = _get_converter(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset_gen
    # Allow float32 fallback for ops that don't support int8
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS_INT8,
        tf.lite.OpsSet.TFLITE_BUILTINS,
    ]
    converter.inference_input_type = tf.float32   # Keep input as float32
    converter.inference_output_type = tf.float32  # Keep output as float32
    tflite_model = converter.convert()
    
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    return len(tflite_model)


def validate_tflite(tflite_path, preprocess_type):
    """Validate a TFLite model by running a test inference."""
    interpreter = tf.lite.Interpreter(model_path=tflite_path)
    interpreter.allocate_tensors()
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Create dummy input
    input_shape = input_details[0]['shape']
    if preprocess_type == 'mobilenetv2':
        test_input = np.random.uniform(-1.0, 1.0, input_shape).astype(np.float32)
    else:
        test_input = np.random.uniform(-130.0, 130.0, input_shape).astype(np.float32)
    
    interpreter.set_tensor(input_details[0]['index'], test_input)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    
    return {
        'input_shape': input_shape.tolist(),
        'input_dtype': str(input_details[0]['dtype']),
        'output_shape': output[0].shape,
        'output_dtype': str(output_details[0]['dtype']),
        'output_sum': float(np.sum(output[0])),
        'num_classes': output[0].shape[-1],
        'valid': output[0].shape[-1] == 10,
    }


def convert_single_model(model_name, config, calibration_images):
    """Convert a single model to all three variants."""
    print(f"\n{'='*70}")
    print(f"  CONVERTING: {model_name.upper()}")
    print(f"{'='*70}")
    
    model = load_keras_model(model_name, config)
    results = {}
    
    variants = [
        ('fp32', convert_fp32, {}),
        ('float16', convert_float16, {}),
        ('int8', convert_int8, {
            'representative_dataset_gen': make_representative_dataset(
                calibration_images, config['preprocess']
            ),
        }),
    ]
    
    for variant_name, convert_fn, extra_kwargs in variants:
        output_filename = f"{model_name}_{variant_name}.tflite"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"\n  --- {variant_name.upper()} ---")
        try:
            size_bytes = convert_fn(model, output_path, **extra_kwargs)
            size_mb = size_bytes / (1024 * 1024)
            checksum = md5_checksum(output_path)
            
            # Validate
            validation = validate_tflite(output_path, config['preprocess'])
            
            results[variant_name] = {
                'filename': output_filename,
                'size_bytes': size_bytes,
                'size_mb': round(size_mb, 2),
                'md5': checksum,
                'validation': validation,
                'valid': validation['valid'],
            }
            
            status = "PASS" if validation['valid'] else "FAIL"
            print(f"  [{status}] {output_filename}: {size_mb:.2f} MB | "
                  f"output shape: {validation['output_shape']} | "
                  f"md5: {checksum[:12]}...")
            
        except Exception as e:
            print(f"  [FAIL] {variant_name}: {e}")
            results[variant_name] = {'error': str(e), 'valid': False}
    
    return results


def main():
    print("=" * 70)
    print("  AgriSense TFLite Model Converter")
    print("  Research: Mobile Deployment Trade-off Analysis")
    print("  Generating float32 / float16 / int8 variants")
    print("=" * 70)
    
    # Load metadata
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH) as f:
            metadata = json.load(f)
        print(f"\nMetadata: {json.dumps(metadata, indent=2)}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Find calibration images for int8 quantization
    print("\n--- Calibration Dataset ---")
    calibration_images = find_calibration_images()
    
    # Convert all models
    all_results = {}
    for model_name, config in MODELS.items():
        all_results[model_name] = convert_single_model(
            model_name, config, calibration_images
        )
    
    # Also copy the fp32 versions as the default model files (backward compatible)
    print("\n--- Creating backward-compatible copies ---")
    for model_name in MODELS:
        src = os.path.join(OUTPUT_DIR, f"{model_name}_fp32.tflite")
        dst = os.path.join(OUTPUT_DIR, f"{model_name}.tflite")
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  Copied {model_name}_fp32.tflite -> {model_name}.tflite")
    
    # Generate conversion report
    report = {
        'conversion_timestamp': str(np.datetime64('now')),
        'tensorflow_version': tf.__version__,
        'input_shape': list(INPUT_SHAPE),
        'num_classes': 10,
        'calibration_samples': NUM_CALIBRATION_SAMPLES,
        'models': all_results,
    }
    
    report_path = os.path.join(OUTPUT_DIR, 'conversion_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'='*70}")
    print("  CONVERSION SUMMARY")
    print(f"{'='*70}")
    print(f"  Output directory: {os.path.abspath(OUTPUT_DIR)}")
    print(f"  Report saved to:  {report_path}\n")
    
    print(f"  {'Model':<20} {'Variant':<10} {'Size (MB)':<12} {'Valid':<8}")
    print(f"  {'-'*50}")
    for model_name, variants in all_results.items():
        for variant_name, info in variants.items():
            if 'error' in info:
                print(f"  {model_name:<20} {variant_name:<10} {'ERROR':<12} {'No':<8}")
            else:
                print(f"  {model_name:<20} {variant_name:<10} {info['size_mb']:<12.2f} {'Yes' if info['valid'] else 'No':<8}")
    
    # Print size comparison table for the paper
    print(f"\n  --- Size Comparison (for Results & Discussion) ---")
    print(f"  {'Model':<15} {'FP32 (MB)':<12} {'Float16 (MB)':<14} {'Int8 (MB)':<12} {'FP32>F16 %':<12} {'FP32>Int8 %':<12}")
    print(f"  {'-'*75}")
    for model_name, variants in all_results.items():
        fp32_size = variants.get('fp32', {}).get('size_mb', 0)
        f16_size = variants.get('float16', {}).get('size_mb', 0)
        int8_size = variants.get('int8', {}).get('size_mb', 0)
        f16_reduction = ((fp32_size - f16_size) / fp32_size * 100) if fp32_size > 0 else 0
        int8_reduction = ((fp32_size - int8_size) / fp32_size * 100) if fp32_size > 0 else 0
        print(f"  {model_name:<15} {fp32_size:<12.2f} {f16_size:<14.2f} {int8_size:<12.2f} {f16_reduction:<12.1f} {int8_reduction:<12.1f}")
    
    print(f"\n  Total files generated: {sum(1 for m in all_results.values() for v in m.values() if v.get('valid', False))}")
    print(f"  + 2 backward-compatible copies (mobilenetv2.tflite, resnet50.tflite)")
    print("\n  Done!")


if __name__ == '__main__':
    main()
