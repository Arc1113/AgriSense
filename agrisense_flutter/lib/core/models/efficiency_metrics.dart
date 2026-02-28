/// Efficiency metrics model for computational performance study.
/// Supports research objective 2.2.3: Compare computational efficiency 
/// across float32/float16/int8 variants with CPU/NNAPI delegates.
class EfficiencyMetrics {
  /// Model name (MobileNetV2, ResNet50)
  final String modelName;
  
  /// Quantization variant (fp32, float16, int8)
  final String modelVariant;
  
  /// Delegate used (cpu, nnapi)
  final String delegateType;

  /// Model file size in bytes
  final int modelSizeBytes;

  /// Time to load model from assets (ms) - equivalent to "model preparation time"
  final double modelLoadTimeMs;

  /// Time to preprocess image (resize, normalize) in ms
  final double preprocessingTimeMs;

  /// Pure inference time (model forward pass) in ms
  final double inferenceTimeMs;
  
  /// Peak RAM usage during inference (MB), null if not measured
  final double? peakRamMB;
  
  /// Energy consumed per inference (battery %), null if not measured
  final double? energyPerInference;

  /// Total diagnosis time = preprocessing + inference (ms)
  double get totalDiagnosisTimeMs => preprocessingTimeMs + inferenceTimeMs;

  /// Throughput: diagnoses per second (single image)
  double get throughputPerSecond => 1000.0 / totalDiagnosisTimeMs;

  /// FPS equivalent (frames per second)
  double get fps => 1000.0 / inferenceTimeMs;

  /// Memory footprint in MB
  double get modelSizeMB => modelSizeBytes / (1024 * 1024);

  /// Timestamp when metrics were captured
  final DateTime timestamp;

