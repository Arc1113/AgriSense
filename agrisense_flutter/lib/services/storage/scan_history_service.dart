import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:logger/logger.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/models/prediction_result.dart';

/// Local storage service for scan history
class ScanHistoryService extends ChangeNotifier {
  final Logger _logger = Logger();
  static const String _storageKey = 'scan_history';
  static const int _maxItems = 50;

  List<Map<String, dynamic>> _history = [];

  List<Map<String, dynamic>> get history => List.unmodifiable(_history);
  int get count => _history.length;

  /// Load history from shared preferences
  Future<void> loadHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final data = prefs.getString(_storageKey);
      if (data != null) {
        _history = List<Map<String, dynamic>>.from(
          json.decode(data).map((item) => Map<String, dynamic>.from(item)),
        );
        notifyListeners();
        _logger.i('Loaded ${_history.length} scan history items');
      }
    } catch (e) {
      _logger.e('Failed to load scan history', error: e);
    }
  }

  /// Save a scan result
  Future<void> saveScan({
    required PredictionResult result,
    String? imagePath,
    ModelComparisonResult? comparison,
  }) async {
    try {
      final entry = {
        'id': DateTime.now().millisecondsSinceEpoch.toString(),
        'result': result.toJson(),
        'image_path': imagePath,
        'comparison': comparison != null
            ? {
                'mobilenet': comparison.mobilenetResult.toJson(),
                'resnet': comparison.resnetResult.toJson(),
                'models_agree': comparison.modelsAgree,
              }
            : null,
        'saved_at': DateTime.now().toIso8601String(),
      };

      _history.insert(0, entry);

      // Keep only last N items
      if (_history.length > _maxItems) {
        _history = _history.sublist(0, _maxItems);
      }

      await _persist();
      notifyListeners();
      _logger.i('Scan saved: ${result.disease}');
    } catch (e) {
      _logger.e('Failed to save scan', error: e);
    }
  }

  /// Delete a scan entry
  Future<void> deleteScan(String id) async {
    _history.removeWhere((item) => item['id'] == id);
    await _persist();
    notifyListeners();
  }

  /// Clear all history
  Future<void> clearHistory() async {
    _history.clear();
    await _persist();
    notifyListeners();
  }

  Future<void> _persist() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_storageKey, json.encode(_history));
    } catch (e) {
      _logger.e('Failed to persist scan history', error: e);
    }
  }
}
