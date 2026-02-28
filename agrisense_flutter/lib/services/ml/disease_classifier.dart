import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:logger/logger.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

import '../../core/constants/app_constants.dart';
import '../../core/models/prediction_result.dart';

/// Enum representing available ML model types
enum ModelType { mobilenet, resnet }

/// Unique key for a loaded model configuration
class _ModelKey {
  final ModelType type;
  final String variant;
  final String delegate;
  _ModelKey(this.type, this.variant, this.delegate);

  @override
  bool operator ==(Object other) =>
      other is _ModelKey &&
      type == other.type &&
      variant == other.variant &&
      delegate == other.delegate;

  @override
  int get hashCode => Object.hash(type, variant, delegate);

  @override
  String toString() => '${type.name}/$variant/$delegate';
}

/// On-device disease classifier using TensorFlow Lite.
/// Loads both MobileNetV2 and ResNet50 models for comparison.
/// 
/// Enhanced to support study objective 2.2.3: measuring computational efficiency
/// across float32/float16/int8 variants with CPU/NNAPI delegates.
class DiseaseClassifier extends ChangeNotifier {
  final Logger _logger = Logger();

  // TFLite interpreters – keyed by model+variant+delegate
  final Map<_ModelKey, Interpreter> _interpreters = {};

  // Legacy quick-access references (default fp32/cpu)
  Interpreter? _mobilenetInterpreter;
  Interpreter? _resnetInterpreter;

  // Loading state
  bool _isInitialized = false;
  bool _isLoading = false;
  String? _error;

  // Model load status
  final Map<ModelType, bool> _modelLoaded = {
    ModelType.mobilenet: false,
    ModelType.resnet: false,
  };

  // Model sizes (bytes) – keyed by _ModelKey.toString()
  final Map<String, int> _modelSizes = {};

  // Model load times (milliseconds) – keyed by _ModelKey.toString()
  final Map<String, double> _modelLoadTimes = {};

  // Currently active variant & delegate per model type
  final Map<ModelType, String> _activeVariant = {
    ModelType.mobilenet: 'fp32',
    ModelType.resnet: 'fp32',
  };
  final Map<ModelType, String> _activeDelegate = {
    ModelType.mobilenet: 'cpu',
    ModelType.resnet: 'cpu',
  };

  // Last preprocessing time (milliseconds)
  double _lastPreprocessingTimeMs = 0.0;

  bool get isInitialized => _isInitialized;
  bool get isLoading => _isLoading;
  String? get error => _error;
  Map<ModelType, bool> get modelLoaded => Map.unmodifiable(_modelLoaded);
  
  /// Get model load time in milliseconds (for study objective 2.2.3)
  double getModelLoadTimeMs(ModelType type, [String? variant, String? delegate]) {
    final key = _ModelKey(type, variant ?? _activeVariant[type]!, delegate ?? _activeDelegate[type]!);
    return _modelLoadTimes[key.toString()] ?? 0.0;
  }
  
  /// Get model size in bytes
  int getModelSizeBytes(ModelType type, [String? variant, String? delegate]) {
    final key = _ModelKey(type, variant ?? _activeVariant[type]!, delegate ?? _activeDelegate[type]!);
    return _modelSizes[key.toString()] ?? 0;
  }
  
  /// Get last preprocessing time
  double get lastPreprocessingTimeMs => _lastPreprocessingTimeMs;

  /// Active variant for a model type
  String getActiveVariant(ModelType type) => _activeVariant[type] ?? 'fp32';
  
  /// Active delegate for a model type
  String getActiveDelegate(ModelType type) => _activeDelegate[type] ?? 'cpu';

