import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:logger/logger.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/models/efficiency_metrics.dart';
import '../../core/models/prediction_result.dart';
import 'device_metrics_service.dart';
import 'disease_classifier.dart';

/// Configuration for a single benchmark run
class BenchmarkConfig {
  final ModelType modelType;
  final String variant;  // fp32, float16, int8
  final String delegate; // cpu, nnapi
  final int warmupRuns;
  final int benchmarkRuns;

  const BenchmarkConfig({
    required this.modelType,
    this.variant = 'fp32',
    this.delegate = 'cpu',
    this.warmupRuns = 5,
    this.benchmarkRuns = 200,
  });

  String get label =>
      '${modelType == ModelType.mobilenet ? "MobileNetV2" : "ResNet50"}'
      ' ($variant/$delegate)';
}

/// Service for benchmarking MobileNetV2 vs ResNet50 performance on-device.
/// Enhanced to support study objective 2.2.3: measuring computational efficiency
/// across float32/float16/int8 variants with CPU/NNAPI delegates.
class ModelBenchmarkService extends ChangeNotifier {
  final Logger _logger = Logger();

  bool _isRunning = false;
  double _progress = 0.0;
  String _statusMessage = '';
  BenchmarkReport? _lastReport;
  FullStudyReport? _lastStudyReport;

  bool get isRunning => _isRunning;
  double get progress => _progress;
  String get statusMessage => _statusMessage;
  BenchmarkReport? get lastReport => _lastReport;
  FullStudyReport? get lastStudyReport => _lastStudyReport;

