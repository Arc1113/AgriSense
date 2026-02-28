import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/models/prediction_result.dart';
import '../../core/theme/app_theme.dart';
import '../../services/ml/disease_classifier.dart';
import '../../services/storage/scan_history_service.dart';

/// Side-by-side comparison of MobileNetV2 vs ResNet50 on the same image.
/// This is the key feature for evaluating whether ResNet can run on mobile.
class ComparisonScreen extends StatefulWidget {
  final Uint8List imageBytes;

  const ComparisonScreen({super.key, required this.imageBytes});

  @override
  State<ComparisonScreen> createState() => _ComparisonScreenState();
}

class _ComparisonScreenState extends State<ComparisonScreen> {
  ModelComparisonResult? _comparison;
  bool _isLoading = true;
  String _statusText = 'Running MobileNetV2...';
  String? _error;

  @override
  void initState() {
    super.initState();
    _runComparison();
  }

  Future<void> _runComparison() async {
    try {
      final classifier = context.read<DiseaseClassifier>();

      setState(() {
        _isLoading = true;
        _statusText = 'Running MobileNetV2...';
      });

      await Future.delayed(const Duration(milliseconds: 300));

      setState(() => _statusText = 'Running ResNet50...');

      final comparison = await classifier.compareModels(widget.imageBytes);

      // Save to history
      context.read<ScanHistoryService>().saveScan(
            result: comparison.mobilenetResult,
            comparison: comparison,
          );

      if (!mounted) return;
      setState(() {
        _comparison = comparison;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgLight,
      appBar: AppBar(
        backgroundColor: AppColors.bgLight,
        title: const Text(
          'Model Comparison',
          style: TextStyle(fontWeight: FontWeight.w600, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _isLoading
          ? _buildLoading()
          : _error != null
              ? _buildError()
              : _buildResults(),
    );
  }

  Widget _buildLoading() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Preview image
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: SizedBox(
              width: 160,
              height: 160,
              child: Image.memory(widget.imageBytes, fit: BoxFit.cover),
            ),
          ),
          const SizedBox(height: 32),
          const CircularProgressIndicator(color: AppColors.primary),
          const SizedBox(height: 20),
          Text(
            _statusText,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Comparing both models on same image',
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 56),
            const SizedBox(height: 16),
            const Text(
              'Comparison Failed',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _error = null;
                  _isLoading = true;
                });
                _runComparison();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResults() {
    final comp = _comparison!;
    final mobile = comp.mobilenetResult;
    final resnet = comp.resnetResult;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Image preview
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: SizedBox(
              height: 180,
              width: double.infinity,
              child: Image.memory(widget.imageBytes, fit: BoxFit.cover),
            ),
          ),

          const SizedBox(height: 20),

          // Agreement status
          _buildAgreementBanner(comp),

          const SizedBox(height: 20),

          // Side-by-side comparison cards
          Row(
            children: [
              Expanded(child: _buildModelCard(mobile, AppColors.primary, 'MobileNetV2')),
              const SizedBox(width: 12),
              Expanded(child: _buildModelCard(resnet, AppColors.accent, 'ResNet50')),
            ],
          ),

          const SizedBox(height: 20),

          // Performance comparison
          _buildPerformanceCard(comp),

          const SizedBox(height: 20),

          // Verdict card
          _buildVerdictCard(comp),

          const SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _buildAgreementBanner(ModelComparisonResult comp) {
    final agree = comp.modelsAgree;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: (agree ? AppColors.success : AppColors.warning).withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: (agree ? AppColors.success : AppColors.warning).withOpacity(0.2),
        ),
      ),
      child: Row(
        children: [
          Icon(
            agree ? Icons.check_circle_rounded : Icons.warning_rounded,
            color: agree ? AppColors.success : AppColors.warning,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  agree ? 'Models Agree ✓' : 'Models Disagree ⚠',
                  style: TextStyle(
                    color: agree ? AppColors.success : AppColors.warning,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  agree
                      ? 'Both models identified the same disease'
                      : 'Models gave different diagnoses — review carefully',
                  style: TextStyle(
                    color: (agree ? AppColors.success : AppColors.warning)
                        .withOpacity(0.8),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModelCard(
      PredictionResult result, Color color, String modelName) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Model name badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              modelName,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Disease name
          Text(
            result.disease,
            style: const TextStyle(
              color: AppColors.textPrimary,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 8),

          // Confidence
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: result.confidence,
                    minHeight: 6,
                    backgroundColor: AppColors.bgDarker,
                    valueColor: AlwaysStoppedAnimation(color),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${(result.confidence * 100).toStringAsFixed(1)}%',
                style: TextStyle(
                  color: color,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Inference time
          Row(
            children: [
              const Icon(Icons.timer_outlined, size: 14, color: AppColors.textMuted),
              const SizedBox(width: 4),
              Text(
                '${result.inferenceTimeMs.toStringAsFixed(1)} ms',
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceCard(ModelComparisonResult comp) {
    final mobile = comp.mobilenetResult;
    final resnet = comp.resnetResult;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Performance Comparison',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 16),

          _buildComparisonRow(
            'Inference Speed',
            '${mobile.inferenceTimeMs.toStringAsFixed(1)} ms',
            '${resnet.inferenceTimeMs.toStringAsFixed(1)} ms',
            mobile.inferenceTimeMs <= resnet.inferenceTimeMs,
          ),
          const SizedBox(height: 12),
          _buildComparisonRow(
            'Confidence',
            '${(mobile.confidence * 100).toStringAsFixed(1)}%',
            '${(resnet.confidence * 100).toStringAsFixed(1)}%',
            mobile.confidence >= resnet.confidence,
          ),
          const SizedBox(height: 12),
          _buildComparisonRow(
            'Speed Difference',
            '',
            '',
            true,
            customValue:
                '${comp.speedDifferenceMs.abs().toStringAsFixed(1)} ms ${comp.fasterModel == "MobileNetV2" ? "(MobileNet faster)" : "(ResNet faster)"}',
          ),
        ],
      ),
    );
  }

  Widget _buildComparisonRow(
    String label,
    String mobileValue,
    String resnetValue,
    bool mobileWins, {
    String? customValue,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
        ),
        const SizedBox(height: 6),
        if (customValue != null)
          Text(
            customValue,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          )
        else
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: mobileWins
                        ? AppColors.primary.withOpacity(0.1)
                        : AppColors.bgDarker,
                    borderRadius: BorderRadius.circular(8),
                    border: mobileWins
                        ? Border.all(
                            color: AppColors.primary.withOpacity(0.3))
                        : null,
                  ),
                  child: Text(
                    mobileValue,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: mobileWins ? AppColors.primary : AppColors.textMuted,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Text('vs',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
              ),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: !mobileWins
                        ? AppColors.accent.withOpacity(0.1)
                        : AppColors.bgDarker,
                    borderRadius: BorderRadius.circular(8),
                    border: !mobileWins
                        ? Border.all(
                            color: AppColors.accent.withOpacity(0.3))
                        : null,
                  ),
                  child: Text(
                    resnetValue,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: !mobileWins ? AppColors.accent : AppColors.textMuted,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            ],
          ),
      ],
    );
  }

  Widget _buildVerdictCard(ModelComparisonResult comp) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.primary.withOpacity(0.15),
            AppColors.accent.withOpacity(0.1),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.insights_rounded, color: AppColors.primary),
              SizedBox(width: 8),
              Text(
                'Verdict',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _getVerdictText(comp),
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 14,
              height: 1.6,
            ),
          ),
        ],
      ),
    );
  }

  String _getVerdictText(ModelComparisonResult comp) {
    final speedDiff = comp.speedDifferenceMs.abs();
    final faster = comp.fasterModel;
    final confDiff =
        ((comp.mobilenetResult.confidence - comp.resnetResult.confidence) * 100)
            .abs();

    String verdict = '';

    if (comp.modelsAgree) {
      verdict +=
          '✅ Both models agree on "${comp.mobilenetResult.disease}" — high confidence diagnosis.\n\n';
    } else {
      verdict +=
          '⚠️ Models disagree: MobileNetV2 says "${comp.mobilenetResult.disease}" while ResNet50 says "${comp.resnetResult.disease}" (confidence diff: ${confDiff.toStringAsFixed(1)}%). Consider a second opinion.\n\n';
    }

    verdict +=
        '⚡ $faster is ${speedDiff.toStringAsFixed(1)} ms faster.\n\n';

    if (comp.mobilenetResult.inferenceTimeMs < 100) {
      verdict += '📱 MobileNetV2 runs smoothly on this device (${comp.mobilenetResult.inferenceTimeMs.toStringAsFixed(0)} ms).\n';
    }

    if (comp.resnetResult.inferenceTimeMs < 200) {
      verdict += '📱 ResNet50 is also viable on this device (${comp.resnetResult.inferenceTimeMs.toStringAsFixed(0)} ms).\n';
    } else if (comp.resnetResult.inferenceTimeMs < 500) {
      verdict += '⏳ ResNet50 is usable but slower on mobile (${comp.resnetResult.inferenceTimeMs.toStringAsFixed(0)} ms).\n';
    } else {
      verdict += '🐌 ResNet50 may be too slow for real-time mobile use (${comp.resnetResult.inferenceTimeMs.toStringAsFixed(0)} ms).\n';
    }

    return verdict;
  }
}