  EfficiencyMetrics({
    required this.modelName,
    this.modelVariant = 'fp32',
    this.delegateType = 'cpu',
    required this.modelSizeBytes,
    required this.modelLoadTimeMs,
    required this.preprocessingTimeMs,
    required this.inferenceTimeMs,
    this.peakRamMB,
    this.energyPerInference,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Create from benchmark run data
  factory EfficiencyMetrics.fromBenchmark({
    required String modelName,
    String modelVariant = 'fp32',
    String delegateType = 'cpu',
    required int modelSizeBytes,
    required double modelLoadTimeMs,
    required double preprocessingTimeMs,
    required double inferenceTimeMs,
    double? peakRamMB,
    double? energyPerInference,
  }) {
    return EfficiencyMetrics(
      modelName: modelName,
      modelVariant: modelVariant,
      delegateType: delegateType,
      modelSizeBytes: modelSizeBytes,
      modelLoadTimeMs: modelLoadTimeMs,
      preprocessingTimeMs: preprocessingTimeMs,
      inferenceTimeMs: inferenceTimeMs,
      peakRamMB: peakRamMB,
      energyPerInference: energyPerInference,
    );
  }

  Map<String, dynamic> toJson() => {
        'model_name': modelName,
        'model_variant': modelVariant,
        'delegate_type': delegateType,
        'model_size_bytes': modelSizeBytes,
        'model_size_mb': modelSizeMB.toStringAsFixed(2),
        'model_load_time_ms': modelLoadTimeMs,
        'preprocessing_time_ms': preprocessingTimeMs,
        'inference_time_ms': inferenceTimeMs,
        'total_diagnosis_time_ms': totalDiagnosisTimeMs,
        'throughput_per_second': throughputPerSecond.toStringAsFixed(2),
        'fps': fps.toStringAsFixed(2),
        'peak_ram_mb': peakRamMB,
        'energy_per_inference': energyPerInference,
        'timestamp': timestamp.toIso8601String(),
      };

  @override
  String toString() => 
    '$modelName ($modelVariant/$delegateType): inference=${inferenceTimeMs.toStringAsFixed(1)}ms, '
    'total=${totalDiagnosisTimeMs.toStringAsFixed(1)}ms, '
    'load=${modelLoadTimeMs.toStringAsFixed(0)}ms';
}

/// Aggregated statistics for multiple benchmark runs
class EfficiencyStats {
  final String modelName;
  final String modelVariant;
  final String delegateType;
  final int sampleCount;
  
  // Inference time statistics
  final double meanInferenceMs;
  final double medianInferenceMs;
  final double minInferenceMs;
  final double maxInferenceMs;
  final double stdDevInferenceMs;
  final double p95InferenceMs;
  final double p99InferenceMs;

  // Preprocessing time statistics  
  final double meanPreprocessingMs;

  // Total diagnosis time statistics
  final double meanTotalDiagnosisMs;

  // Model metadata
  final double modelSizeMB;
  final double modelLoadTimeMs;
  
  // Peak RAM (MB), null if not measured
  final double? peakRamMB;
  
  // Energy per inference (battery %), null if not measured
  final double? energyPerInference;

  // Raw per-run timings (for inferential statistics)
  final List<double> rawInferenceTimesMs;
  final List<double> rawPreprocessingTimesMs;

  // Derived metrics
  double get meanFPS => 1000.0 / meanInferenceMs;
  double get meanThroughput => 1000.0 / meanTotalDiagnosisMs;
  
  /// Coefficient of variation (stdDev / mean * 100) - lower is more consistent
  double get variabilityPercent => (stdDevInferenceMs / meanInferenceMs) * 100;

  EfficiencyStats({
    required this.modelName,
    this.modelVariant = 'fp32',
    this.delegateType = 'cpu',
    required this.sampleCount,
    required this.meanInferenceMs,
    required this.medianInferenceMs,
    required this.minInferenceMs,
    required this.maxInferenceMs,
    required this.stdDevInferenceMs,
    required this.p95InferenceMs,
    required this.p99InferenceMs,
    required this.meanPreprocessingMs,
    required this.meanTotalDiagnosisMs,
    required this.modelSizeMB,
    required this.modelLoadTimeMs,
    this.peakRamMB,
    this.energyPerInference,
    this.rawInferenceTimesMs = const [],
    this.rawPreprocessingTimesMs = const [],
  });

  /// Compute statistics from a list of individual runs
  factory EfficiencyStats.fromRuns({
    required String modelName,
    String modelVariant = 'fp32',
    String delegateType = 'cpu',
    required List<double> inferenceTimes,
    required List<double> preprocessingTimes,
    required double modelSizeMB,
    required double modelLoadTimeMs,
    double? peakRamMB,
    double? energyPerInference,
  }) {
    if (inferenceTimes.isEmpty) {
      throw ArgumentError('inferenceTimes cannot be empty');
    }

    final sortedInference = List<double>.from(inferenceTimes)..sort();
    final n = sortedInference.length;

    // Mean
    final meanInf = sortedInference.reduce((a, b) => a + b) / n;
    final meanPrep = preprocessingTimes.reduce((a, b) => a + b) / n;

    // Median
    final medianInf = n.isOdd 
        ? sortedInference[n ~/ 2]
        : (sortedInference[n ~/ 2 - 1] + sortedInference[n ~/ 2]) / 2;

    // Std deviation
    final variance = sortedInference
        .map((t) => (t - meanInf) * (t - meanInf))
        .reduce((a, b) => a + b) / n;
    final stdDev = _sqrt(variance);

    // Percentiles
    final p95Idx = ((n - 1) * 0.95).round().clamp(0, n - 1);
    final p99Idx = ((n - 1) * 0.99).round().clamp(0, n - 1);

    return EfficiencyStats(
      modelName: modelName,
      modelVariant: modelVariant,
      delegateType: delegateType,
      sampleCount: n,
      meanInferenceMs: meanInf,
      medianInferenceMs: medianInf,
      minInferenceMs: sortedInference.first,
      maxInferenceMs: sortedInference.last,
      stdDevInferenceMs: stdDev,
      p95InferenceMs: sortedInference[p95Idx],
      p99InferenceMs: sortedInference[p99Idx],
      meanPreprocessingMs: meanPrep,
      meanTotalDiagnosisMs: meanInf + meanPrep,
      modelSizeMB: modelSizeMB,
      modelLoadTimeMs: modelLoadTimeMs,
      peakRamMB: peakRamMB,
      energyPerInference: energyPerInference,
      rawInferenceTimesMs: List<double>.from(inferenceTimes),
      rawPreprocessingTimesMs: List<double>.from(preprocessingTimes),
    );
  }

  static double _sqrt(double x) {
    if (x <= 0) return 0;
    double guess = x / 2;
    for (int i = 0; i < 20; i++) {
      guess = (guess + x / guess) / 2;
    }
    return guess;
  }

  Map<String, dynamic> toJson() => {
        'model_name': modelName,
        'model_variant': modelVariant,
        'delegate_type': delegateType,
        'sample_count': sampleCount,
        'model_size_mb': modelSizeMB.toStringAsFixed(2),
        'model_load_time_ms': modelLoadTimeMs.toStringAsFixed(1),
        'inference': {
          'mean_ms': meanInferenceMs.toStringAsFixed(2),
          'median_ms': medianInferenceMs.toStringAsFixed(2),
          'min_ms': minInferenceMs.toStringAsFixed(2),
          'max_ms': maxInferenceMs.toStringAsFixed(2),
          'std_dev_ms': stdDevInferenceMs.toStringAsFixed(2),
          'p95_ms': p95InferenceMs.toStringAsFixed(2),
          'p99_ms': p99InferenceMs.toStringAsFixed(2),
        },
        'preprocessing_mean_ms': meanPreprocessingMs.toStringAsFixed(2),
        'total_diagnosis_mean_ms': meanTotalDiagnosisMs.toStringAsFixed(2),
        'peak_ram_mb': peakRamMB,
        'energy_per_inference': energyPerInference,
        'raw_inference_times_ms': rawInferenceTimesMs,
        'raw_preprocessing_times_ms': rawPreprocessingTimesMs,
        'derived': {
          'mean_fps': meanFPS.toStringAsFixed(2),
          'mean_throughput': meanThroughput.toStringAsFixed(2),
          'variability_percent': variabilityPercent.toStringAsFixed(2),
        },
      };
}

/// Comparative analysis between two models for study reporting
class EfficiencyComparison {
  final EfficiencyStats model1Stats;
  final EfficiencyStats model2Stats;
  final DateTime timestamp;

  EfficiencyComparison({
    required this.model1Stats,
    required this.model2Stats,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Which model has faster inference
  String get fasterModel => 
      model1Stats.meanInferenceMs <= model2Stats.meanInferenceMs
          ? model1Stats.modelName
          : model2Stats.modelName;

  /// Speed ratio (slower / faster)
  double get speedRatio {
    final faster = model1Stats.meanInferenceMs <= model2Stats.meanInferenceMs
        ? model1Stats.meanInferenceMs
        : model2Stats.meanInferenceMs;
    final slower = model1Stats.meanInferenceMs > model2Stats.meanInferenceMs
        ? model1Stats.meanInferenceMs
        : model2Stats.meanInferenceMs;
    return slower / faster;
  }

  /// Size ratio (larger / smaller)
  double get sizeRatio {
    final smaller = model1Stats.modelSizeMB <= model2Stats.modelSizeMB
        ? model1Stats.modelSizeMB
        : model2Stats.modelSizeMB;
    final larger = model1Stats.modelSizeMB > model2Stats.modelSizeMB
        ? model1Stats.modelSizeMB
        : model2Stats.modelSizeMB;
    return larger / smaller;
  }

  /// Model load time comparison  
  double get loadTimeRatio {
    final faster = model1Stats.modelLoadTimeMs <= model2Stats.modelLoadTimeMs
        ? model1Stats.modelLoadTimeMs
        : model2Stats.modelLoadTimeMs;
    final slower = model1Stats.modelLoadTimeMs > model2Stats.modelLoadTimeMs
        ? model1Stats.modelLoadTimeMs
        : model2Stats.modelLoadTimeMs;
    return slower / faster;
  }

  /// Which model is smaller
  String get smallerModel =>
      model1Stats.modelSizeMB <= model2Stats.modelSizeMB
          ? model1Stats.modelName
          : model2Stats.modelName;

  /// Which model is more consistent (lower variability)
  String get moreConsistentModel =>
      model1Stats.variabilityPercent <= model2Stats.variabilityPercent
          ? model1Stats.modelName
          : model2Stats.modelName;

  /// Generate study-ready summary text
  String get studySummary {
    String _label(EfficiencyStats s) =>
        '${s.modelName} (${s.modelVariant}/${s.delegateType})';
    final buffer = StringBuffer();
    buffer.writeln('=== Computational Efficiency Comparison ===');
    buffer.writeln('');
    buffer.writeln('Model 1: ${_label(model1Stats)}');
    buffer.writeln('  - Model Size: ${model1Stats.modelSizeMB.toStringAsFixed(2)} MB');
    buffer.writeln('  - Load Time: ${model1Stats.modelLoadTimeMs.toStringAsFixed(1)} ms');
    buffer.writeln('  - Mean Inference: ${model1Stats.meanInferenceMs.toStringAsFixed(2)} ms');
    buffer.writeln('  - Mean FPS: ${model1Stats.meanFPS.toStringAsFixed(2)}');
    buffer.writeln('  - Variability: ${model1Stats.variabilityPercent.toStringAsFixed(2)}%');
    if (model1Stats.peakRamMB != null) {
      buffer.writeln('  - Peak RAM: ${model1Stats.peakRamMB!.toStringAsFixed(1)} MB');
    }
    buffer.writeln('');
    buffer.writeln('Model 2: ${_label(model2Stats)}');
    buffer.writeln('  - Model Size: ${model2Stats.modelSizeMB.toStringAsFixed(2)} MB');
    buffer.writeln('  - Load Time: ${model2Stats.modelLoadTimeMs.toStringAsFixed(1)} ms');
    buffer.writeln('  - Mean Inference: ${model2Stats.meanInferenceMs.toStringAsFixed(2)} ms');
    buffer.writeln('  - Mean FPS: ${model2Stats.meanFPS.toStringAsFixed(2)}');
    buffer.writeln('  - Variability: ${model2Stats.variabilityPercent.toStringAsFixed(2)}%');
    if (model2Stats.peakRamMB != null) {
      buffer.writeln('  - Peak RAM: ${model2Stats.peakRamMB!.toStringAsFixed(1)} MB');
    }
    buffer.writeln('');
    buffer.writeln('Comparison Results:');
    buffer.writeln('  - Faster Model: $fasterModel (${speedRatio.toStringAsFixed(2)}x faster)');
    buffer.writeln('  - Smaller Model: $smallerModel (${sizeRatio.toStringAsFixed(2)}x smaller)');
    buffer.writeln('  - More Consistent: $moreConsistentModel');
    return buffer.toString();
  }

  Map<String, dynamic> toJson() => {
        'model1': model1Stats.toJson(),
        'model2': model2Stats.toJson(),
        'comparison': {
          'faster_model': fasterModel,
          'speed_ratio': speedRatio.toStringAsFixed(2),
          'smaller_model': smallerModel,
          'size_ratio': sizeRatio.toStringAsFixed(2),
          'more_consistent_model': moreConsistentModel,
          'load_time_ratio': loadTimeRatio.toStringAsFixed(2),
        },
        'timestamp': timestamp.toIso8601String(),
      };
}

/// Per-class classification metrics for test set evaluation
class ClassMetrics {
  final String className;
  final int truePositives;
  final int falsePositives;
  final int falseNegatives;
  final int trueNegatives;

  ClassMetrics({
    required this.className,
    required this.truePositives,
    required this.falsePositives,
    required this.falseNegatives,
    required this.trueNegatives,
  });

  double get precision =>
      truePositives + falsePositives == 0
          ? 0.0
          : truePositives / (truePositives + falsePositives);

  double get recall =>
      truePositives + falseNegatives == 0
          ? 0.0
          : truePositives / (truePositives + falseNegatives);

  double get f1Score =>
      precision + recall == 0 ? 0.0 : 2 * precision * recall / (precision + recall);

  double get specificity =>
      trueNegatives + falsePositives == 0
          ? 0.0
          : trueNegatives / (trueNegatives + falsePositives);

  int get support => truePositives + falseNegatives;

  Map<String, dynamic> toJson() => {
        'class': className,
        'precision': precision,
        'recall': recall,
        'f1_score': f1Score,
        'specificity': specificity,
        'support': support,
      };
}

/// Results of batch test set evaluation on device
class TestSetResults {
  final String modelName;
  final String modelVariant;
  final String delegateType;
  final int totalImages;
  final int correctPredictions;
  final List<ClassMetrics> perClassMetrics;

  /// Row-major flattened confusion matrix (numClasses x numClasses)
  final List<int> confusionMatrix;
  final int numClasses;

  /// Timestamp of evaluation
  final DateTime timestamp;

  TestSetResults({
    required this.modelName,
    this.modelVariant = 'fp32',
    this.delegateType = 'cpu',
    required this.totalImages,
    required this.correctPredictions,
    required this.perClassMetrics,
    required this.confusionMatrix,
    required this.numClasses,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  double get accuracy => totalImages == 0 ? 0.0 : correctPredictions / totalImages;

  /// Macro-averaged precision
  double get macroPrecision =>
      perClassMetrics.isEmpty
          ? 0.0
          : perClassMetrics.map((c) => c.precision).reduce((a, b) => a + b) /
              perClassMetrics.length;

  /// Macro-averaged recall
  double get macroRecall =>
      perClassMetrics.isEmpty
          ? 0.0
          : perClassMetrics.map((c) => c.recall).reduce((a, b) => a + b) /
              perClassMetrics.length;

  /// Macro-averaged F1
  double get macroF1 =>
      perClassMetrics.isEmpty
          ? 0.0
          : perClassMetrics.map((c) => c.f1Score).reduce((a, b) => a + b) /
              perClassMetrics.length;

  /// Macro-averaged specificity
  double get macroSpecificity =>
      perClassMetrics.isEmpty
          ? 0.0
          : perClassMetrics.map((c) => c.specificity).reduce((a, b) => a + b) /
              perClassMetrics.length;

  /// Confusion matrix as 2D list
  List<List<int>> get confusionMatrix2D {
    final matrix = <List<int>>[];
    for (int i = 0; i < numClasses; i++) {
      matrix.add(confusionMatrix.sublist(i * numClasses, (i + 1) * numClasses));
    }
    return matrix;
  }

  Map<String, dynamic> toJson() => {
        'model_name': modelName,
        'model_variant': modelVariant,
        'delegate_type': delegateType,
        'total_images': totalImages,
        'correct_predictions': correctPredictions,
        'accuracy': accuracy,
        'macro_precision': macroPrecision,
        'macro_recall': macroRecall,
        'macro_f1': macroF1,
        'macro_specificity': macroSpecificity,
        'per_class': perClassMetrics.map((c) => c.toJson()).toList(),
        'confusion_matrix': confusionMatrix2D,
        'timestamp': timestamp.toIso8601String(),
      };

  @override
  String toString() =>
      '$modelName ($modelVariant/$delegateType): accuracy=${(accuracy * 100).toStringAsFixed(2)}%, '
      'macroF1=${(macroF1 * 100).toStringAsFixed(2)}%, '
      'n=$totalImages';
}