  /// Run a single-config benchmark (backward compatible, enhanced)
  Future<BenchmarkReport> runBenchmark(
    DiseaseClassifier classifier,
    Uint8List imageBytes, {
    int warmupRuns = 5,
    int benchmarkRuns = 200,
    DeviceMetricsService? deviceMetrics,
  }) async {
    _isRunning = true;
    _progress = 0;
    _statusMessage = 'Starting benchmark...';
    notifyListeners();

    final mobilenetInferenceTimes = <double>[];
    final mobilenetPreprocessingTimes = <double>[];
    final resnetInferenceTimes = <double>[];
    final resnetPreprocessingTimes = <double>[];
    
    PredictionResult? mobilenetPrediction;
    PredictionResult? resnetPrediction;
    double? mobilenetPeakRam;
    double? resnetPeakRam;
    double? mobilenetEnergy;
    double? resnetEnergy;

    final totalRuns = (warmupRuns + benchmarkRuns) * 2;
    int completedRuns = 0;

    try {
      // --- MobileNetV2 ---
      _statusMessage = 'Warming up MobileNetV2...';
      notifyListeners();

      for (int i = 0; i < warmupRuns; i++) {
        await classifier.predict(imageBytes, modelType: ModelType.mobilenet);
        completedRuns++;
        _progress = completedRuns / totalRuns;
        notifyListeners();
      }

      _statusMessage = 'Benchmarking MobileNetV2 (0/$benchmarkRuns)...';
      notifyListeners();

      // Reset RAM before benchmark
      await deviceMetrics?.resetPeakRam();
      final mobilenetBatteryStart = await deviceMetrics?.getBatteryLevel();

      for (int i = 0; i < benchmarkRuns; i++) {
        final result = await classifier.predict(
          imageBytes,
          modelType: ModelType.mobilenet,
        );
        mobilenetInferenceTimes.add(result.inferenceTimeMs);
        mobilenetPreprocessingTimes.add(result.preprocessingTimeMs);
        mobilenetPrediction = result;
        completedRuns++;
        _progress = completedRuns / totalRuns;
        if (i % 20 == 0 || i == benchmarkRuns - 1) {
          _statusMessage = 'Benchmarking MobileNetV2 (${i + 1}/$benchmarkRuns)...';
          notifyListeners();
        }
      }

      mobilenetPeakRam = await deviceMetrics?.getPeakRamMB();
      final mobilenetBatteryEnd = await deviceMetrics?.getBatteryLevel();
      if (mobilenetBatteryStart != null && mobilenetBatteryEnd != null) {
        final totalDelta = mobilenetBatteryStart - mobilenetBatteryEnd;
        mobilenetEnergy = benchmarkRuns > 0 ? totalDelta / benchmarkRuns : null;
      }

      // --- ResNet50 ---
      _statusMessage = 'Warming up ResNet50...';
      notifyListeners();

      for (int i = 0; i < warmupRuns; i++) {
        await classifier.predict(imageBytes, modelType: ModelType.resnet);
        completedRuns++;
        _progress = completedRuns / totalRuns;
        notifyListeners();
      }

      _statusMessage = 'Benchmarking ResNet50 (0/$benchmarkRuns)...';
      notifyListeners();

      await deviceMetrics?.resetPeakRam();
      final resnetBatteryStart = await deviceMetrics?.getBatteryLevel();

      for (int i = 0; i < benchmarkRuns; i++) {
        final result = await classifier.predict(
          imageBytes,
          modelType: ModelType.resnet,
        );
        resnetInferenceTimes.add(result.inferenceTimeMs);
        resnetPreprocessingTimes.add(result.preprocessingTimeMs);
        resnetPrediction = result;
        completedRuns++;
        _progress = completedRuns / totalRuns;
        if (i % 20 == 0 || i == benchmarkRuns - 1) {
          _statusMessage = 'Benchmarking ResNet50 (${i + 1}/$benchmarkRuns)...';
          notifyListeners();
        }
      }

      resnetPeakRam = await deviceMetrics?.getPeakRamMB();
      final resnetBatteryEnd = await deviceMetrics?.getBatteryLevel();
      if (resnetBatteryStart != null && resnetBatteryEnd != null) {
        final totalDelta = resnetBatteryStart - resnetBatteryEnd;
        resnetEnergy = benchmarkRuns > 0 ? totalDelta / benchmarkRuns : null;
      }

      // Build report
      final mobilenetSizeMB =
          classifier.getModelSizeBytes(ModelType.mobilenet) / (1024 * 1024);
      final resnetSizeMB =
          classifier.getModelSizeBytes(ModelType.resnet) / (1024 * 1024);

      final report = BenchmarkReport(
        mobilenetStats: _computeStats(
          'MobileNetV2',
          mobilenetInferenceTimes,
          mobilenetPreprocessingTimes,
        ),
        resnetStats: _computeStats(
          'ResNet50',
          resnetInferenceTimes,
          resnetPreprocessingTimes,
        ),
        mobilenetPrediction: mobilenetPrediction!,
        resnetPrediction: resnetPrediction!,
        warmupRuns: warmupRuns,
        benchmarkRuns: benchmarkRuns,
        mobilenetSizeMB: classifier.getModelSizeMB(ModelType.mobilenet),
        resnetSizeMB: classifier.getModelSizeMB(ModelType.resnet),
        mobilenetLoadTimeMs:
            classifier.getModelLoadTimeMs(ModelType.mobilenet),
        resnetLoadTimeMs: classifier.getModelLoadTimeMs(ModelType.resnet),
        mobilenetEfficiency: EfficiencyStats.fromRuns(
          modelName: 'MobileNetV2',
          modelVariant: classifier.getActiveVariant(ModelType.mobilenet),
          delegateType: classifier.getActiveDelegate(ModelType.mobilenet),
          inferenceTimes: mobilenetInferenceTimes,
          preprocessingTimes: mobilenetPreprocessingTimes,
          modelSizeMB: mobilenetSizeMB,
          modelLoadTimeMs:
              classifier.getModelLoadTimeMs(ModelType.mobilenet),
          peakRamMB: mobilenetPeakRam,
          energyPerInference: mobilenetEnergy,
        ),
        resnetEfficiency: EfficiencyStats.fromRuns(
          modelName: 'ResNet50',
          modelVariant: classifier.getActiveVariant(ModelType.resnet),
          delegateType: classifier.getActiveDelegate(ModelType.resnet),
          inferenceTimes: resnetInferenceTimes,
          preprocessingTimes: resnetPreprocessingTimes,
          modelSizeMB: resnetSizeMB,
          modelLoadTimeMs: classifier.getModelLoadTimeMs(ModelType.resnet),
          peakRamMB: resnetPeakRam,
          energyPerInference: resnetEnergy,
        ),
        timestamp: DateTime.now(),
      );

      _lastReport = report;
      _statusMessage = 'Benchmark complete!';
      _logger.i('Benchmark complete: ${report.summary}');

      return report;
    } catch (e) {
      _statusMessage = 'Benchmark failed: $e';
      _logger.e('Benchmark error', error: e);
      rethrow;
    } finally {
      _isRunning = false;
      _progress = 1.0;
      notifyListeners();
    }
  }

