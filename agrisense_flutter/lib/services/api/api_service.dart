import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';

import '../../core/constants/app_constants.dart';

/// Service for communicating with the AgriSense backend API.
/// Used as fallback when on-device models aren't available,
/// or to fetch RAG-powered treatment advice.
class ApiService {
  final Logger _logger = Logger();
  final String baseUrl;

  ApiService({String? baseUrl})
      : baseUrl = baseUrl ?? AppConstants.apiBaseUrl;

  /// Health check
  Future<bool> checkHealth() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      _logger.w('Backend not reachable: $e');
      return false;
    }
  }

  /// Send disease detection result to backend for RAG-powered treatment advice.
  /// Disease detection is performed on-device via TFLite; this method sends
  /// the result to the backend to get AI-generated treatment recommendations.
  Future<Map<String, dynamic>> predictFromBackend(
    Uint8List imageBytes, {
    String model = 'mobile',
    String weather = 'Sunny',
    String? disease,
    double? confidence,
    double? latitude,
    double? longitude,
  }) async {
    try {
      // If disease was detected on-device, send JSON request (no image upload needed)
      if (disease != null && confidence != null) {
        final body = {
          'disease': disease,
          'confidence': confidence,
          'model_used': model,
          'weather': weather,
        };

        if (latitude != null && longitude != null) {
          body['latitude'] = latitude;
          body['longitude'] = longitude;
        }

        final response = await http
            .post(
              Uri.parse('$baseUrl/predict'),
              headers: {'Content-Type': 'application/json'},
              body: json.encode(body),
            )
            .timeout(const Duration(seconds: 30));

        if (response.statusCode == 200) {
          return json.decode(response.body);
        } else {
          throw Exception('Backend advice failed: ${response.statusCode}');
        }
      }

      // Fallback: if no on-device result, return error
      throw Exception(
          'Disease name and confidence required. Run on-device detection first.');
    } catch (e) {
      _logger.e('Backend API error', error: e);
      rethrow;
    }
  }

  /// Get treatment advice from the RAG agent via /predict endpoint.
  /// Sends the on-device detection result to get AI-powered advice.
  Future<Map<String, dynamic>> getTreatmentAdvice(
    String disease, {
    String weather = 'Sunny',
    double confidence = 0.9,
    String model = 'mobile',
    double? latitude,
    double? longitude,
  }) async {
    try {
      final body = <String, dynamic>{
        'disease': disease,
        'confidence': confidence,
        'model_used': model,
        'weather': weather,
      };

      if (latitude != null && longitude != null) {
        body['latitude'] = latitude;
        body['longitude'] = longitude;
      }

      final response = await http
          .post(
            Uri.parse('$baseUrl/predict'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Return the advice portion for backward compatibility
        return data['advice'] ?? data;
      } else {
        throw Exception('Failed to get advice: ${response.statusCode}');
      }
    } catch (e) {
      _logger.w('Could not get RAG advice: $e');
      return _getFallbackAdvice(disease);
    }
  }

  /// Fallback advice when backend is unavailable
  Map<String, dynamic> _getFallbackAdvice(String disease) {
    final description = AppConstants.diseaseDescriptions[disease] ??
        'No description available.';
    final severity = AppConstants.diseaseSeverity[disease] ?? 'Unknown';

    return {
      'severity': severity,
      'action_plan':
          'Disease: $disease\n\nDescription: $description\n\n'
              'Please consult a local agricultural extension office for treatment recommendations.\n'
              'Note: This is offline advice. Connect to the internet for AI-powered treatment plans.',
      'safety_warning':
          'Always wear protective equipment when handling pesticides. '
              'Follow label instructions carefully.',
      'weather_advisory':
          'Monitor weather conditions. Avoid spraying during rain or high winds.',
      'sources': [],
      'rag_enabled': false,
    };
  }
}
