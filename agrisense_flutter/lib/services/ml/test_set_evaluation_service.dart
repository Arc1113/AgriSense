import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:logger/logger.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/models/efficiency_metrics.dart';
import '../../core/models/prediction_result.dart';
import 'disease_classifier.dart';

/// Service for evaluating models against a structured test set on device.
/// Supports research objective: on-device classification accuracy measurement.
///
/// Test set layout (on device storage):
/// /sdcard/AgriSense/test_set/
///   manifest.json
///   Tomato___Bacterial_spot/
///     img_001.jpg
///     ...
///   Tomato___Early_blight/
///     ...
class TestSetEvaluationService extends ChangeNotifier {
  final Logger _logger = Logger();
  final DiseaseClassifier _classifier;

  // State
  bool _isRunning = false;
  String? _error;
  double _progress = 0.0; // 0.0 – 1.0
  int _processedImages = 0;
  int _totalImages = 0;

  // Results
  TestSetResults? _lastResults;
  final List<_PredictionRecord> _records = [];

  bool get isRunning => _isRunning;
  String? get error => _error;
  double get progress => _progress;
  int get processedImages => _processedImages;
  int get totalImages => _totalImages;
  TestSetResults? get lastResults => _lastResults;

  TestSetEvaluationService({required DiseaseClassifier classifier})
      : _classifier = classifier;

  /// Discover and return the test set root directory path.
  /// Priority: external storage > app documents.
  Future<String?> findTestSetRoot() async {
    // Primary: /sdcard/AgriSense/test_set/
    final externalPath = '/sdcard/AgriSense/test_set';
    if (await Directory(externalPath).exists()) {
      return externalPath;
    }

    // Fallback: app documents directory
    final docsDir = await getApplicationDocumentsDirectory();
    final altPath = '${docsDir.path}/test_set';
    if (await Directory(altPath).exists()) {
      return altPath;
    }

    return null;
  }

  /// Load manifest.json which maps class folders to expected labels.
  /// If no manifest exists, infer from folder names.
  Future<Map<String, List<File>>> _loadTestImages(String rootPath) async {
    final root = Directory(rootPath);
    final classImageMap = <String, List<File>>{};

    // Try to load manifest
    final manifestFile = File('$rootPath/${AppConstants.testManifestFilename}');
    Map<String, dynamic>? manifest;
    if (await manifestFile.exists()) {
      try {
        manifest = json.decode(await manifestFile.readAsString())
            as Map<String, dynamic>;
        _logger.i('Loaded test manifest: ${manifest.keys.length} classes');
      } catch (e) {
        _logger.w('Failed to parse manifest, inferring from folders: $e');
      }
    }

    // Enumerate class directories
    await for (final entity in root.list()) {
      if (entity is Directory) {
        final folderName = entity.path.split(Platform.pathSeparator).last;
        // Skip hidden or system folders
        if (folderName.startsWith('.')) continue;

        // Resolve class name from manifest or use folder name directly
        final className = manifest != null
            ? (manifest['class_mapping']?[folderName] as String? ?? folderName)
            : folderName;

        // Match folder name to one of the known class names
        final matchedClass = _matchClassName(className);
        if (matchedClass == null) {
          _logger.w('Unknown class folder: $folderName → $className, skipping');
          continue;
        }

        final images = <File>[];
        await for (final file in entity.list()) {
          if (file is File) {
            final ext = file.path.toLowerCase();
            if (ext.endsWith('.jpg') ||
                ext.endsWith('.jpeg') ||
                ext.endsWith('.png')) {
              images.add(file);
            }
          }
        }
        classImageMap[matchedClass] = images;
        _logger.i('  $matchedClass: ${images.length} images');
      }
    }

    return classImageMap;
  }

  /// Match a folder/manifest class name to one of AppConstants.classNames.
  String? _matchClassName(String name) {
    // Direct match
    if (AppConstants.classNames.contains(name)) return name;

    // Normalize: lowercase, replace spaces/dashes/underscores
    final normalized = name.toLowerCase().replaceAll(RegExp(r'[\s\-_]+'), '_');
    for (final cn in AppConstants.classNames) {
      if (cn.toLowerCase().replaceAll(RegExp(r'[\s\-_]+'), '_') == normalized) {
        return cn;
      }
    }

    // Partial / fuzzy match
    for (final cn in AppConstants.classNames) {
      if (normalized.contains(cn.toLowerCase().replaceAll(RegExp(r'[\s\-_]+'), '_')) ||
          cn.toLowerCase().replaceAll(RegExp(r'[\s\-_]+'), '_').contains(normalized)) {
        return cn;
      }
    }
    return null;
  }