  /// Run a full study across all variant × delegate configurations.
  /// This is the primary method for research data collection.
  ///
  /// Produces a [FullStudyReport] with one [EfficiencyStats] per config.
  Future<FullStudyReport> runFullStudy(
    DiseaseClassifier classifier,
    Uint8List imageBytes, {
    int warmupRuns = 5,
    int benchmarkRuns = 200,
    DeviceMetricsService? deviceMetrics,
    List<BenchmarkConfig>? configs,
  }) async {
    _isRunning = true;
    _progress = 0;
    notifyListeners();

    // Default: all 6 variants × cpu only (add nnapi variants if desired)
    final allConfigs = configs ??
        [
          for (final mt in ModelType.values)
            for (final v in ['fp32', 'float16', 'int8'])
              BenchmarkConfig(
                modelType: mt,
                variant: v,
                delegate: 'cpu',
                warmupRuns: warmupRuns,
                benchmarkRuns: benchmarkRuns,
              ),
        ];

    final results = <EfficiencyStats>[];
    final deviceInfo = await deviceMetrics?.getDeviceInfo() ?? {};

    for (int ci = 0; ci < allConfigs.length; ci++) {
      final cfg = allConfigs[ci];
      _statusMessage = 'Config ${ci + 1}/${allConfigs.length}: ${cfg.label}';
      notifyListeners();

      try {
        // Load model variant
        _statusMessage = 'Loading ${cfg.label}...';
        notifyListeners();
        final loadTime = await classifier.loadModelVariant(
          cfg.modelType,
          variant: cfg.variant,
          delegate: cfg.delegate,
        );

        final modelSizeMB =
            classifier.getModelSizeBytes(cfg.modelType) / (1024 * 1024);

        // Warmup
        _statusMessage = 'Warming up ${cfg.label}...';
        notifyListeners();
        for (int w = 0; w < cfg.warmupRuns; w++) {
          await classifier.predict(imageBytes, modelType: cfg.modelType);
        }

        // Benchmark
        final inferenceTimes = <double>[];
        final preprocessTimes = <double>[];

        await deviceMetrics?.resetPeakRam();
        final batteryStart = await deviceMetrics?.getBatteryLevel();

        for (int r = 0; r < cfg.benchmarkRuns; r++) {
          final result = await classifier.predict(
            imageBytes,
            modelType: cfg.modelType,
          );
          inferenceTimes.add(result.inferenceTimeMs);
          preprocessTimes.add(result.preprocessingTimeMs);

          // Update overall progress
          final configProgress = (r + 1) / cfg.benchmarkRuns;
          _progress =
              (ci + configProgress) / allConfigs.length;
          if (r % 20 == 0 || r == cfg.benchmarkRuns - 1) {
            _statusMessage =
                '${cfg.label}: ${r + 1}/${cfg.benchmarkRuns}';
            notifyListeners();
          }
        }

        final peakRam = await deviceMetrics?.getPeakRamMB();
        final batteryEnd = await deviceMetrics?.getBatteryLevel();
        double? energyPerInf;
        if (batteryStart != null && batteryEnd != null && cfg.benchmarkRuns > 0) {
          energyPerInf = (batteryStart - batteryEnd) / cfg.benchmarkRuns;
        }

        final stats = EfficiencyStats.fromRuns(
          modelName: cfg.modelType == ModelType.mobilenet
              ? 'MobileNetV2'
              : 'ResNet50',
          modelVariant: cfg.variant,
          delegateType: cfg.delegate,
          inferenceTimes: inferenceTimes,
          preprocessingTimes: preprocessTimes,
          modelSizeMB: modelSizeMB,
          modelLoadTimeMs: loadTime,
          peakRamMB: peakRam,
          energyPerInference: energyPerInf,
        );

        results.add(stats);
        _logger.i('Completed: ${cfg.label} → '
            'mean=${stats.meanInferenceMs.toStringAsFixed(2)}ms');
      } catch (e) {
        _logger.e('Failed config ${cfg.label}: $e');
        _statusMessage = 'Failed: ${cfg.label} - $e';
        notifyListeners();
      }
    }

    // Reload default fp32/cpu models
    _statusMessage = 'Restoring default models...';
    notifyListeners();
    await classifier.loadModelVariant(ModelType.mobilenet);
    await classifier.loadModelVariant(ModelType.resnet);

    final report = FullStudyReport(
      results: results,
      deviceInfo: deviceInfo,
      benchmarkRuns: allConfigs.first.benchmarkRuns,
      warmupRuns: allConfigs.first.warmupRuns,
      timestamp: DateTime.now(),
    );

    _lastStudyReport = report;
    _statusMessage = 'Full study complete! (${results.length} configs)';
    _isRunning = false;
    _progress = 1.0;
    notifyListeners();

    return report;
  }

