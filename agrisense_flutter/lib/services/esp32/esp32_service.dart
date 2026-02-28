import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../core/constants/app_constants.dart';

/// State of the ESP32-CAM scanner
enum ScanState {
  idle,
  scanning,
  leafDetected,
  capturing,
  classifying,
  advising,
  resultReady,
  error,
}

/// A single YOLO detection bounding box
class Detection {
  final double x1, y1, x2, y2;
  final double confidence;
  final String className;

  Detection({
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
    required this.confidence,
    this.className = 'Tomato_Leaf',
  });

  factory Detection.fromJson(Map<String, dynamic> json) => Detection(
        x1: (json['x1'] as num).toDouble(),
        y1: (json['y1'] as num).toDouble(),
        x2: (json['x2'] as num).toDouble(),
        y2: (json['y2'] as num).toDouble(),
        confidence: (json['confidence'] as num).toDouble(),
        className: json['class_name'] ?? 'Tomato_Leaf',
      );
}

/// A scan result from YOLO detection + disease classification
class ScanResult {
  final int scanIndex;
  final String? disease;
  final double? confidence;
  final String? model;
  final double? inferenceTimeMs;
  final Map<String, dynamic>? allPredictions;
  final Map<String, dynamic>? advice;
  final String? imageBase64;
  final DateTime timestamp;

