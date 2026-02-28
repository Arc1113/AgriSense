import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';

import '../../services/api/api_service.dart';
import '../../services/esp32/esp32_service.dart';
import '../../services/ml/device_metrics_service.dart';
import '../../services/ml/disease_classifier.dart';
import '../../services/ml/model_benchmark_service.dart';
import '../../services/ml/test_set_evaluation_service.dart';
import '../../services/storage/scan_history_service.dart';
import '../../services/weather/weather_service.dart';

/// All app-level providers
List<SingleChildWidget> get appProviders => [
      // ML Disease Classifier (on-device TFLite)
      ChangeNotifierProvider(create: (_) => DiseaseClassifier()),

      // Model Benchmark Service (compare ResNet vs MobileNet, all variants)
      ChangeNotifierProvider(create: (_) => ModelBenchmarkService()),

      // Device Metrics Service (RAM, battery, CPU via platform channel)
      Provider(create: (_) => DeviceMetricsService()),

      // Test Set Evaluation Service (depends on DiseaseClassifier)
      ChangeNotifierProxyProvider<DiseaseClassifier, TestSetEvaluationService>(
        create: (context) => TestSetEvaluationService(
          classifier: context.read<DiseaseClassifier>(),
        ),
        update: (_, classifier, previous) =>
            previous ?? TestSetEvaluationService(classifier: classifier),
      ),

      // Backend API Service
      Provider(create: (_) => ApiService()),

      // Weather Service
      ChangeNotifierProvider(create: (_) => WeatherService()),

      // Scan History
      ChangeNotifierProvider(create: (_) => ScanHistoryService()),

      // ESP32-CAM Robotics Service
      ChangeNotifierProvider(create: (_) => ESP32Service()),
    ];