  /// Export study report as CSV for research paper
  Future<String> exportStudyCsv(FullStudyReport report) async {
    final docsDir = await getApplicationDocumentsDirectory();
    final timestamp =
        DateTime.now().toIso8601String().replaceAll(':', '-');
    final file = File(
        '${docsDir.path}/benchmark_study_$timestamp.csv');

    final buffer = StringBuffer();
    buffer.writeln(
      'Model,Variant,Delegate,N,Size_MB,Load_ms,'
      'Mean_ms,Median_ms,Min_ms,Max_ms,StdDev_ms,P95_ms,P99_ms,'
      'Preprocess_ms,Total_ms,FPS,Throughput,'
      'PeakRAM_MB,Energy_per_inf,Variability_%',
    );

    for (final s in report.results) {
      buffer.writeln(
        '${s.modelName},${s.modelVariant},${s.delegateType},'
        '${s.sampleCount},${s.modelSizeMB.toStringAsFixed(2)},'
        '${s.modelLoadTimeMs.toStringAsFixed(1)},'
        '${s.meanInferenceMs.toStringAsFixed(2)},'
        '${s.medianInferenceMs.toStringAsFixed(2)},'
        '${s.minInferenceMs.toStringAsFixed(2)},'
        '${s.maxInferenceMs.toStringAsFixed(2)},'
        '${s.stdDevInferenceMs.toStringAsFixed(2)},'
        '${s.p95InferenceMs.toStringAsFixed(2)},'
        '${s.p99InferenceMs.toStringAsFixed(2)},'
        '${s.meanPreprocessingMs.toStringAsFixed(2)},'
        '${s.meanTotalDiagnosisMs.toStringAsFixed(2)},'
        '${s.meanFPS.toStringAsFixed(2)},'
        '${s.meanThroughput.toStringAsFixed(2)},'
        '${s.peakRamMB?.toStringAsFixed(1) ?? "N/A"},'
        '${s.energyPerInference?.toStringAsFixed(6) ?? "N/A"},'
        '${s.variabilityPercent.toStringAsFixed(2)}',
      );
    }

    await file.writeAsString(buffer.toString());
    _logger.i('Study CSV exported: ${file.path}');
    return file.path;
  }

  /// Export study report as JSON
  Future<String> exportStudyJson(FullStudyReport report) async {
    final docsDir = await getApplicationDocumentsDirectory();
    final timestamp =
        DateTime.now().toIso8601String().replaceAll(':', '-');
    final file = File(
        '${docsDir.path}/benchmark_study_$timestamp.json');

    final jsonStr =
        const JsonEncoder.withIndent('  ').convert(report.toJson());
    await file.writeAsString(jsonStr);
    _logger.i('Study JSON exported: ${file.path}');
    return file.path;
  }

  ModelStats _computeStats(
    String name, 
    List<double> inferenceTimes,
    List<double> preprocessingTimes,
  ) {
    inferenceTimes.sort();
    final sum = inferenceTimes.reduce((a, b) => a + b);
    final mean = sum / inferenceTimes.length;
    final median = inferenceTimes[inferenceTimes.length ~/ 2];
    final min = inferenceTimes.first;
    final max = inferenceTimes.last;

    // Mean preprocessing time
    final meanPreprocessing = preprocessingTimes.reduce((a, b) => a + b) / preprocessingTimes.length;

    // Standard deviation
    final variance =
        inferenceTimes.map((t) => (t - mean) * (t - mean)).reduce((a, b) => a + b) /
            inferenceTimes.length;
    final stdDev = _sqrt(variance);

    // Percentiles
    final p95Index = (inferenceTimes.length * 0.95).floor().clamp(0, inferenceTimes.length - 1);
    final p99Index = (inferenceTimes.length * 0.99).floor().clamp(0, inferenceTimes.length - 1);
    final p95 = inferenceTimes[p95Index];
    final p99 = inferenceTimes[p99Index];

    return ModelStats(
      modelName: name,
      meanMs: mean,
      medianMs: median,
      minMs: min,
      maxMs: max,
      stdDevMs: stdDev,
      p95Ms: p95,
      p99Ms: p99,
      meanPreprocessingMs: meanPreprocessing,
      allTimesMs: inferenceTimes,
    );
  }

