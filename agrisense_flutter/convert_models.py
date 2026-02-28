"""
Convert Keras/H5 models to TFLite format for Flutter deployment.

Usage:
    python convert_models.py

This will convert both MobileNetV2 and ResNet50 models from the backend
and place the .tflite files into assets/models/ for the Flutter app.
"""

import os
import sys

def convert_from_saved_model(saved_model_dir, tflite_output_path, model_name):
    """Convert a SavedModel to TFLite format (fastest & most reliable)."""
    import tensorflow as tf

    print(f"\n{'='*50}")
    print(f"Converting {model_name} from SavedModel...")
    print(f"  Source: {saved_model_dir}")
    print(f"  Output: {tflite_output_path}")

    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    
    # Optional: float16 quantization to cut size ~50%
    # converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # converter.target_spec.supported_types = [tf.float16]

    print(f"  Converting to TFLite...")
    tflite_model = converter.convert()

    os.makedirs(os.path.dirname(tflite_output_path), exist_ok=True)
    with open(tflite_output_path, 'wb') as f:
        f.write(tflite_model)

    size_mb = len(tflite_model) / (1024 * 1024)
    print(f"  ✅ Saved! Size: {size_mb:.1f} MB")
    return True


def convert_from_keras(keras_path, tflite_output_path, model_name):
    """Convert a Keras model to TFLite format (fallback)."""
    import tensorflow as tf

    print(f"\n{'='*50}")
    print(f"Converting {model_name} from Keras...")
    print(f"  Source: {keras_path}")
    print(f"  Output: {tflite_output_path}")

    print(f"  Loading model...")
    model = tf.keras.models.load_model(keras_path)
    print(f"  Input shape: {model.input_shape}")
    print(f"  Output shape: {model.output_shape}")

    print(f"  Converting to TFLite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    os.makedirs(os.path.dirname(tflite_output_path), exist_ok=True)
    with open(tflite_output_path, 'wb') as f:
        f.write(tflite_model)

    size_mb = len(tflite_model) / (1024 * 1024)
    print(f"  ✅ Saved! Size: {size_mb:.1f} MB")
    return True


def main():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_models = os.path.join(script_dir, '..', 'backend', 'models')
    output_dir = os.path.join(script_dir, 'assets', 'models')

    models = [
        {
            'name': 'MobileNetV2',
            'saved_model': os.path.join(backend_models, 'mobilenetv2', 'mobilenetv2_savedmodel'),
            'keras_path': os.path.join(backend_models, 'mobilenetv2', 'mobilenetv2_finetuned.keras'),
            'h5_path': os.path.join(backend_models, 'mobilenetv2', 'mobilenetv2_finetuned.h5'),
            'output': os.path.join(output_dir, 'mobilenetv2.tflite'),
        },
        {
            'name': 'ResNet50',
            'saved_model': os.path.join(backend_models, 'resnet50', 'resnet50_savedmodel'),
            'keras_path': os.path.join(backend_models, 'resnet50', 'resnet50_finetuned.keras'),
            'h5_path': os.path.join(backend_models, 'resnet50', 'resnet50_finetuned.h5'),
            'output': os.path.join(output_dir, 'resnet50.tflite'),
        },
    ]

    success_count = 0
    for m in models:
        try:
            # Prefer SavedModel (fastest), then .keras, then .h5
            if os.path.isdir(m['saved_model']) and os.path.exists(os.path.join(m['saved_model'], 'saved_model.pb')):
                convert_from_saved_model(m['saved_model'], m['output'], m['name'])
            elif os.path.exists(m['keras_path']):
                convert_from_keras(m['keras_path'], m['output'], m['name'])
            elif os.path.exists(m['h5_path']):
                convert_from_keras(m['h5_path'], m['output'], m['name'])
            else:
                print(f"\n❌ {m['name']}: No model file found!")
                continue
            success_count += 1
        except Exception as e:
            print(f"\n❌ {m['name']} conversion failed: {e}")

    print(f"\n{'='*50}")
    print(f"Done! {success_count}/{len(models)} models converted.")

    if success_count > 0:
        print(f"\nTFLite models saved to: {output_dir}")
        print("You can now rebuild the Flutter app: flutter build apk --debug")
    else:
        print("\nNo models were converted. Make sure TensorFlow is installed:")
        print("  pip install tensorflow")


if __name__ == '__main__':
    main()