  ScanResult({
    required this.scanIndex,
    this.disease,
    this.confidence,
    this.model,
    this.inferenceTimeMs,
    this.allPredictions,
    this.advice,
    this.imageBase64,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  ScanResult copyWith({Map<String, dynamic>? advice}) => ScanResult(
        scanIndex: scanIndex,
        disease: disease,
        confidence: confidence,
        model: model,
        inferenceTimeMs: inferenceTimeMs,
        allPredictions: allPredictions,
        advice: advice ?? this.advice,
        imageBase64: imageBase64,
        timestamp: timestamp,
      );
}

/// ChangeNotifier-based service for ESP32-CAM scanner state management.
///
/// Handles: connection, motor control, auto-scan, WebSocket events.
class ESP32Service extends ChangeNotifier {
  // Connection
  String _esp32Ip = '192.168.1.100';
  int _esp32Port = 80;
  bool _isConnected = false;
  String? _connectionError;

  // Scanner
  ScanState _scanState = ScanState.idle;
  List<Detection> _detections = [];
  final List<ScanResult> _scanResults = [];
  Uint8List? _latestFrame;

  // System status
  bool _yoloLoaded = false;
  bool _visionLoaded = false;

  // Auto-scan config
  String _modelType = 'mobilenet';
  double _detectionConfidence = 0.25;
  int _stepSize = 5;

  // Servo position tracking
  int _panAngle = 90;
  int _tiltAngle = 75;

  // WebSocket
  WebSocketChannel? _wsChannel;
  StreamSubscription? _wsSubscription;

  // Backend URL
  String get _apiBase => AppConstants.defaultApiUrl;

  // === Getters ===
  String get esp32Ip => _esp32Ip;
  int get esp32Port => _esp32Port;
  bool get isConnected => _isConnected;
  String? get connectionError => _connectionError;
  ScanState get scanState => _scanState;
  List<Detection> get detections => _detections;
  List<ScanResult> get scanResults => _scanResults;
  Uint8List? get latestFrame => _latestFrame;
  bool get yoloLoaded => _yoloLoaded;
  bool get visionLoaded => _visionLoaded;
  String get modelType => _modelType;
  double get detectionConfidence => _detectionConfidence;
  int get stepSize => _stepSize;
  int get panAngle => _panAngle;
  int get tiltAngle => _tiltAngle;

  bool get isScanning =>
      _scanState == ScanState.scanning ||
      _scanState == ScanState.leafDetected ||
      _scanState == ScanState.capturing ||
      _scanState == ScanState.classifying ||
      _scanState == ScanState.advising;

  String get scanStateLabel {
    switch (_scanState) {
      case ScanState.idle:
        return 'Idle';
      case ScanState.scanning:
        return 'Scanning...';
      case ScanState.leafDetected:
        return 'Leaf Detected!';
      case ScanState.capturing:
        return 'Capturing...';
      case ScanState.classifying:
        return 'Classifying...';
      case ScanState.advising:
        return 'Getting Advice...';
      case ScanState.resultReady:
        return 'Result Ready';
      case ScanState.error:
        return 'Error';
    }
  }

  // === Setters ===
  set modelType(String v) {
    _modelType = v;
    notifyListeners();
  }

  set detectionConfidence(double v) {
    _detectionConfidence = v;
    notifyListeners();
  }

  set motorSpeed(int v) {
    _stepSize = v;
    notifyListeners();
  }

  set stepSize(int v) {
    _stepSize = v;
    notifyListeners();
  }

  // === Status Check ===
  Future<void> checkStatus() async {
    try {
      final res = await http
          .get(Uri.parse('$_apiBase/esp32/status'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        _isConnected = data['connected'] == true;
        _yoloLoaded = data['yolo_loaded'] == true;
        _visionLoaded = data['vision_engine_loaded'] == true;
        _scanState = _parseScanState(data['scan_state'] ?? 'idle');
        notifyListeners();
      }
    } catch (_) {
      // Backend not reachable
    }
  }

  // === Connection ===
  Future<bool> connect(String ip, {int port = 80}) async {
    _esp32Ip = ip;
    _esp32Port = port;
    _connectionError = null;
    notifyListeners();

    try {
      final res = await http
          .post(
            Uri.parse('$_apiBase/esp32/connect'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'ip_address': ip, 'port': port}),
          )
          .timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        _isConnected = true;
        _connectionError = null;
        _connectWebSocket();
        notifyListeners();
        return true;
      } else {
        final err = jsonDecode(res.body);
        _connectionError = err['detail'] ?? 'Connection failed';
        notifyListeners();
        return false;
      }
    } catch (e) {
      _connectionError = 'Backend not reachable: $e';
      notifyListeners();
      return false;
    }
  }

  Future<void> disconnect() async {
    try {
      await http.post(Uri.parse('$_apiBase/esp32/disconnect'));
    } catch (_) {}
    _isConnected = false;
    _scanState = ScanState.idle;
    _disconnectWebSocket();
    notifyListeners();
  }

  // === Motor Control ===
  Future<void> motorLeft() async {
    if (!_isConnected) return;
    await _postMotorCommand('left');
  }

  Future<void> motorRight() async {
    if (!_isConnected) return;
    await _postMotorCommand('right');
  }

  Future<void> motorStop() async {
    if (!_isConnected) return;
    await _postMotorCommand('stop');
  }

  Future<void> motorUp() async {
    if (!_isConnected) return;
    await _postMotorCommand('up');
  }

  Future<void> motorDown() async {
    if (!_isConnected) return;
    await _postMotorCommand('down');
  }

  Future<void> motorCenter() async {
    if (!_isConnected) return;
    await _postMotorCommand('center');
  }

  Future<void> _postMotorCommand(String direction) async {
    try {
      await http.post(
        Uri.parse('$_apiBase/esp32/motor'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'direction': direction, 'step': _stepSize}),
      );
    } catch (e) {
      debugPrint('Motor command failed: $e');
    }
  }