  double _sqrt(double x) {
    if (x <= 0) return 0;
    double guess = x / 2;
    for (int i = 0; i < 20; i++) {
      guess = (guess + x / guess) / 2;
    }
    return guess;
  }
}

/// Statistics for a single model's benchmark (enhanced for study)
class ModelStats {
  final String modelName;
  final double meanMs;
  final double medianMs;
  final double minMs;
  final double maxMs;
  final double stdDevMs;
  final double p95Ms;
  final double p99Ms;
  final double meanPreprocessingMs;
  final List<double> allTimesMs;

  ModelStats({
    required this.modelName,
    required this.meanMs,
    required this.medianMs,
    required this.minMs,
    required this.maxMs,
    required this.stdDevMs,
    required this.p95Ms,
    this.p99Ms = 0,
    this.meanPreprocessingMs = 0,
    required this.allTimesMs,
  });

  // Formatted getters for display
  String get formattedMean => '${meanMs.toStringAsFixed(1)} ms';
  String get formattedMedian => '${medianMs.toStringAsFixed(1)} ms';
  String get formattedP95 => '${p95Ms.toStringAsFixed(1)} ms';
  String get formattedP99 => '${p99Ms.toStringAsFixed(1)} ms';
  String get formattedPreprocessing => '${meanPreprocessingMs.toStringAsFixed(1)} ms';
  
  // Derived metrics for study
  double get meanTotalDiagnosisMs => meanMs + meanPreprocessingMs;
  String get formattedTotalDiagnosis => '${meanTotalDiagnosisMs.toStringAsFixed(1)} ms';
  double get fps => 1000.0 / meanMs;
  String get formattedFPS => '${fps.toStringAsFixed(1)} FPS';
  double get throughput => 1000.0 / meanTotalDiagnosisMs;
  String get formattedThroughput => '${throughput.toStringAsFixed(1)} dx/s';
  
  /// Coefficient of variation (lower = more consistent)
  double get variabilityPercent => (stdDevMs / meanMs) * 100;
  String get formattedVariability => '${variabilityPercent.toStringAsFixed(1)}%';
}

/// Full benchmark report comparing both models (enhanced for study objective 2.2.3)
class BenchmarkReport {
  final ModelStats mobilenetStats;
  final ModelStats resnetStats;
  final PredictionResult mobilenetPrediction;
  final PredictionResult resnetPrediction;
  final int warmupRuns;
  final int benchmarkRuns;
  final String mobilenetSizeMB;
  final String resnetSizeMB;
  final double mobilenetLoadTimeMs;
  final double resnetLoadTimeMs;
  final EfficiencyStats mobilenetEfficiency;
  final EfficiencyStats resnetEfficiency;
  final DateTime timestamp;

  BenchmarkReport({
    required this.mobilenetStats,
    required this.resnetStats,
    required this.mobilenetPrediction,
    required this.resnetPrediction,
    required this.warmupRuns,
    required this.benchmarkRuns,
    required this.mobilenetSizeMB,
    required this.resnetSizeMB,
    required this.mobilenetLoadTimeMs,
    required this.resnetLoadTimeMs,
    required this.mobilenetEfficiency,
    required this.resnetEfficiency,
    required this.timestamp,
  });

  bool get modelsAgree =>
      mobilenetPrediction.disease == resnetPrediction.disease;

  String get fasterModel =>
      mobilenetStats.meanMs <= resnetStats.meanMs ? 'MobileNetV2' : 'ResNet50';

  String get slowerModel =>
      mobilenetStats.meanMs > resnetStats.meanMs ? 'MobileNetV2' : 'ResNet50';

