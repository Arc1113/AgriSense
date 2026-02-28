/// Data model for a disease prediction result.
/// Updated to support study objective 2.2.3: measuring computational efficiency
/// and supporting float32/float16/int8 model variants with CPU/NNAPI delegates.
class PredictionResult {
  final String disease;
  final String rawClass;
  final double confidence;
  final bool isHealthy;
  final String modelUsed;
  
  /// Model quantization variant (fp32, float16, int8)
  final String modelVariant;
  
  /// Inference delegate used (cpu, nnapi)
  final String delegateType;
  
  /// Pure model inference time in milliseconds
  final double inferenceTimeMs;
  
  /// Image preprocessing time (resize, normalize) in milliseconds
  final double preprocessingTimeMs;
  
  /// Peak RAM usage during inference in MB (null if not measured)
  final double? peakRamMB;
  
  /// Total diagnosis time = preprocessing + inference (ms)
  double get totalDiagnosisTimeMs => preprocessingTimeMs + inferenceTimeMs;
  
  /// Throughput: how many diagnoses per second (based on total time)
  double get diagnosesPerSecond => 1000.0 / totalDiagnosisTimeMs;
  
  /// Frames per second equivalent (based on inference only)
  double get fps => 1000.0 / inferenceTimeMs;
  
  final Map<String, double> allPredictions;
  final DateTime timestamp;

  PredictionResult({
    required this.disease,
    required this.rawClass,
    required this.confidence,
    required this.isHealthy,
    required this.modelUsed,
    this.modelVariant = 'fp32',
    this.delegateType = 'cpu',
    required this.inferenceTimeMs,
    this.preprocessingTimeMs = 0.0,
    this.peakRamMB,
    required this.allPredictions,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Severity based on disease type
  String get severity {
    if (isHealthy) return 'None';
    if (confidence < 0.5) return 'Low';
    if (confidence < 0.75) return 'Medium';
    return 'High';
  }

  Map<String, dynamic> toJson() => {
        'disease': disease,
        'raw_class': rawClass,
        'confidence': confidence,
        'is_healthy': isHealthy,
        'model_used': modelUsed,
        'model_variant': modelVariant,
        'delegate_type': delegateType,
        'inference_time_ms': inferenceTimeMs,
        'preprocessing_time_ms': preprocessingTimeMs,
        'total_diagnosis_time_ms': totalDiagnosisTimeMs,
        'diagnoses_per_second': diagnosesPerSecond,
        'fps': fps,
        'peak_ram_mb': peakRamMB,
        'all_predictions': allPredictions,
        'timestamp': timestamp.toIso8601String(),
      };

  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    return PredictionResult(
      disease: json['disease'] ?? 'Unknown',
      rawClass: json['raw_class'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      isHealthy: json['is_healthy'] ?? false,
      modelUsed: json['model_used'] ?? 'unknown',
      modelVariant: json['model_variant'] ?? 'fp32',
      delegateType: json['delegate_type'] ?? 'cpu',
      inferenceTimeMs: (json['inference_time_ms'] ?? 0.0).toDouble(),
      preprocessingTimeMs: (json['preprocessing_time_ms'] ?? 0.0).toDouble(),
      peakRamMB: json['peak_ram_mb'] != null ? (json['peak_ram_mb'] as num).toDouble() : null,
      allPredictions: Map<String, double>.from(
        (json['all_predictions'] ?? {}).map(
          (k, v) => MapEntry(k.toString(), (v as num).toDouble()),
        ),
      ),
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
    );
  }
}

/// Data model for comparing two model results
class ModelComparisonResult {
  final PredictionResult mobilenetResult;
  final PredictionResult resnetResult;
  final DateTime timestamp;

  ModelComparisonResult({
    required this.mobilenetResult,
    required this.resnetResult,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Whether both models agree on the diagnosis
  bool get modelsAgree => mobilenetResult.disease == resnetResult.disease;

  /// Speed difference (positive = mobilenet faster)
  double get speedDifferenceMs =>
      resnetResult.inferenceTimeMs - mobilenetResult.inferenceTimeMs;

  /// Which model is more confident
  String get moreConfidentModel =>
      mobilenetResult.confidence >= resnetResult.confidence
          ? 'MobileNetV2'
          : 'ResNet50';

  /// Which model is faster
  String get fasterModel =>
      mobilenetResult.inferenceTimeMs <= resnetResult.inferenceTimeMs
          ? 'MobileNetV2'
          : 'ResNet50';
}

/// Benchmark result for a single model run
class BenchmarkEntry {
  final String modelName;
  final double inferenceTimeMs;
  final double confidence;
  final String predictedClass;
  final int imageWidth;
  final int imageHeight;
  final double preprocessTimeMs;
  final DateTime timestamp;

  BenchmarkEntry({
    required this.modelName,
    required this.inferenceTimeMs,
    required this.confidence,
    required this.predictedClass,
    this.imageWidth = 224,
    this.imageHeight = 224,
    this.preprocessTimeMs = 0,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

/// Scan history item stored locally
class ScanHistoryItem {
  final String id;
  final String imagePath;
  final PredictionResult result;
  final ModelComparisonResult? comparison;
  final DateTime savedAt;

  ScanHistoryItem({
    required this.id,
    required this.imagePath,
    required this.result,
    this.comparison,
    DateTime? savedAt,
  }) : savedAt = savedAt ?? DateTime.now();
}
