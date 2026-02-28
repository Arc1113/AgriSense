# AgriSense Flutter

## On-Device ML Model Setup

### Converting .h5 Models to TFLite

The Flutter app uses TensorFlow Lite for on-device inference. You need to convert
the existing Keras `.h5` models to `.tflite` format.

Run the `convert_models.py` script from the `agrisense_flutter/scripts/` folder:

```bash
cd agrisense_flutter/scripts
pip install tensorflow
python convert_models.py
```

This will generate:
- `assets/models/mobilenetv2.tflite`
- `assets/models/resnet50.tflite`

### Model Files Placement
Place the converted `.tflite` files in:
```
agrisense_flutter/assets/models/
├── mobilenetv2.tflite
└── resnet50.tflite
```

Both models expect 224×224×3 RGB input images.