  double get speedupFactor {
    final slower = mobilenetStats.meanMs > resnetStats.meanMs
        ? mobilenetStats.meanMs
        : resnetStats.meanMs;
    final faster = mobilenetStats.meanMs <= resnetStats.meanMs
        ? mobilenetStats.meanMs
        : resnetStats.meanMs;
    return slower / faster;
  }

  /// Model load time comparison (for "training time" equivalent)
  String get fasterLoadModel =>
      mobilenetLoadTimeMs <= resnetLoadTimeMs ? 'MobileNetV2' : 'ResNet50';

  double get loadTimeRatio {
    final slower = mobilenetLoadTimeMs > resnetLoadTimeMs
        ? mobilenetLoadTimeMs
        : resnetLoadTimeMs;
    final faster = mobilenetLoadTimeMs <= resnetLoadTimeMs
        ? mobilenetLoadTimeMs
        : resnetLoadTimeMs;
    return slower / faster;
  }

  /// Which model is more consistent (lower variability)
  String get moreConsistentModel =>
      mobilenetStats.variabilityPercent <= resnetStats.variabilityPercent 
          ? 'MobileNetV2' 
          : 'ResNet50';

  String get summary =>
      '$fasterModel is ${speedupFactor.toStringAsFixed(1)}x faster '
      '(${mobilenetStats.formattedMean} vs ${resnetStats.formattedMean}). '
      'Models ${modelsAgree ? "agree" : "disagree"} on diagnosis.';

  /// Generate comprehensive study summary for objective 2.2.3
  String get studySummary {
    final buffer = StringBuffer();
    buffer.writeln('=== COMPUTATIONAL EFFICIENCY COMPARISON ===');
    buffer.writeln('Study Objective 2.2.3: Training Time & Inference Speed');
    buffer.writeln('');
    buffer.writeln('--- MobileNetV2 ---');
    buffer.writeln('Model Size: $mobilenetSizeMB');
    buffer.writeln('Load Time: ${mobilenetLoadTimeMs.toStringAsFixed(1)} ms');
    buffer.writeln('Mean Inference: ${mobilenetStats.formattedMean}');
    buffer.writeln('Mean Preprocessing: ${mobilenetStats.formattedPreprocessing}');
    buffer.writeln('Total Diagnosis: ${mobilenetStats.formattedTotalDiagnosis}');
    buffer.writeln('FPS: ${mobilenetStats.formattedFPS}');
    buffer.writeln('Throughput: ${mobilenetStats.formattedThroughput}');
    buffer.writeln('Variability: ${mobilenetStats.formattedVariability}');
    buffer.writeln('');
    buffer.writeln('--- ResNet50 ---');
    buffer.writeln('Model Size: $resnetSizeMB');
    buffer.writeln('Load Time: ${resnetLoadTimeMs.toStringAsFixed(1)} ms');
    buffer.writeln('Mean Inference: ${resnetStats.formattedMean}');
    buffer.writeln('Mean Preprocessing: ${resnetStats.formattedPreprocessing}');
    buffer.writeln('Total Diagnosis: ${resnetStats.formattedTotalDiagnosis}');
    buffer.writeln('FPS: ${resnetStats.formattedFPS}');
    buffer.writeln('Throughput: ${resnetStats.formattedThroughput}');
    buffer.writeln('Variability: ${resnetStats.formattedVariability}');
    buffer.writeln('');
    buffer.writeln('--- COMPARISON RESULTS ---');
    buffer.writeln('Faster Inference: $fasterModel (${speedupFactor.toStringAsFixed(2)}x)');
    buffer.writeln('Faster Load: $fasterLoadModel (${loadTimeRatio.toStringAsFixed(2)}x)');
    buffer.writeln('More Consistent: $moreConsistentModel');
    buffer.writeln('Diagnosis Agreement: ${modelsAgree ? "Yes" : "No"}');
    return buffer.toString();
  }

