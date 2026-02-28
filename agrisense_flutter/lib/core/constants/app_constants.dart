/// Quantization variant for TFLite models
enum ModelVariant { fp32, float16, int8 }

/// Inference delegate type
enum DelegateType { cpu, nnapi }

/// Constants used across the app
class AppConstants {
  // API
  static const String defaultApiUrl =
      'https://agrisense-api-jytid2.azurewebsites.net';
  static const String apiUrlIos = 'http://localhost:8000';
  static const String deployedApiUrl =
      'https://agrisense-api-jytid2.azurewebsites.net';
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: defaultApiUrl,
  );

  // Feature flags
  static const bool enableRobotics = bool.fromEnvironment(
    'ENABLE_ROBOTICS',
    defaultValue: true,
  );

  // ML Model Configuration
  static const int inputSize = 224;
  static const int numClasses = 10;
  static const double confidenceThreshold = 0.5;

  // Benchmark defaults (paper requires N=200)
  static const int defaultBenchmarkRuns = 200;
  static const int defaultWarmupRuns = 5;

  // Test set evaluation
  static const String testManifestFilename = 'test_manifest.json';
  static const String testSetDirectoryName = 'AgriSense/test_set';

  // Model files — FP32 (default / backward-compatible)
  static const String mobilenetModelPath = 'assets/models/mobilenetv2.tflite';
  static const String resnetModelPath = 'assets/models/resnet50.tflite';
  static const String labelsPath = 'assets/labels/class_names.json';

  // Model files — All quantization variants
  static const Map<String, Map<ModelVariant, String>> modelPaths = {
    'mobilenet': {
      ModelVariant.fp32: 'assets/models/mobilenetv2_fp32.tflite',
      ModelVariant.float16: 'assets/models/mobilenetv2_float16.tflite',
      ModelVariant.int8: 'assets/models/mobilenetv2_int8.tflite',
    },
    'resnet': {
      ModelVariant.fp32: 'assets/models/resnet50_fp32.tflite',
      ModelVariant.float16: 'assets/models/resnet50_float16.tflite',
      ModelVariant.int8: 'assets/models/resnet50_int8.tflite',
    },
  };

  /// Get variant display name
  static String variantDisplayName(ModelVariant variant) {
    switch (variant) {
      case ModelVariant.fp32:
        return 'FP32';
      case ModelVariant.float16:
        return 'Float16';
      case ModelVariant.int8:
        return 'Int8';
    }
  }

  /// Get delegate display name
  static String delegateDisplayName(DelegateType delegate) {
    switch (delegate) {
      case DelegateType.cpu:
        return 'CPU';
      case DelegateType.nnapi:
        return 'NNAPI';
    }
  }

  // Disease class names (same order as training)
  static const List<String> classNames = [
    'Tomato___Bacterial_spot',
    'Tomato___Early_blight',
    'Tomato___Late_blight',
    'Tomato___Leaf_Mold',
    'Tomato___Septoria_leaf_spot',
    'Tomato___Spider_mites Two-spotted_spider_mite',
    'Tomato___Target_Spot',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
    'Tomato___Tomato_mosaic_virus',
    'Tomato___healthy',
  ];

  // Display-friendly names
  static const Map<String, String> displayNames = {
    'Tomato___Bacterial_spot': 'Bacterial Spot',
    'Tomato___Early_blight': 'Early Blight',
    'Tomato___Late_blight': 'Late Blight',
    'Tomato___Leaf_Mold': 'Leaf Mold',
    'Tomato___Septoria_leaf_spot': 'Septoria Leaf Spot',
    'Tomato___Spider_mites Two-spotted_spider_mite': 'Spider Mites (Two-spotted)',
    'Tomato___Target_Spot': 'Target Spot',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': 'Yellow Leaf Curl Virus',
    'Tomato___Tomato_mosaic_virus': 'Mosaic Virus',
    'Tomato___healthy': 'Healthy',
  };

  // Disease descriptions
  static const Map<String, String> diseaseDescriptions = {
    'Bacterial Spot':
        'Bacterial leaf spot is caused by Xanthomonas species. Small, dark, water-soaked spots appear on leaves.',
    'Early Blight':
        'Caused by Alternaria solani. Dark concentric rings (target spots) on older leaves first.',
    'Late Blight':
        'Caused by Phytophthora infestans. Large, irregular water-soaked lesions, can devastate crops rapidly.',
    'Leaf Mold':
        'Caused by Passalora fulva. Yellow spots on upper leaf surface with olive-green mold underneath.',
    'Septoria Leaf Spot':
        'Caused by Septoria lycopersici. Small circular spots with dark borders and gray centers.',
    'Spider Mites (Two-spotted)':
        'Tiny arachnids (Tetranychus urticae) that cause stippling and yellowing of leaves.',
    'Target Spot':
        'Caused by Corynespora cassiicola. Concentric ringed spots resembling a target.',
    'Yellow Leaf Curl Virus':
        'Transmitted by whiteflies. Severe leaf curling, yellowing, and stunted plant growth.',
    'Mosaic Virus':
        'Causes mottled light/dark green patterns on leaves with possible leaf distortion.',
    'Healthy':
        'No disease detected. The plant appears to be in good health.',
  };

  // Disease severity mapping
  static const Map<String, String> diseaseSeverity = {
    'Bacterial Spot': 'Medium',
    'Early Blight': 'Medium',
    'Late Blight': 'High',
    'Leaf Mold': 'Low',
    'Septoria Leaf Spot': 'Medium',
    'Spider Mites (Two-spotted)': 'Low',
    'Target Spot': 'Medium',
    'Yellow Leaf Curl Virus': 'High',
    'Mosaic Virus': 'High',
    'Healthy': 'None',
  };

  // Weather
  static const double defaultLat = 14.5995;
  static const double defaultLon = 120.9842;
  static const String defaultLocation = 'Manila, Philippines';

  // ESP32-CAM Robotics
  static const String defaultEsp32Ip = '192.168.1.100';
  static const int defaultEsp32Port = 80;
}
