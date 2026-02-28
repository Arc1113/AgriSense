import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/models/prediction_result.dart';
import '../../core/theme/app_theme.dart';
import '../../services/api/api_service.dart';
import '../../services/ml/disease_classifier.dart';
import '../../services/storage/scan_history_service.dart';
import '../../services/weather/weather_service.dart';
import '../result/result_screen.dart';

/// Screen that performs disease detection on an image using on-device ML
class DetectionScreen extends StatefulWidget {
  final Uint8List imageBytes;
  final ModelType? initialModelType;

  const DetectionScreen({
    super.key,
    required this.imageBytes,
    this.initialModelType,
  });

  @override
  State<DetectionScreen> createState() => _DetectionScreenState();
}

class _DetectionScreenState extends State<DetectionScreen>
    with TickerProviderStateMixin {
  late AnimationController _ringController;
  PredictionResult? _result;
  Map<String, dynamic>? _advice;
  bool _isAnalyzing = true;
  String _statusText = 'Processing image...';
  int _activeStep = 0;
  String? _error;
  late ModelType _selectedModel;

  @override
  void initState() {
    super.initState();
    _selectedModel = widget.initialModelType ?? ModelType.mobilenet;

    _ringController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();

    _runAnalysis();
  }

  Future<void> _runAnalysis() async {
    try {
      // Step 1: Processing image
      setState(() {
        _activeStep = 0;
        _statusText = 'Processing image...';
      });
      await Future.delayed(const Duration(milliseconds: 500));

      // Step 2: Running AI inference
      setState(() {
        _activeStep = 1;
        _statusText = 'AI Diagnosis...';
      });

      final classifier = context.read<DiseaseClassifier>();
      final result = await classifier.predict(
        widget.imageBytes,
        modelType: _selectedModel,
      );

      setState(() {
        _result = result;
        _activeStep = 2;
        _statusText = 'Generating report...';
      });

      // Step 3: Fetch treatment advice
      try {
        final apiService = context.read<ApiService>();
        final weather = context.read<WeatherService>();
        _advice = await apiService.getTreatmentAdvice(
          result.disease,
          weather: weather.weatherCondition,
        );
      } catch (_) {
        // Use offline fallback advice
        _advice = {
          'severity': AppConstants.diseaseSeverity[result.disease] ?? 'Unknown',
          'action_plan': AppConstants.diseaseDescriptions[result.disease] ??
              'No information available.',
          'safety_warning': 'Wear PPE when applying treatments.',
          'weather_advisory': 'Monitor weather conditions.',
          'rag_enabled': false,
        };
      }

      // Save to history
      context.read<ScanHistoryService>().saveScan(result: result);

      await Future.delayed(const Duration(milliseconds: 500));

      if (!mounted) return;
      setState(() => _isAnalyzing = false);

      // Navigate to results
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => ResultScreen(
            result: result,
            imageBytes: widget.imageBytes,
            advice: _advice ?? {},
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isAnalyzing = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _ringController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FB),
      body: SafeArea(
        child: _error != null
            ? _buildErrorView()
            : _isAnalyzing
                ? _buildLoadingView()
                : _buildLoadingView(),
      ),
    );
  }

  Widget _buildLoadingView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Animated ring
            SizedBox(
              width: 140,
              height: 140,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Background ring
                  Container(
                    width: 140,
                    height: 140,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.grey.shade200,
                        width: 4,
                      ),
                    ),
                  ),
                  // Animated spinner
                  RotationTransition(
                    turns: _ringController,
                    child: const SizedBox(
                      width: 140,
                      height: 140,
                      child: CircularProgressIndicator(
                        strokeWidth: 5,
                        strokeCap: StrokeCap.round,
                        valueColor: AlwaysStoppedAnimation(
                          AppColors.primary,
                        ),
                        backgroundColor: Colors.transparent,
                      ),
                    ),
                  ),
                  // Center icon
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const LinearGradient(
                        colors: [AppColors.primary, AppColors.primaryDark],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.primary.withOpacity(0.4),
                          blurRadius: 20,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.biotech_rounded,
                      color: Colors.white,
                      size: 40,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 40),

            Text(
              _result != null ? 'Analysis Complete' : 'Analyzing Plant',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: Colors.grey.shade800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _statusText,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade500,
                fontWeight: FontWeight.w500,
              ),
            ),

            const SizedBox(height: 40),

            // Progress steps
            _buildStep(0, 'Processing Image'),
            const SizedBox(height: 12),
            _buildStep(1, 'AI Diagnosis'),
            const SizedBox(height: 12),
            _buildStep(2, 'Generating Report'),
          ],
        ),
      ),
    );
  }

  Widget _buildStep(int step, String label) {
    final isDone = _activeStep > step;
    final isCurrent = _activeStep == step;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: isCurrent
            ? AppColors.primary.withOpacity(0.08)
            : isDone
                ? AppColors.primary.withOpacity(0.05)
                : Colors.grey.shade100,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isDone
                  ? AppColors.primary
                  : isCurrent
                      ? Colors.white
                      : Colors.white.withOpacity(0.6),
              border: isCurrent
                  ? Border.all(color: AppColors.primary, width: 2)
                  : null,
              boxShadow: isDone
                  ? [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.3),
                        blurRadius: 8,
                      )
                    ]
                  : null,
            ),
            child: isDone
                ? const Icon(Icons.check, color: Colors.white, size: 18)
                : isCurrent
                    ? Container(
                        margin: const EdgeInsets.all(10),
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.primary,
                        ),
                      )
                    : const SizedBox(),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: isCurrent
                    ? AppColors.primary
                    : isDone
                        ? Colors.grey.shade700
                        : Colors.grey.shade400,
              ),
            ),
          ),
          if (isCurrent)
            SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation(
                  AppColors.primary.withOpacity(0.5),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.error.withOpacity(0.1),
              ),
              child: const Icon(
                Icons.error_outline_rounded,
                color: AppColors.error,
                size: 44,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Analysis Failed',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: Colors.black87,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              _error ?? 'Unknown error occurred',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 32),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Go Back'),
                ),
                const SizedBox(width: 16),
                ElevatedButton(
                  onPressed: () {
                    setState(() {
                      _error = null;
                      _isAnalyzing = true;
                      _activeStep = 0;
                    });
                    _runAnalysis();
                  },
                  child: const Text('Retry'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