  /// Export as JSON for data analysis
  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'config': {
        'warmup_runs': warmupRuns,
        'benchmark_runs': benchmarkRuns,
      },
      'mobilenet': {
        'size_mb': mobilenetSizeMB,
        'load_time_ms': mobilenetLoadTimeMs,
        'inference_mean_ms': mobilenetStats.meanMs,
        'inference_median_ms': mobilenetStats.medianMs,
        'inference_min_ms': mobilenetStats.minMs,
        'inference_max_ms': mobilenetStats.maxMs,
        'inference_stddev_ms': mobilenetStats.stdDevMs,
        'inference_p95_ms': mobilenetStats.p95Ms,
        'inference_p99_ms': mobilenetStats.p99Ms,
        'preprocessing_mean_ms': mobilenetStats.meanPreprocessingMs,
        'total_diagnosis_ms': mobilenetStats.meanTotalDiagnosisMs,
        'fps': mobilenetStats.fps,
        'throughput': mobilenetStats.throughput,
        'variability_percent': mobilenetStats.variabilityPercent,
        'prediction': mobilenetPrediction.disease,
        'confidence': mobilenetPrediction.confidence,
      },
      'resnet': {
        'size_mb': resnetSizeMB,
        'load_time_ms': resnetLoadTimeMs,
        'inference_mean_ms': resnetStats.meanMs,
        'inference_median_ms': resnetStats.medianMs,
        'inference_min_ms': resnetStats.minMs,
        'inference_max_ms': resnetStats.maxMs,
        'inference_stddev_ms': resnetStats.stdDevMs,
        'inference_p95_ms': resnetStats.p95Ms,
        'inference_p99_ms': resnetStats.p99Ms,
        'preprocessing_mean_ms': resnetStats.meanPreprocessingMs,
        'total_diagnosis_ms': resnetStats.meanTotalDiagnosisMs,
        'fps': resnetStats.fps,
        'throughput': resnetStats.throughput,
        'variability_percent': resnetStats.variabilityPercent,
        'prediction': resnetPrediction.disease,
        'confidence': resnetPrediction.confidence,
      },
      'comparison': {
        'faster_model': fasterModel,
        'speedup_factor': speedupFactor,
        'faster_load_model': fasterLoadModel,
        'load_time_ratio': loadTimeRatio,
        'more_consistent_model': moreConsistentModel,
        'models_agree': modelsAgree,
      },
    };
  }
}
/// Report for a full multi-variant study
class FullStudyReport {
  final List<EfficiencyStats> results;
  final Map<String, dynamic> deviceInfo;
  final int benchmarkRuns;
  final int warmupRuns;
  final DateTime timestamp;

  FullStudyReport({
    required this.results,
    required this.deviceInfo,
    required this.benchmarkRuns,
    required this.warmupRuns,
    required this.timestamp,
  });

  /// Get results filtered by model name
  List<EfficiencyStats> getByModel(String modelName) =>
      results.where((r) => r.modelName == modelName).toList();

  /// Get results filtered by variant
  List<EfficiencyStats> getByVariant(String variant) =>
      results.where((r) => r.modelVariant == variant).toList();

  /// Get results filtered by delegate
  List<EfficiencyStats> getByDelegate(String delegate) =>
      results.where((r) => r.delegateType == delegate).toList();

  /// Find the best (fastest) configuration overall
  EfficiencyStats? get fastestConfig {
    if (results.isEmpty) return null;
    return results.reduce(
        (a, b) => a.meanInferenceMs <= b.meanInferenceMs ? a : b);
  }

  /// Find the smallest model configuration
  EfficiencyStats? get smallestConfig {
    if (results.isEmpty) return null;
    return results
        .reduce((a, b) => a.modelSizeMB <= b.modelSizeMB ? a : b);
  }

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'device_info': deviceInfo,
        'config': {
          'benchmark_runs': benchmarkRuns,
          'warmup_runs': warmupRuns,
        },
        'results': results.map((r) => r.toJson()).toList(),
      };

  /// Generate a summary table string for display
  String get summaryTable {
    final buffer = StringBuffer();
    buffer.writeln(
      'Model           | Variant | Delegate | Mean(ms) | Median(ms) | Size(MB) | RAM(MB)',
    );
    buffer.writeln('-' * 85);
    for (final r in results) {
      final ram = r.peakRamMB?.toStringAsFixed(1) ?? 'N/A';
      buffer.writeln(
        '${r.modelName.padRight(16)}| '
        '${r.modelVariant.padRight(8)}| '
        '${r.delegateType.padRight(9)}| '
        '${r.meanInferenceMs.toStringAsFixed(2).padLeft(8)} | '
        '${r.medianInferenceMs.toStringAsFixed(2).padLeft(10)} | '
        '${r.modelSizeMB.toStringAsFixed(2).padLeft(8)} | '
        '${ram.padLeft(6)}',
      );
    }
    return buffer.toString();
  }
}