  /// Run full test set evaluation for the currently loaded model variant.
  ///
  /// [modelType] – which model to evaluate
  /// [testSetRoot] – path to the root test_set/ folder
  Future<TestSetResults> evaluate({
    required ModelType modelType,
    required String testSetRoot,
  }) async {
    if (_isRunning) {
      throw StateError('Evaluation already in progress');
    }

    _isRunning = true;
    _error = null;
    _progress = 0.0;
    _processedImages = 0;
    _records.clear();
    notifyListeners();

    try {
      // Load images per class
      final classImages = await _loadTestImages(testSetRoot);
      if (classImages.isEmpty) {
        throw Exception('No test images found in $testSetRoot');
      }

      _totalImages = classImages.values.fold(0, (sum, imgs) => sum + imgs.length);
      _logger.i('Starting evaluation: $_totalImages images across ${classImages.length} classes');

      // Run predictions
      for (final entry in classImages.entries) {
        final trueClass = entry.key;
        for (final imageFile in entry.value) {
          try {
            final imageBytes = await imageFile.readAsBytes();
            final result = await _classifier.predict(
              Uint8List.fromList(imageBytes),
              modelType: modelType,
            );
            _records.add(_PredictionRecord(
              trueClass: trueClass,
              predictedClass: result.rawClass,
              confidence: result.confidence,
            ));
          } catch (e) {
            _logger.e('Failed on ${imageFile.path}: $e');
            // Count as wrong prediction with empty class
            _records.add(_PredictionRecord(
              trueClass: trueClass,
              predictedClass: '__error__',
              confidence: 0.0,
            ));
          }

          _processedImages++;
          _progress = _processedImages / _totalImages;
          // Notify at intervals to avoid UI jank
          if (_processedImages % 10 == 0 || _processedImages == _totalImages) {
            notifyListeners();
          }
        }
      }

      // Compute metrics
      final results = _computeResults(modelType);
      _lastResults = results;
      return results;
    } catch (e) {
      _error = 'Evaluation failed: $e';
      _logger.e('Evaluation error', error: e);
      rethrow;
    } finally {
      _isRunning = false;
      notifyListeners();
    }
  }

  /// Compute TestSetResults from prediction records.
  TestSetResults _computeResults(ModelType modelType) {
    final classes = AppConstants.classNames;
    final numClasses = classes.length;
    final classIndex = <String, int>{};
    for (int i = 0; i < numClasses; i++) {
      classIndex[classes[i]] = i;
    }

    // Build confusion matrix
    final cm = List.filled(numClasses * numClasses, 0);
    int correct = 0;

    for (final rec in _records) {
      final trueIdx = classIndex[rec.trueClass];
      final predIdx = classIndex[rec.predictedClass];
      if (trueIdx == null || predIdx == null) continue;
      cm[trueIdx * numClasses + predIdx]++;
      if (trueIdx == predIdx) correct++;
    }

    // Per-class metrics
    final perClass = <ClassMetrics>[];
    for (int i = 0; i < numClasses; i++) {
      int tp = cm[i * numClasses + i];
      int fp = 0;
      int fn = 0;
      int tn = 0;
      for (int j = 0; j < numClasses; j++) {
        if (j != i) {
          fp += cm[j * numClasses + i]; // column i, row != i
          fn += cm[i * numClasses + j]; // row i, col != i
        }
      }
      // TN = total - TP - FP - FN
      tn = _records.length - tp - fp - fn;

      perClass.add(ClassMetrics(
        className: classes[i],
        truePositives: tp,
        falsePositives: fp,
        falseNegatives: fn,
        trueNegatives: tn,
      ));
    }

    return TestSetResults(
      modelName: modelType == ModelType.mobilenet ? 'MobileNetV2' : 'ResNet50',
      modelVariant: _classifier.getActiveVariant(modelType),
      delegateType: _classifier.getActiveDelegate(modelType),
      totalImages: _records.length,
      correctPredictions: correct,
      perClassMetrics: perClass,
      confusionMatrix: cm,
      numClasses: numClasses,
    );
  }

  /// Export evaluation results to JSON file.
  Future<String> exportResults(TestSetResults results) async {
    final docsDir = await getApplicationDocumentsDirectory();
    final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final fileName =
        'test_eval_${results.modelName}_${results.modelVariant}_$timestamp.json';
    final file = File('${docsDir.path}/$fileName');
    
    final jsonStr = const JsonEncoder.withIndent('  ').convert(results.toJson());
    await file.writeAsString(jsonStr);
    _logger.i('Results exported to: ${file.path}');
    return file.path;
  }

  /// Export results as CSV (for research paper tables)
  Future<String> exportResultsCsv(TestSetResults results) async {
    final docsDir = await getApplicationDocumentsDirectory();
    final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final fileName =
        'test_eval_${results.modelName}_${results.modelVariant}_$timestamp.csv';
    final file = File('${docsDir.path}/$fileName');

    final buffer = StringBuffer();
    buffer.writeln('Class,Precision,Recall,F1-Score,Specificity,Support');
    for (final cm in results.perClassMetrics) {
      buffer.writeln(
        '${cm.className},'
        '${cm.precision.toStringAsFixed(4)},'
        '${cm.recall.toStringAsFixed(4)},'
        '${cm.f1Score.toStringAsFixed(4)},'
        '${cm.specificity.toStringAsFixed(4)},'
        '${cm.support}',
      );
    }
    buffer.writeln(
      'Macro Average,'
      '${results.macroPrecision.toStringAsFixed(4)},'
      '${results.macroRecall.toStringAsFixed(4)},'
      '${results.macroF1.toStringAsFixed(4)},'
      '${results.macroSpecificity.toStringAsFixed(4)},'
      '${results.totalImages}',
    );

    await file.writeAsString(buffer.toString());
    _logger.i('CSV exported to: ${file.path}');
    return file.path;
  }
}

/// Internal record of a single prediction for evaluation
class _PredictionRecord {
  final String trueClass;
  final String predictedClass;
  final double confidence;

  _PredictionRecord({
    required this.trueClass,
    required this.predictedClass,
    required this.confidence,
  });
}