  // === Auto-Scan ===
  Future<void> startAutoScan() async {
    if (!_isConnected) return;
    _scanResults.clear();
    notifyListeners();

    try {
      final res = await http.post(
        Uri.parse('$_apiBase/esp32/scan/start'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'model_type': _modelType,
          'detection_confidence': _detectionConfidence,
        }),
      );
      if (res.statusCode == 200) {
        _scanState = ScanState.scanning;
        notifyListeners();
      }
    } catch (e) {
      _connectionError = 'Failed to start scan: $e';
      notifyListeners();
    }
  }

  Future<void> stopAutoScan() async {
    try {
      await http.post(Uri.parse('$_apiBase/esp32/scan/stop'));
      _scanState = ScanState.idle;
      notifyListeners();
    } catch (_) {}
  }

  /// Single-shot YOLO detection
  Future<void> singleDetect() async {
    if (!_isConnected) return;
    try {
      final res = await http.post(Uri.parse('$_apiBase/esp32/detect'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        _detections = (data['detections'] as List)
            .map((d) => Detection.fromJson(d))
            .toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Detection failed: $e');
    }
  }

  // === WebSocket ===
  void _connectWebSocket() {
    _disconnectWebSocket();

    final wsUrl = _apiBase.replaceFirst('http', 'ws');
    try {
      _wsChannel = WebSocketChannel.connect(Uri.parse('$wsUrl/ws/scan'));
      _wsSubscription = _wsChannel!.stream.listen(
        _handleWsMessage,
        onError: (e) => debugPrint('WebSocket error: $e'),
        onDone: () => debugPrint('WebSocket closed'),
      );
    } catch (e) {
      debugPrint('WebSocket connection failed: $e');
    }
  }

  void _disconnectWebSocket() {
    _wsSubscription?.cancel();
    _wsSubscription = null;
    _wsChannel?.sink.close();
    _wsChannel = null;
  }

  void _handleWsMessage(dynamic rawData) {
    try {
      final msg = jsonDecode(rawData as String) as Map<String, dynamic>;
      final eventType = msg['event_type'] as String?;
      final data = msg['data'] as Map<String, dynamic>? ?? {};

      switch (eventType) {
        case 'state_change':
          _scanState = _parseScanState(msg['state'] ?? data['state'] ?? 'idle');
          _updatePositionFromData(data);
          break;

        case 'frame':
          final b64 = data['frame_base64'] as String?;
          if (b64 != null) {
            _latestFrame = base64Decode(b64);
          }
          final dets = data['detections'] as List?;
          if (dets != null) {
            _detections = dets.map((d) => Detection.fromJson(d)).toList();
          }
          _updatePositionFromData(data);
          break;

        case 'detection':
          final dets = data['detections'] as List?;
          if (dets != null) {
            _detections = dets.map((d) => Detection.fromJson(d)).toList();
          }
          _updatePositionFromData(data);
          break;

        case 'classification':
          _scanResults.insert(
            0,
            ScanResult(
              scanIndex: data['scan_index'] ?? _scanResults.length + 1,
              disease: data['disease'],
              confidence: (data['confidence'] as num?)?.toDouble(),
              model: data['model'],
              inferenceTimeMs: (data['inference_time_ms'] as num?)?.toDouble(),
              allPredictions: data['all_predictions'],
            ),
          );
          _updatePositionFromData(data);
          break;

        case 'advice':
          if (_scanResults.isNotEmpty) {
            _scanResults[0] = _scanResults[0].copyWith(
              advice: data['advice'] as Map<String, dynamic>?,
            );
          }
          break;

        case 'error':
          _connectionError = data['message'] as String?;
          _scanState = ScanState.error;
          break;
      }
      notifyListeners();
    } catch (e) {
      debugPrint('WS message parse error: $e');
    }
  }

  void _updatePositionFromData(Map<String, dynamic> data) {
    final pos = data['position'] as Map<String, dynamic>?;
    if (pos != null) {
      _panAngle = (pos['pan'] as num?)?.toInt() ?? _panAngle;
      _tiltAngle = (pos['tilt'] as num?)?.toInt() ?? _tiltAngle;
    }
  }

  ScanState _parseScanState(String s) {
    switch (s) {
      case 'scanning':
        return ScanState.scanning;
      case 'leaf_detected':
        return ScanState.leafDetected;
      case 'capturing':
        return ScanState.capturing;
      case 'classifying':
        return ScanState.classifying;
      case 'advising':
        return ScanState.advising;
      case 'result_ready':
        return ScanState.resultReady;
      case 'error':
        return ScanState.error;
      default:
        return ScanState.idle;
    }
  }

  @override
  void dispose() {
    _disconnectWebSocket();
    super.dispose();
  }
}
