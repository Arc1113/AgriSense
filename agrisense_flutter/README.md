# AgriSense Flutter 🌱📱

AI-Powered Tomato Disease Detection — **Flutter Mobile App** with **on-device ML inference**.

This is the Flutter version of the AgriSense project. It embeds both **MobileNetV2** and **ResNet50** TensorFlow Lite models directly into the app, enabling fully offline disease detection and direct on-device performance comparison.

---

## 🎯 Key Features

### On-Device ML Inference
- **MobileNetV2** — Lightweight, optimized for mobile
- **ResNet50** — Heavier, potentially more accurate
- Both models run **entirely on-device** using TensorFlow Lite — no internet needed for detection

### Model Comparison
- **Side-by-side comparison** of both models on the same image
- See which model is faster, more confident, and whether they agree
- **Benchmark mode** — run configurable multi-pass benchmarks with statistical analysis (mean, median, P95, std dev)

### Full Feature Set
- 📸 Camera capture & gallery upload
- 🔍 10 tomato disease classes + healthy detection
- 📊 Detailed result cards with confidence bars
- 💊 Treatment advice (online via backend RAG, offline fallback)
- 🌤️ Weather integration (Open-Meteo API)
- 📜 Scan history with local storage
- 🎨 Modern dark UI matching the web app design

---

## 📁 Project Structure

```
agrisense_flutter/
├── pubspec.yaml                  # Dependencies
├── assets/
│   ├── models/                   # TFLite model files (see setup)
│   │   ├── mobilenetv2.tflite
│   │   └── resnet50.tflite
│   └── labels/
│       └── class_names.json      # 10 disease class labels
├── scripts/
│   └── convert_models.py         # Keras .h5 → TFLite converter
├── lib/
│   ├── main.dart                 # App entry point
│   ├── core/
│   │   ├── constants/            # App-wide constants, class names
│   │   ├── models/               # Data models (PredictionResult, etc.)
│   │   ├── providers/            # Provider setup
│   │   └── theme/                # Dark theme, colors
│   ├── services/
│   │   ├── ml/
│   │   │   ├── disease_classifier.dart     # TFLite inference engine
│   │   │   └── model_benchmark_service.dart # Multi-pass benchmarking
│   │   ├── api/
│   │   │   └── api_service.dart            # Backend API client
│   │   ├── weather/
│   │   │   └── weather_service.dart        # Open-Meteo weather
│   │   └── storage/
│   │       └── scan_history_service.dart   # Local scan history
│   └── features/
│       ├── splash/               # Animated splash screen
│       ├── home/                 # Camera viewfinder + controls
│       ├── detection/            # Analysis loading screen
│       ├── result/               # Disease result display
│       ├── comparison/           # MobileNet vs ResNet comparison
│       ├── benchmark/            # Multi-run performance benchmark
│       └── history/              # Saved scan history
```

---

## 🚀 Setup

### Prerequisites
- Flutter SDK 3.2+
- Android Studio / Xcode
- Python 3.8+ (for model conversion)

### 1. Convert Models to TFLite

```bash
cd agrisense_flutter/scripts
pip install tensorflow
python convert_models.py
```

This converts the Keras `.h5` models from `backend/models/` to `.tflite` format and places them in `assets/models/`.

### 2. Install Flutter Dependencies

```bash
cd agrisense_flutter
flutter pub get
```

### 3. Run on Device

```bash
# Android
flutter run

# iOS (macOS only)
flutter run -d ios
```

### 4. (Optional) Connect to Backend

For RAG-powered treatment advice, run the backend server:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The app works **fully offline** for disease detection but connects to the backend for AI treatment advice when available.

---

## 📱 Model Comparison: MobileNet vs ResNet

The core purpose of this Flutter app is to test whether **ResNet50 can run successfully on mobile devices** compared to the lighter **MobileNetV2**.

### Using the Comparison Feature
1. Open the app → tap **Compare** button
2. Take or select a photo of a tomato leaf
3. Both models run on the same image
4. View side-by-side results: disease, confidence, speed

### Using the Benchmark Feature
1. Tap **Benchmark** in the bottom menu
2. Select a test image
3. Configure number of runs (3-30)
4. View detailed statistics: mean, median, P95, min, max, std deviation

### Expected Results
| Metric        | MobileNetV2    | ResNet50       |
|---------------|----------------|----------------|
| Model Size    | ~9 MB          | ~90 MB         |
| Inference     | ~30-80 ms      | ~100-500 ms    |
| Parameters    | ~2.3M          | ~23.5M         |
| Mobile Rating | ⭐ Excellent   | ⚡ Varies      |

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐
│   Flutter    │────▶│  DiseaseClassifier│
│   Camera /   │     │  (TFLite Runtime) │
│   Gallery    │     ├──────────────────┤
│              │     │  MobileNetV2.tflite│
│              │     │  ResNet50.tflite  │
└─────────────┘     └──────────────────┘
       │                      │
       ▼                      ▼
┌─────────────┐     ┌──────────────────┐
│  Result UI  │     │ Benchmark Service│
│  Comparison │     │ (Multi-run stats)│
│  History    │     └──────────────────┘
└─────────────┘
       │
       ▼ (optional, online)
┌─────────────────────────┐
│  Backend API (FastAPI)  │
│  RAG Treatment Advice   │
│  Weather Integration    │
└─────────────────────────┘
```

---

## 📄 License

Same as the main AgriSense project.
