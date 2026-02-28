import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:logger/logger.dart';

/// Service for collecting device-level metrics via platform channel.
/// Supports research objective 2.2.3: peak RAM, energy, CPU%, device info.
///
/// Communicates with native Android code via MethodChannel.
class DeviceMetricsService {
  static const _channel = MethodChannel('com.agrisense/device_metrics');
  final Logger _logger = Logger();

  // Cached device info
  Map<String, dynamic>? _deviceInfo;

  /// Get device hardware information (cached after first call)
  Future<Map<String, dynamic>> getDeviceInfo() async {
    if (_deviceInfo != null) return _deviceInfo!;
    try {
      final result = await _channel.invokeMapMethod<String, dynamic>(
        'getDeviceInfo',
      );
      _deviceInfo = result ?? {};
      _logger.i('Device info: $_deviceInfo');
      return _deviceInfo!;
    } on PlatformException catch (e) {
      _logger.w('Platform channel not available for getDeviceInfo: $e');
      return _fallbackDeviceInfo();
    } on MissingPluginException {
      _logger.w('Device metrics plugin not registered, using fallback');
      return _fallbackDeviceInfo();
    }
  }

  /// Get current battery level (0–100), null if unavailable
  Future<double?> getBatteryLevel() async {
    try {
      final level = await _channel.invokeMethod<double>('getBatteryLevel');
      return level;
    } on PlatformException catch (e) {
      _logger.w('getBatteryLevel failed: $e');
      return null;
    } on MissingPluginException {
      return null;
    }
  }

  /// Get peak RAM usage of the app process in MB.
  /// Falls back to Dart-level memory info if native channel unavailable.
  Future<double?> getPeakRamMB() async {
    try {
      final ram = await _channel.invokeMethod<double>('getPeakRamMB');
      return ram;
    } on PlatformException catch (e) {
      _logger.w('getPeakRamMB failed: $e');
      return _getDartMemoryMB();
    } on MissingPluginException {
      return _getDartMemoryMB();
    }
  }

  /// Get current app RSS memory from Dart VM (fallback)
  double? _getDartMemoryMB() {
    try {
      final rss = ProcessInfo.currentRss;
      return rss / (1024 * 1024);
    } catch (_) {
      return null;
    }
  }

  /// Measure energy consumption for a block of work.
  /// Returns battery % consumed (end - start). Null if battery API unavailable.
  ///
  /// Usage:
  /// ```dart
  /// final delta = await deviceMetrics.measureEnergy(() async {
  ///   // run N inferences
  /// });
  /// ```
  Future<double?> measureEnergy(Future<void> Function() work) async {
    final startLevel = await getBatteryLevel();
    if (startLevel == null) return null;

    await work();

    // Small delay for battery reading to settle
    await Future.delayed(const Duration(milliseconds: 200));
    final endLevel = await getBatteryLevel();
    if (endLevel == null) return null;

    final delta = startLevel - endLevel;
    _logger.i('Energy consumed: ${delta.toStringAsFixed(3)}% '
        '(${startLevel.toStringAsFixed(1)}% → ${endLevel.toStringAsFixed(1)}%)');
    return delta;
  }

  /// Reset peak RAM counter (call before a benchmark run)
  Future<void> resetPeakRam() async {
    try {
      await _channel.invokeMethod('resetPeakRam');
    } catch (e) {
      _logger.w('resetPeakRam not available: $e');
    }
  }

  /// Get current CPU usage percentage of the app, null if unavailable
  Future<double?> getCpuUsage() async {
    try {
      final cpu = await _channel.invokeMethod<double>('getCpuUsage');
      return cpu;
    } on PlatformException catch (e) {
      _logger.w('getCpuUsage failed: $e');
      return null;
    } on MissingPluginException {
      return null;
    }
  }

  /// Fallback device info from Dart Platform API
  Map<String, dynamic> _fallbackDeviceInfo() {
    _deviceInfo = {
      'platform': Platform.operatingSystem,
      'os_version': Platform.operatingSystemVersion,
      'dart_version': Platform.version,
      'processors': Platform.numberOfProcessors,
      'note': 'Native channel unavailable – limited info',
    };
    return _deviceInfo!;
  }
}
