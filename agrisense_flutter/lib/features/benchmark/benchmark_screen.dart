import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../services/ml/device_metrics_service.dart';
import '../../services/ml/disease_classifier.dart';
import '../../services/ml/model_benchmark_service.dart';
import '../../services/ml/test_set_evaluation_service.dart';

/// Benchmark screen: run multiple inference rounds on both models
/// and compare performance statistics for study objective 2.2.3:
/// "Compare computational efficiency by measuring total training time 
/// and the speed of a single diagnosis (inference speed)."
class BenchmarkScreen extends StatefulWidget {
  const BenchmarkScreen({super.key});

  @override
  State<BenchmarkScreen> createState() => _BenchmarkScreenState();
}

class _BenchmarkScreenState extends State<BenchmarkScreen> {
  final ImagePicker _picker = ImagePicker();
  final DeviceMetricsService _deviceMetrics = DeviceMetricsService();
  Uint8List? _imageBytes;
  int _benchmarkRuns = 200;
  bool _showDetailedMetrics = false;
  String _selectedVariant = 'fp32';
  String _selectedDelegate = 'cpu';

  @override
  Widget build(BuildContext context) {
    final benchmarkService = context.watch<ModelBenchmarkService>();
    final classifier = context.watch<DiseaseClassifier>();
    final testSetService = context.watch<TestSetEvaluationService>();
    final isBusy = benchmarkService.isRunning || testSetService.isRunning;

    return Scaffold(
      backgroundColor: AppColors.bgLight,
      appBar: AppBar(
        backgroundColor: AppColors.bgLight,
        title: const Text(
          'Model Benchmark',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      body: Stack(
        children: [
          // Main content
          SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header description
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        AppColors.primary.withOpacity(0.1),
                        AppColors.accent.withOpacity(0.05),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.primary.withOpacity(0.2)),
                  ),
                  child: const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.science_rounded, color: AppColors.primary),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Computational Efficiency Study',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Objective 2.2.3: Compare computational efficiency by measuring '
                        'model load time (training equivalent) and inference speed '
                        '(single diagnosis time) between MobileNetV2 and ResNet50.',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 13,
                          height: 1.5,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 20),

                // Image selection
                GestureDetector(
                  onTap: isBusy ? null : _selectImage,
              child: Container(
                width: double.infinity,
                height: 160,
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: AppColors.primary.withOpacity(0.1),
                    style: _imageBytes == null
                        ? BorderStyle.solid
                        : BorderStyle.none,
                  ),
                ),
                child: _imageBytes == null
                    ? const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_photo_alternate_rounded,
                              size: 40, color: AppColors.textMuted),
                          SizedBox(height: 8),
                          Text(
                            'Tap to select test image',
                            style: TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      )
                    : ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: Image.memory(_imageBytes!, fit: BoxFit.cover,
                            width: double.infinity),
                      ),
              ),
            ),

            const SizedBox(height: 20),

            // Runs slider
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Benchmark Runs',
                        style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '$_benchmarkRuns runs',
                          style: const TextStyle(
                            color: AppColors.primary,
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                  Slider(
                    value: _benchmarkRuns.toDouble(),
                    min: 10,
                    max: 200,
                    divisions: 19,
                    activeColor: AppColors.primary,
                    inactiveColor: AppColors.bgDarker,
                    onChanged: (v) =>
                        setState(() => _benchmarkRuns = v.round()),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Variant & Delegate selectors
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Model Configuration',
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Quantization',
                                style: TextStyle(
                                    color: AppColors.textMuted, fontSize: 12)),
                            const SizedBox(height: 4),
                            SegmentedButton<String>(
                              segments: const [
                                ButtonSegment(value: 'fp32', label: Text('FP32')),
                                ButtonSegment(value: 'float16', label: Text('FP16')),
                                ButtonSegment(value: 'int8', label: Text('INT8')),
                              ],
                              selected: {_selectedVariant},
                              onSelectionChanged: (v) =>
                                  setState(() => _selectedVariant = v.first),
                              style: ButtonStyle(
                                textStyle: WidgetStatePropertyAll(
                                    const TextStyle(fontSize: 12)),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Delegate',
                              style: TextStyle(
                                  color: AppColors.textMuted, fontSize: 12)),
                          const SizedBox(height: 4),
                          SegmentedButton<String>(
                            segments: const [
                              ButtonSegment(value: 'cpu', label: Text('CPU')),
                              ButtonSegment(value: 'nnapi', label: Text('NNAPI')),
                            ],
                            selected: {_selectedDelegate},
                            onSelectionChanged: (v) =>
                                setState(() => _selectedDelegate = v.first),
                            style: ButtonStyle(
                              textStyle: WidgetStatePropertyAll(
                                  const TextStyle(fontSize: 12)),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Start button
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: (_imageBytes != null &&
                        !benchmarkService.isRunning &&
                        classifier.isInitialized)
                    ? () => _runBenchmark(benchmarkService, classifier)
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  disabledBackgroundColor: AppColors.textMuted.withOpacity(0.2),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: benchmarkService.isRunning
                    ? Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            benchmarkService.statusMessage,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      )
                    : const Text(
                        'Run Benchmark',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
              ),
            ),

            // Progress bar
            if (benchmarkService.isRunning) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: benchmarkService.progress,
                  minHeight: 4,
                  backgroundColor: AppColors.bgDarker,
                  valueColor:
                      const AlwaysStoppedAnimation(AppColors.primary),
                ),
              ),
            ],

            if (testSetService.isRunning) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: testSetService.progress,
                  minHeight: 4,
                  backgroundColor: AppColors.bgDarker,
                  valueColor:
                      const AlwaysStoppedAnimation(AppColors.accent),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Test set evaluation: ${testSetService.processedImages}/${testSetService.totalImages}',
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 12,
                ),
              ),
            ],

            // Full Study button
            if (!isBusy && _imageBytes != null && classifier.isInitialized) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: OutlinedButton.icon(
                  onPressed: () => _runFullStudy(benchmarkService, classifier),
                  icon: const Icon(Icons.science_outlined, size: 18),
                  label: const Text('Run Full Study (All Variants)'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.accent,
                    side: const BorderSide(color: AppColors.accent),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                ),
              ),
            ],

            if (!isBusy && classifier.isInitialized) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: OutlinedButton.icon(
                  onPressed: () => _runTestSetEvaluation(classifier),
                  icon: const Icon(Icons.fact_check_outlined, size: 18),
                  label: Text(
                    'Run Test Set Evaluation (${_selectedVariant.toUpperCase()}/${_selectedDelegate.toUpperCase()})',
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.primary,
                    side: const BorderSide(color: AppColors.primary),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                ),
              ),
            ],

            // Results
            if (benchmarkService.lastReport != null && !benchmarkService.isRunning) ...[
              const SizedBox(height: 24),
              _buildReportSection(benchmarkService.lastReport!),
            ],

            // Full study results
            if (benchmarkService.lastStudyReport != null && !benchmarkService.isRunning) ...[
              const SizedBox(height: 24),
              _buildStudyReportSection(benchmarkService),
            ],

            const SizedBox(height: 30),
          ],
        ),
      ),

          // Loading overlay
          if (benchmarkService.isRunning)
            _buildLoadingOverlay(benchmarkService),
        ],
      ),
    );
  }

  Future<void> _runTestSetEvaluation(DiseaseClassifier classifier) async {
    final testSetService = context.read<TestSetEvaluationService>();

    try {
      final root = await testSetService.findTestSetRoot();
      if (root == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Test set not found. Place it in /sdcard/AgriSense/test_set/',
              ),
            ),
          );
        }
        return;
      }

      final sharedFiles = <XFile>[];

      for (final modelType in [ModelType.mobilenet, ModelType.resnet]) {
        await classifier.loadModelVariant(
          modelType,
          variant: _selectedVariant,
          delegate: _selectedDelegate,
        );

        final results = await testSetService.evaluate(
          modelType: modelType,
          testSetRoot: root,
        );

        final jsonPath = await testSetService.exportResults(results);
        final csvPath = await testSetService.exportResultsCsv(results);

        sharedFiles.add(XFile(csvPath));
        sharedFiles.add(XFile(jsonPath));
      }

      await Share.shareXFiles(
        sharedFiles,
        text: 'AgriSense test set evaluation results (${_selectedVariant.toUpperCase()}/${_selectedDelegate.toUpperCase()})',
        subject: 'AgriSense Test Set Evaluation',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Test set evaluation complete for MobileNetV2 + ResNet50 (${_selectedVariant.toUpperCase()}/${_selectedDelegate.toUpperCase()}).',
            ),
            duration: const Duration(seconds: 4),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Test set evaluation failed: $e')),
        );
      }
    }
  }

  Widget _buildLoadingOverlay(ModelBenchmarkService benchmarkService) {
    return Container(
      color: Colors.white.withOpacity(0.95),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Animated benchmark icon
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppColors.primary.withOpacity(0.2),
                      AppColors.accent.withOpacity(0.1),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  shape: BoxShape.circle,
                ),
                child: const Center(
                  child: Icon(
                    Icons.speed_rounded,
                    size: 48,
                    color: AppColors.primary,
                  ),
                ),
              ),
              
              const SizedBox(height: 32),
              
              // Status message
              Text(
                benchmarkService.statusMessage,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
              ),
              
              const SizedBox(height: 24),
              
              // Progress bar with percentage
              SizedBox(
                width: 280,
                child: Column(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: LinearProgressIndicator(
                        value: benchmarkService.progress,
                        minHeight: 10,
                        backgroundColor: AppColors.bgDarker,
                        valueColor: const AlwaysStoppedAnimation(AppColors.primary),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      '${(benchmarkService.progress * 100).toInt()}%',
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Progress details
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.bgDarker,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _buildProgressStep(
                      'MobileNetV2',
                      benchmarkService.progress > 0.5,
                      benchmarkService.progress <= 0.5 && benchmarkService.progress > 0,
                    ),
                    Container(
                      width: 40,
                      height: 2,
                      margin: const EdgeInsets.symmetric(horizontal: 8),
                      color: benchmarkService.progress > 0.5 
                          ? AppColors.primary 
                          : AppColors.textMuted.withOpacity(0.3),
                    ),
                    _buildProgressStep(
                      'ResNet50',
                      benchmarkService.progress >= 1.0,
                      benchmarkService.progress > 0.5 && benchmarkService.progress < 1.0,
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 32),
              
              // Info text
              const Text(
                'Measuring inference speed...\nPlease wait, this may take a moment.',
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 13,
                  height: 1.5,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProgressStep(String label, bool isComplete, bool isActive) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isComplete 
                ? AppColors.success 
                : isActive 
                    ? AppColors.primary 
                    : AppColors.bgDarker,
            border: Border.all(
              color: isComplete || isActive 
                  ? Colors.transparent 
                  : AppColors.textMuted.withOpacity(0.3),
              width: 2,
            ),
          ),
          child: Center(
            child: isComplete 
                ? const Icon(Icons.check, color: Colors.white, size: 18)
                : isActive
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : null,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: TextStyle(
            color: isComplete || isActive ? AppColors.textPrimary : AppColors.textMuted,
            fontSize: 11,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
      ],
    );
  }

  Future<void> _selectImage() async {
    final image = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1024,
      imageQuality: 90,
    );
    if (image == null) return;
    final bytes = await image.readAsBytes();
    setState(() => _imageBytes = bytes);
  }

  Future<void> _runBenchmark(
    ModelBenchmarkService benchmarkService,
    DiseaseClassifier classifier,
  ) async {
    try {
      // Load the selected variant first
      await classifier.loadModelVariant(
        ModelType.mobilenet,
        variant: _selectedVariant,
        delegate: _selectedDelegate,
      );
      await classifier.loadModelVariant(
        ModelType.resnet,
        variant: _selectedVariant,
        delegate: _selectedDelegate,
      );

      await benchmarkService.runBenchmark(
        classifier,
        _imageBytes!,
        warmupRuns: AppConstants.defaultWarmupRuns,
        benchmarkRuns: _benchmarkRuns,
        deviceMetrics: _deviceMetrics,
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Benchmark failed: $e')),
        );
      }
    }
  }

  Future<void> _runFullStudy(
    ModelBenchmarkService benchmarkService,
    DiseaseClassifier classifier,
  ) async {
    try {
      final report = await benchmarkService.runFullStudy(
        classifier,
        _imageBytes!,
        warmupRuns: AppConstants.defaultWarmupRuns,
        benchmarkRuns: _benchmarkRuns,
        deviceMetrics: _deviceMetrics,
      );

      // Auto-export CSV and JSON
      final csvPath = await benchmarkService.exportStudyCsv(report);
      final jsonPath = await benchmarkService.exportStudyJson(report);

      await Share.shareXFiles(
        [XFile(csvPath), XFile(jsonPath)],
        text: 'AgriSense benchmark study results (CSV + JSON)',
        subject: 'AgriSense Benchmark Results',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Study complete! CSV/JSON share sheet opened.'),
            duration: const Duration(seconds: 4),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Full study failed: $e')),
        );
      }
    }
  }

  Widget _buildStudyReportSection(ModelBenchmarkService benchmarkService) {
    final report = benchmarkService.lastStudyReport!;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.accent.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.science_rounded,
                  color: AppColors.accent, size: 18),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Full Study Results',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              IconButton(
                onPressed: () async {
                  final csvPath =
                      await benchmarkService.exportStudyCsv(report);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('CSV: $csvPath')),
                    );
                  }
                },
                icon: const Icon(Icons.table_chart_outlined,
                    color: AppColors.textSecondary, size: 20),
                tooltip: 'Export CSV',
              ),
              IconButton(
                onPressed: () async {
                  final csvPath = await benchmarkService.exportStudyCsv(report);
                  final jsonPath = await benchmarkService.exportStudyJson(report);
                  await Share.shareXFiles(
                    [XFile(csvPath), XFile(jsonPath)],
                    text: 'AgriSense benchmark study results (CSV + JSON)',
                    subject: 'AgriSense Benchmark Results',
                  );
                },
                icon: const Icon(Icons.share_rounded,
                    color: AppColors.textSecondary, size: 20),
                tooltip: 'Share CSV + JSON',
              ),
              IconButton(
                onPressed: () {
                  final json = const JsonEncoder.withIndent('  ')
                      .convert(report.toJson());
                  Clipboard.setData(ClipboardData(text: json));
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                          content: Text('Study JSON copied to clipboard')),
                    );
                  }
                },
                icon: const Icon(Icons.copy_rounded,
                    color: AppColors.textSecondary, size: 20),
                tooltip: 'Copy JSON',
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Summary table
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.bgDarker,
              borderRadius: BorderRadius.circular(8),
            ),
            child: SelectableText(
              report.summaryTable,
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 10,
                fontFamily: 'monospace',
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '${report.results.length} configurations benchmarked, '
            'N=${report.benchmarkRuns} per config',
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
            ),
          ),
          if (report.fastestConfig != null) ...[
            const SizedBox(height: 4),
            Text(
              'Fastest: ${report.fastestConfig!.modelName} '
              '(${report.fastestConfig!.modelVariant}/${report.fastestConfig!.delegateType}) '
              '= ${report.fastestConfig!.meanInferenceMs.toStringAsFixed(2)} ms',
              style: const TextStyle(
                color: AppColors.success,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildReportSection(BenchmarkReport report) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section title with export button
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Study Results',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            Row(
              children: [
                // Toggle detailed view
                IconButton(
                  onPressed: () => setState(() => _showDetailedMetrics = !_showDetailedMetrics),
                  icon: Icon(
                    _showDetailedMetrics ? Icons.visibility_off : Icons.visibility,
                    color: AppColors.textSecondary,
                    size: 20,
                  ),
                  tooltip: _showDetailedMetrics ? 'Hide details' : 'Show details',
                ),
                // Export JSON button
                IconButton(
                  onPressed: () => _exportResults(report),
                  icon: const Icon(Icons.download_rounded, color: AppColors.textSecondary, size: 20),
                  tooltip: 'Copy JSON to clipboard',
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Summary card with key findings
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.primary.withOpacity(0.15),
                AppColors.accent.withOpacity(0.1),
              ],
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Key Findings',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              _buildFindingRow('Faster Inference', report.fasterModel, 
                  '${report.speedupFactor.toStringAsFixed(2)}x faster'),
              _buildFindingRow('Faster Load Time', report.fasterLoadModel,
                  '${report.loadTimeRatio.toStringAsFixed(2)}x faster'),
              _buildFindingRow('More Consistent', report.moreConsistentModel, 
                  'Lower variability'),
              _buildFindingRow('Diagnosis Agreement', 
                  report.modelsAgree ? 'Yes' : 'No',
                  report.modelsAgree ? 'Both models agree' : 'Models disagree'),
            ],
          ),
        ),

        const SizedBox(height: 16),

        // Model Load Time Comparison (Training Time Equivalent)
        _buildLoadTimeCard(report),

        const SizedBox(height: 16),

        // Model comparison cards
        _buildStatsCard('MobileNetV2', report.mobilenetStats,
            report.mobilenetSizeMB, report.mobilenetLoadTimeMs, AppColors.primary),
        const SizedBox(height: 12),
        _buildStatsCard('ResNet50', report.resnetStats, report.resnetSizeMB,
            report.resnetLoadTimeMs, AppColors.accent),

        // Detailed metrics (expandable)
        if (_showDetailedMetrics) ...[
          const SizedBox(height: 16),
          _buildDetailedMetricsCard(report),
        ],
      ],
    );
  }

  Widget _buildFindingRow(String label, String value, String detail) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            detail,
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadTimeCard(BenchmarkReport report) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.primary.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.timer_outlined, color: AppColors.warning, size: 18),
              SizedBox(width: 8),
              Text(
                'Model Load Time (Training Equivalent)',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Time to load model into memory (one-time cost per session)',
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildLoadTimeItem(
                  'MobileNetV2',
                  report.mobilenetLoadTimeMs,
                  AppColors.primary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildLoadTimeItem(
                  'ResNet50',
                  report.resnetLoadTimeMs,
                  AppColors.accent,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLoadTimeItem(String name, double loadTimeMs, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(
            name,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${loadTimeMs.toStringAsFixed(0)} ms',
            style: const TextStyle(
              color: AppColors.textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsCard(
      String name, ModelStats stats, String sizeMB, double loadTimeMs, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  name,
                  style: TextStyle(
                    color: color,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                sizeMB,
                style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 14),
          
          // Key metrics for study (Inference Speed)
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                const Text(
                  'INFERENCE SPEED (Single Diagnosis)',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _buildMetricItem('Mean', stats.formattedMean, color, isHighlight: true),
                    _buildMetricItem('Median', stats.formattedMedian, color),
                    _buildMetricItem('FPS', stats.formattedFPS, color, isHighlight: true),
                  ],
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 12),
          
          // Total diagnosis time
          Row(
            children: [
              _buildStatItem('Preprocess', stats.formattedPreprocessing, color),
              _buildStatItem('Total Dx', stats.formattedTotalDiagnosis, color),
              _buildStatItem('Throughput', stats.formattedThroughput, color),
            ],
          ),
          
          const SizedBox(height: 8),
          
          // Statistical spread
          Row(
            children: [
              _buildStatItem('Min', '${stats.minMs.toStringAsFixed(1)} ms', color),
              _buildStatItem('Max', '${stats.maxMs.toStringAsFixed(1)} ms', color),
              _buildStatItem('Variability', stats.formattedVariability, color),
            ],
          ),
          
          const SizedBox(height: 8),
          
          // Percentiles
          Row(
            children: [
              _buildStatItem('StdDev', '${stats.stdDevMs.toStringAsFixed(1)} ms', color),
              _buildStatItem('P95', stats.formattedP95, color),
              _buildStatItem('P99', stats.formattedP99, color),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricItem(String label, String value, Color color, {bool isHighlight = false}) {
    return Expanded(
      child: Column(
        children: [
          Text(
            label,
            style: TextStyle(
              color: isHighlight ? color : AppColors.textMuted, 
              fontSize: 11,
              fontWeight: isHighlight ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: isHighlight ? 16 : 14,
              fontWeight: isHighlight ? FontWeight.w700 : FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(
            label,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.textPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailedMetricsCard(BenchmarkReport report) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.primary.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.analytics_outlined, color: AppColors.textSecondary, size: 18),
              SizedBox(width: 8),
              Text(
                'Detailed Study Metrics',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          // Study summary text
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.bgDarker,
              borderRadius: BorderRadius.circular(8),
            ),
            child: SelectableText(
              report.studySummary,
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 11,
                fontFamily: 'monospace',
                height: 1.5,
              ),
            ),
          ),
          
          const SizedBox(height: 12),
          
          // Benchmark configuration
          Row(
            children: [
              _buildConfigItem('Warmup Runs', '${report.warmupRuns}'),
              _buildConfigItem('Benchmark Runs', '${report.benchmarkRuns}'),
              _buildConfigItem('Timestamp', _formatTime(report.timestamp)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildConfigItem(String label, String value) {
    return Expanded(
      child: Column(
        children: [
          Text(
            label,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 10),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(DateTime timestamp) {
    return '${timestamp.hour.toString().padLeft(2, '0')}:'
           '${timestamp.minute.toString().padLeft(2, '0')}:'
           '${timestamp.second.toString().padLeft(2, '0')}';
  }

  Future<void> _exportResults(BenchmarkReport report) async {
    try {
      final jsonString = const JsonEncoder.withIndent('  ').convert(report.toJson());
      await Clipboard.setData(ClipboardData(text: jsonString));
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Row(
              children: [
                Icon(Icons.check_circle, color: Colors.white, size: 18),
                SizedBox(width: 8),
                Text('Benchmark data copied to clipboard'),
              ],
            ),
            backgroundColor: AppColors.success,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to export: $e')),
        );
      }
    }
  }
}