  String getModelSizeMB(ModelType type, [String? variant, String? delegate]) {
    final bytes = getModelSizeBytes(type, variant, delegate);
    if (bytes == 0) return 'N/A';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  /// Get formatted model load time string
  String getModelLoadTimeFormatted(ModelType type, [String? variant, String? delegate]) {
    final ms = getModelLoadTimeMs(type, variant, delegate);
    if (ms == 0.0) return 'N/A';
    return '${ms.toStringAsFixed(0)} ms';
  }

  /// Initialize both ML models with default fp32/CPU configuration
  Future<void> initialize() async {
    if (_isInitialized || _isLoading) return;

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _loadModel(ModelType.mobilenet);
      await _loadModel(ModelType.resnet);

      _isInitialized = _modelLoaded.values.any((loaded) => loaded);

      if (!_isInitialized) {
        _error = 'No models could be loaded. Please check assets/models/ folder.';
      }

      _logger.i('Models initialized: $_modelLoaded');
    } catch (e) {
      _error = 'Failed to initialize models: $e';
      _logger.e('Model initialization error', error: e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load a specific model variant with the given delegate.
  /// Returns the load time in ms. Used by benchmark service for study.
  Future<double> loadModelVariant(
    ModelType type, {
    String variant = 'fp32',
    String delegate = 'cpu',
  }) async {
    // Unload any existing interpreter for this model type
    _unloadModel(type);

    final loadTime = await _loadModel(type, variant: variant, delegate: delegate);
    _activeVariant[type] = variant;
    _activeDelegate[type] = delegate;
    notifyListeners();
    return loadTime;
  }

  /// Unload a model to free memory
  void _unloadModel(ModelType type) {
    // Close all interpreters for this model type
    final keysToRemove = _interpreters.keys
        .where((k) => k.type == type)
        .toList();
    for (final key in keysToRemove) {
      _interpreters[key]?.close();
      _interpreters.remove(key);
    }
    
    // Clear legacy references
    if (type == ModelType.mobilenet) {
      _mobilenetInterpreter = null;
    } else {
      _resnetInterpreter = null;
    }
    _modelLoaded[type] = false;
  }

  /// Load a single TFLite model and track load time for study.
  /// Returns load time in milliseconds.
  Future<double> _loadModel(
    ModelType type, {
    String variant = 'fp32',
    String delegate = 'cpu',
  }) async {
    // Resolve asset path from the model paths map
    final String assetPath;
    final modelKey = type == ModelType.mobilenet ? 'mobilenet' : 'resnet';
    final modelVariant = ModelVariant.values.firstWhere(
      (v) => v.name == variant,
      orElse: () => ModelVariant.fp32,
    );
    assetPath = AppConstants.modelPaths[modelKey]?[modelVariant] ??
        (type == ModelType.mobilenet
            ? AppConstants.mobilenetModelPath
            : AppConstants.resnetModelPath);

    final key = _ModelKey(type, variant, delegate);

    try {
      _logger.i('Loading ${key} from $assetPath...');
      final stopwatch = Stopwatch()..start();

      // Build interpreter options
      final options = InterpreterOptions()..threads = 4;
      
      // Add NNAPI delegate if requested (Android only)
      if (delegate == 'nnapi') {
        try {
          options.useNnApiForAndroid = true;
          _logger.i('NNAPI delegate enabled for $key');
        } catch (e) {
          _logger.w('NNAPI delegate not available, falling back to CPU: $e');
        }
      }

      final interpreter = await Interpreter.fromAsset(
        assetPath,
        options: options,
      );

      stopwatch.stop();
      final loadTimeMs = stopwatch.elapsedMicroseconds / 1000.0;
      _modelLoadTimes[key.toString()] = loadTimeMs;
      
      _logger.i('${key} loaded in ${loadTimeMs.toStringAsFixed(1)}ms');
      _logger.i('  Input shape: ${interpreter.getInputTensor(0).shape}');
      _logger.i('  Output shape: ${interpreter.getOutputTensor(0).shape}');

      // Get model file size
      try {
        final byteData = await rootBundle.load(assetPath);
        _modelSizes[key.toString()] = byteData.lengthInBytes;
        _logger.i(
            '  Model size: ${(byteData.lengthInBytes / 1024 / 1024).toStringAsFixed(1)} MB');
      } catch (_) {}

      // Store interpreter
      _interpreters[key] = interpreter;

      // Update legacy references
      switch (type) {
        case ModelType.mobilenet:
          _mobilenetInterpreter = interpreter;
          break;
        case ModelType.resnet:
          _resnetInterpreter = interpreter;
          break;
      }

      _modelLoaded[type] = true;
      _activeVariant[type] = variant;
      _activeDelegate[type] = delegate;

      return loadTimeMs;
    } catch (e) {
      _logger.e('Failed to load ${key}', error: e);
      _modelLoaded[type] = false;
      return 0.0;
    }
  }

  /// Preprocess image bytes for inference (224x224, normalized)
  /// Returns the preprocessed input and stores preprocessing time
  Float32List _preprocessImage(Uint8List imageBytes, ModelType modelType) {
    final stopwatch = Stopwatch()..start();

    // Decode image
    final image = img.decodeImage(imageBytes);
    if (image == null) {
      throw Exception('Failed to decode image');
    }

    // Resize to 224x224
    final resized = img.copyResize(
      image,
      width: AppConstants.inputSize,
      height: AppConstants.inputSize,
      interpolation: img.Interpolation.linear,
    );

    // Create float32 buffer [1, 224, 224, 3]
    final input = Float32List(1 * 224 * 224 * 3);
    int idx = 0;

    for (int y = 0; y < 224; y++) {
      for (int x = 0; x < 224; x++) {
        final pixel = resized.getPixel(x, y);
        final r = pixel.r.toDouble();
        final g = pixel.g.toDouble();
        final b = pixel.b.toDouble();

        if (modelType == ModelType.mobilenet) {
          // MobileNetV2 preprocessing: scale to [-1, 1]
          input[idx++] = (r / 127.5) - 1.0;
          input[idx++] = (g / 127.5) - 1.0;
          input[idx++] = (b / 127.5) - 1.0;
        } else {
          // ResNet50 preprocessing: zero-center with ImageNet means
          // ImageNet means: R=123.68, G=116.779, B=103.939 (in RGB order)
          input[idx++] = r - 123.68;
          input[idx++] = g - 116.779;
          input[idx++] = b - 103.939;
        }
      }
    }

    stopwatch.stop();
    _lastPreprocessingTimeMs = stopwatch.elapsedMicroseconds / 1000.0;
    _logger.d('Preprocessing took ${_lastPreprocessingTimeMs.toStringAsFixed(2)}ms');

    return input;
  }

  /// Run inference on a single model
  Future<PredictionResult> predict(
    Uint8List imageBytes, {
    ModelType modelType = ModelType.mobilenet,
  }) async {
    final interpreter = modelType == ModelType.mobilenet
        ? _mobilenetInterpreter
        : _resnetInterpreter;

    if (interpreter == null) {
      throw Exception('${modelType.name} model is not loaded');
    }

    // Preprocess
    final preprocessWatch = Stopwatch()..start();
    final inputData = _preprocessImage(imageBytes, modelType);
    preprocessWatch.stop();

    // Reshape input to [1, 224, 224, 3]
    final input = inputData.reshape([1, 224, 224, 3]);

    // Output buffer [1, 10]
    final output = List.filled(1 * AppConstants.numClasses, 0.0)
        .reshape([1, AppConstants.numClasses]);

    // Run inference
    final inferenceWatch = Stopwatch()..start();
    interpreter.run(input, output);
    inferenceWatch.stop();

    final inferenceMs = inferenceWatch.elapsedMicroseconds / 1000.0;
    _logger.i('${modelType.name} inference: ${inferenceMs.toStringAsFixed(1)}ms');

    // Apply softmax to raw logits
    final rawOutput = List<double>.from(output[0] as List);
    final predictions = _softmax(rawOutput);

    // Find top prediction
    int maxIdx = 0;
    double maxConf = 0;
    for (int i = 0; i < predictions.length; i++) {
      if (predictions[i] > maxConf) {
        maxConf = predictions[i];
        maxIdx = i;
      }
    }

    final rawClassName = AppConstants.classNames[maxIdx];
    final displayName =
        AppConstants.displayNames[rawClassName] ?? rawClassName;

    // Build all predictions map
    final allPreds = <String, double>{};
    for (int i = 0; i < AppConstants.classNames.length; i++) {
      final name = AppConstants.displayNames[AppConstants.classNames[i]] ??
          AppConstants.classNames[i];
      allPreds[name] = double.parse(predictions[i].toStringAsFixed(4));
    }

    // Sort by confidence descending
    final sortedPreds = Map.fromEntries(
      allPreds.entries.toList()..sort((a, b) => b.value.compareTo(a.value)),
    );

    return PredictionResult(
      disease: displayName,
      rawClass: rawClassName,
      confidence: double.parse(maxConf.toStringAsFixed(4)),
      isHealthy: rawClassName.toLowerCase().contains('healthy'),
      modelUsed: modelType == ModelType.mobilenet ? 'MobileNetV2' : 'ResNet50',
      modelVariant: _activeVariant[modelType] ?? 'fp32',
      delegateType: _activeDelegate[modelType] ?? 'cpu',
      inferenceTimeMs: double.parse(inferenceMs.toStringAsFixed(2)),
      preprocessingTimeMs: double.parse(_lastPreprocessingTimeMs.toStringAsFixed(2)),
      allPredictions: sortedPreds,
    );
  }

  /// Run both models and return comparison
  Future<ModelComparisonResult> compareModels(Uint8List imageBytes) async {
    if (!(_modelLoaded[ModelType.mobilenet] ?? false)) {
      throw Exception('MobileNetV2 model not loaded');
    }
    if (!(_modelLoaded[ModelType.resnet] ?? false)) {
      throw Exception('ResNet50 model not loaded');
    }

    final mobilenetResult = await predict(
      imageBytes,
      modelType: ModelType.mobilenet,
    );
    final resnetResult = await predict(
      imageBytes,
      modelType: ModelType.resnet,
    );

    return ModelComparisonResult(
      mobilenetResult: mobilenetResult,
      resnetResult: resnetResult,
    );
  }

  /// Softmax function
  List<double> _softmax(List<double> logits) {
    final maxLogit = logits.reduce((a, b) => a > b ? a : b);
    final exps = logits.map((l) => _exp(l - maxLogit)).toList();
    final sum = exps.reduce((a, b) => a + b);
    return exps.map((e) => e / sum).toList();
  }

  /// Safe exp to prevent overflow
  double _exp(double x) {
    if (x > 80) return double.maxFinite;
    if (x < -80) return 0;
    return x >= 0
        ? 1.0 + x + (x * x / 2) + (x * x * x / 6) + (x * x * x * x / 24)
        : 1.0 /
            (1.0 +
                (-x) +
                ((-x) * (-x) / 2) +
                ((-x) * (-x) * (-x) / 6) +
                ((-x) * (-x) * (-x) * (-x) / 24));
  }

  /// Get model status information including efficiency metrics for study
  Map<String, dynamic> getModelStatus() {
    return {
      'mobilenet': {
        'loaded': _modelLoaded[ModelType.mobilenet],
        'variant': _activeVariant[ModelType.mobilenet],
        'delegate': _activeDelegate[ModelType.mobilenet],
        'size': getModelSizeMB(ModelType.mobilenet),
        'size_bytes': getModelSizeBytes(ModelType.mobilenet),
        'load_time_ms': getModelLoadTimeMs(ModelType.mobilenet),
        'input_shape': _mobilenetInterpreter?.getInputTensor(0).shape.toString(),
      },
      'resnet': {
        'loaded': _modelLoaded[ModelType.resnet],
        'variant': _activeVariant[ModelType.resnet],
        'delegate': _activeDelegate[ModelType.resnet],
        'size': getModelSizeMB(ModelType.resnet),
        'size_bytes': getModelSizeBytes(ModelType.resnet),
        'load_time_ms': getModelLoadTimeMs(ModelType.resnet),
        'input_shape': _resnetInterpreter?.getInputTensor(0).shape.toString(),
      },
    };
  }

  /// Get comprehensive efficiency metrics for study objective 2.2.3
  Map<String, dynamic> getEfficiencyMetrics() {
    return {
      'mobilenet': {
        'model_size_mb': getModelSizeBytes(ModelType.mobilenet) / (1024 * 1024),
        'load_time_ms': getModelLoadTimeMs(ModelType.mobilenet),
        'variant': _activeVariant[ModelType.mobilenet],
        'delegate': _activeDelegate[ModelType.mobilenet],
        'is_loaded': _modelLoaded[ModelType.mobilenet] ?? false,
      },
      'resnet': {
        'model_size_mb': getModelSizeBytes(ModelType.resnet) / (1024 * 1024),
        'load_time_ms': getModelLoadTimeMs(ModelType.resnet),
        'variant': _activeVariant[ModelType.resnet],
        'delegate': _activeDelegate[ModelType.resnet],
        'is_loaded': _modelLoaded[ModelType.resnet] ?? false,
      },
      'last_preprocessing_time_ms': _lastPreprocessingTimeMs,
    };
  }

  @override
  void dispose() {
    for (final interp in _interpreters.values) {
      interp.close();
    }
    _interpreters.clear();
    _mobilenetInterpreter = null;
    _resnetInterpreter = null;
    super.dispose();
  }
}
