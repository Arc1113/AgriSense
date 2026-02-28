import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass_container.dart';
import '../../services/esp32/esp32_service.dart';

/// ESP32-CAM Robotics Scanner screen with full control panel.
class RoboticsScreen extends StatefulWidget {
  const RoboticsScreen({super.key});

  @override
  State<RoboticsScreen> createState() => _RoboticsScreenState();
}

class _RoboticsScreenState extends State<RoboticsScreen> {
  final TextEditingController _ipController = TextEditingController();
  bool _showResults = true;

  @override
  void initState() {
    super.initState();
    final esp32 = context.read<ESP32Service>();
    _ipController.text = esp32.esp32Ip;
    esp32.checkStatus();
  }

  @override
  void dispose() {
    _ipController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'ESP32 Scanner',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            fontSize: 20,
          ),
        ),
        actions: [
          Consumer<ESP32Service>(
            builder: (context, esp32, _) => Container(
              margin: const EdgeInsets.only(right: 16),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: esp32.isConnected
                    ? AppColors.success.withOpacity(0.1)
                    : AppColors.error.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: esp32.isConnected ? AppColors.success : AppColors.error,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    esp32.isConnected ? 'Connected' : 'Offline',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: esp32.isConnected ? AppColors.success : AppColors.error,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      body: Consumer<ESP32Service>(
        builder: (context, esp32, _) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildConnectionCard(esp32),
                const SizedBox(height: 16),
                _buildLiveFeedCard(esp32),
                const SizedBox(height: 16),
                _buildMotorControlCard(esp32),
                const SizedBox(height: 16),
                _buildAutoScanCard(esp32),
                const SizedBox(height: 16),
                if (esp32.scanResults.isNotEmpty) _buildScanResultsCard(esp32),
              ],
            ),
          );
        },
      ),
    );
  }

  // === Connection Card ===
  Widget _buildConnectionCard(ESP32Service esp32) {
    return GlassContainer(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.wifi_rounded, size: 18, color: AppColors.accent),
              SizedBox(width: 8),
              Text(
                'ESP32-CAM Connection',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _ipController,
                  enabled: !esp32.isConnected,
                  decoration: InputDecoration(
                    labelText: 'IP Address',
                    hintText: '192.168.1.100',
                    isDense: true,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  ),
                  style: const TextStyle(fontSize: 14),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton(
                onPressed: () async {
                  if (esp32.isConnected) {
                    await esp32.disconnect();
                  } else {
                    await esp32.connect(_ipController.text.trim());
                  }
                },
                style: FilledButton.styleFrom(
                  backgroundColor: esp32.isConnected ? AppColors.error : AppColors.primary,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
                child: Text(
                  esp32.isConnected ? 'Disconnect' : 'Connect',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          if (esp32.connectionError != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                esp32.connectionError!,
                style: const TextStyle(color: AppColors.error, fontSize: 12),
              ),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            children: [
              _buildStatusChip('YOLO', esp32.yoloLoaded),
              _buildStatusChip('Disease Models', esp32.visionLoaded),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusChip(String label, bool ready) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: (ready ? AppColors.success : AppColors.error).withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        '$label ${ready ? "Ready" : "N/A"}',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: ready ? AppColors.success : AppColors.error,
        ),
      ),
    );
  }

  // === Live Feed Card ===
  Widget _buildLiveFeedCard(ESP32Service esp32) {
    return GlassContainer(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _scanStateColor(esp32.scanState),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  esp32.scanStateLabel,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                if (esp32.detections.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${esp32.detections.length} leaf${esp32.detections.length != 1 ? 'es' : ''}',
                      style: const TextStyle(fontSize: 11, color: AppColors.success, fontWeight: FontWeight.w600),
                    ),
                  ),
              ],
            ),
          ),

          // Video area
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Container(
              color: Colors.black,
              child: esp32.isConnected
                  ? Stack(
                      fit: StackFit.expand,
                      children: [
                        // Frame display
                        if (esp32.latestFrame != null)
                          Image.memory(
                            esp32.latestFrame!,
                            fit: BoxFit.contain,
                            gaplessPlayback: true,
                          )
                        else
                          const Center(
                            child: CircularProgressIndicator(
                              color: AppColors.accent,
                              strokeWidth: 2,
                            ),
                          ),

                        // Bounding box overlay
                        if (esp32.detections.isNotEmpty)
                          CustomPaint(
                            painter: _BoundingBoxPainter(esp32.detections),
                          ),
                      ],
                    )
                  : const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.videocam_off_rounded, size: 48, color: Colors.white24),
                          SizedBox(height: 8),
                          Text(
                            'Connect ESP32-CAM\nto view live feed',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.white38, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  // === Motor Control Card ===
  Widget _buildMotorControlCard(ESP32Service esp32) {
    return GlassContainer(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Pan-Tilt Control',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
          const SizedBox(height: 16),
          // D-pad layout
          Column(
            children: [
              // Up button
              _buildMotorButton(
                icon: Icons.arrow_upward_rounded,
                onPressed: esp32.isConnected ? () => esp32.motorUp() : null,
              ),
              const SizedBox(height: 8),
              // Left, Center, Right row
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _buildMotorButton(
                    icon: Icons.arrow_back_rounded,
                    onPressed: esp32.isConnected ? () => esp32.motorLeft() : null,
                  ),
                  const SizedBox(width: 8),
                  _buildMotorButton(
                    icon: Icons.radio_button_checked_rounded,
                    onPressed: esp32.isConnected ? () => esp32.motorCenter() : null,
                    color: AppColors.info,
                  ),
                  const SizedBox(width: 8),
                  _buildMotorButton(
                    icon: Icons.arrow_forward_rounded,
                    onPressed: esp32.isConnected ? () => esp32.motorRight() : null,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Down button
              _buildMotorButton(
                icon: Icons.arrow_downward_rounded,
                onPressed: esp32.isConnected ? () => esp32.motorDown() : null,
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Step size slider
          Row(
            children: [
              const Text('Step:', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              Expanded(
                child: Slider(
                  value: esp32.stepSize.toDouble(),
                  min: 1,
                  max: 45,
                  divisions: 44,
                  activeColor: AppColors.primary,
                  label: '${esp32.stepSize}\u00b0',
                  onChanged: (v) => esp32.stepSize = v.round(),
                ),
              ),
              Text('${esp32.stepSize}\u00b0', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
            ],
          ),
          // Position display
          const SizedBox(height: 4),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.info.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'Pan: ${esp32.panAngle}\u00b0  |  Tilt: ${esp32.tiltAngle}\u00b0',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 11, color: AppColors.info, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMotorButton({
    required IconData icon,
    VoidCallback? onPressed,
    Color color = AppColors.primary,
  }) {
    return SizedBox(
      width: 56,
      height: 56,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: color.withOpacity(0.1),
          foregroundColor: color,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          padding: EdgeInsets.zero,
        ),
        child: Icon(icon, size: 28),
      ),
    );
  }

  // === Auto-Scan Card ===
  Widget _buildAutoScanCard(ESP32Service esp32) {
    return GlassContainer(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Auto-Scan',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
          const SizedBox(height: 12),

          // Model selector
          Row(
            children: [
              const Text('Model:', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              const SizedBox(width: 8),
              Expanded(
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'mobilenet', label: Text('MobileNet', style: TextStyle(fontSize: 11))),
                    ButtonSegment(value: 'resnet', label: Text('ResNet50', style: TextStyle(fontSize: 11))),
                  ],
                  selected: {esp32.modelType},
                  onSelectionChanged: esp32.isScanning ? null : (v) => esp32.modelType = v.first,
                  style: const ButtonStyle(
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Confidence slider
          Row(
            children: [
              const Text('Confidence:', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              Expanded(
                child: Slider(
                  value: esp32.detectionConfidence,
                  min: 0.1,
                  max: 1.0,
                  divisions: 18,
                  activeColor: AppColors.primary,
                  label: esp32.detectionConfidence.toStringAsFixed(2),
                  onChanged: esp32.isScanning ? null : (v) => esp32.detectionConfidence = v,
                ),
              ),
              Text(
                esp32.detectionConfidence.toStringAsFixed(2),
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Action buttons
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: !esp32.isConnected || !esp32.yoloLoaded
                      ? null
                      : esp32.isScanning
                          ? () => esp32.stopAutoScan()
                          : () => esp32.startAutoScan(),
                  icon: Icon(esp32.isScanning ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 20),
                  label: Text(
                    esp32.isScanning ? 'Stop Scan' : 'Start Scan',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                  style: FilledButton.styleFrom(
                    backgroundColor: esp32.isScanning ? AppColors.error : AppColors.primary,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                height: 44,
                child: OutlinedButton(
                  onPressed: !esp32.isConnected || !esp32.yoloLoaded || esp32.isScanning
                      ? null
                      : () => esp32.singleDetect(),
                  style: OutlinedButton.styleFrom(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Detect', style: TextStyle(fontSize: 13)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // === Scan Results Card ===
  Widget _buildScanResultsCard(ESP32Service esp32) {
    return GlassContainer(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.assignment_rounded, size: 18, color: AppColors.accent),
              const SizedBox(width: 8),
              Text(
                'Scan Results (${esp32.scanResults.length})',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
              ),
              const Spacer(),
              IconButton(
                icon: Icon(
                  _showResults ? Icons.expand_less : Icons.expand_more,
                  size: 20,
                ),
                onPressed: () => setState(() => _showResults = !_showResults),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
          if (_showResults) ...[
            const SizedBox(height: 8),
            ...esp32.scanResults.map((result) => _buildResultItem(result)),
          ],
        ],
      ),
    );
  }

  Widget _buildResultItem(ScanResult result) {
    final isHealthy = result.disease?.toLowerCase() == 'healthy';
    final statusColor = isHealthy ? AppColors.success : AppColors.error;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isHealthy ? Icons.eco_rounded : Icons.bug_report_rounded,
                size: 16,
                color: statusColor,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  result.disease ?? 'Unknown',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: statusColor),
                ),
              ),
              if (result.confidence != null)
                Text(
                  '${(result.confidence! * 100).toStringAsFixed(1)}%',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                ),
            ],
          ),

          if (result.confidence != null) ...[
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: result.confidence!,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation(statusColor),
                minHeight: 4,
              ),
            ),
          ],

          const SizedBox(height: 4),
          Text(
            '${result.model == "mobilenet" ? "MobileNetV2" : "ResNet50"} | Scan #${result.scanIndex}'
            '${result.inferenceTimeMs != null ? " | ${result.inferenceTimeMs!.toStringAsFixed(0)}ms" : ""}',
            style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),

          // Advice section
          if (result.advice != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.info.withOpacity(0.05),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Action: ${result.advice!['action_plan'] ?? 'N/A'}',
                    style: const TextStyle(fontSize: 11, height: 1.4),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (result.advice!['severity'] != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                          color: _severityColor(result.advice!['severity']).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '${result.advice!['severity']} Severity',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: _severityColor(result.advice!['severity']),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _scanStateColor(ScanState state) {
    switch (state) {
      case ScanState.idle:
        return Colors.grey;
      case ScanState.scanning:
        return AppColors.success;
      case ScanState.leafDetected:
        return AppColors.warning;
      case ScanState.capturing:
        return AppColors.info;
      case ScanState.classifying:
        return Colors.purple;
      case ScanState.advising:
        return Colors.indigo;
      case ScanState.resultReady:
        return AppColors.success;
      case ScanState.error:
        return AppColors.error;
    }
  }

  Color _severityColor(String? severity) {
    switch (severity) {
      case 'High':
        return AppColors.error;
      case 'Medium':
        return AppColors.warning;
      case 'Low':
        return AppColors.success;
      default:
        return AppColors.textSecondary;
    }
  }
}

/// Custom painter for drawing YOLO bounding boxes on the live feed.
class _BoundingBoxPainter extends CustomPainter {
  final List<Detection> detections;

  _BoundingBoxPainter(this.detections);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.success
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    final textPainter = TextPainter(textDirection: TextDirection.ltr);

    // Assume 640x480 source image for scaling
    const srcW = 640.0;
    const srcH = 480.0;
    final scaleX = size.width / srcW;
    final scaleY = size.height / srcH;

    for (final det in detections) {
      final rect = Rect.fromLTRB(
        det.x1 * scaleX,
        det.y1 * scaleY,
        det.x2 * scaleX,
        det.y2 * scaleY,
      );
      canvas.drawRect(rect, paint);

      // Draw label
      final label = '${(det.confidence * 100).toStringAsFixed(0)}%';
      textPainter.text = TextSpan(
        text: label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.bold,
          backgroundColor: AppColors.success,
        ),
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(rect.left + 2, rect.top - 16));
    }
  }

  @override
  bool shouldRepaint(covariant _BoundingBoxPainter oldDelegate) =>
      oldDelegate.detections != detections;
}
