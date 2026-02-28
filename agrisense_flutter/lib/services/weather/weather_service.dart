import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';

import '../../core/constants/app_constants.dart';

/// Weather service that fetches forecasts from Open-Meteo (free, no API key)
class WeatherService extends ChangeNotifier {
  final Logger _logger = Logger();

  Map<String, dynamic>? _currentWeather;
  bool _isLoading = false;
  String? _error;
  DateTime? _lastFetched;

  Map<String, dynamic>? get currentWeather => _currentWeather;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Get a summary weather condition string for the AI
  String get weatherCondition {
    if (_currentWeather == null) return 'Sunny'; // Default fallback
    final temp = _currentWeather!['temperature'] as double? ?? 25;
    final humidity = _currentWeather!['humidity'] as int? ?? 50;
    final rain = _currentWeather!['precipitation'] as double? ?? 0;

    if (rain > 1) return 'Rainy';
    if (humidity > 80) return 'Humid';
    if (temp > 35) return 'Hot';
    if (temp < 15) return 'Cold';
    if (humidity < 40) return 'Sunny';
    return 'Cloudy';
  }

  /// Fetch current weather from Open-Meteo
  Future<void> fetchWeather({
    double lat = AppConstants.defaultLat,
    double lon = AppConstants.defaultLon,
  }) async {
    // Cache for 1 hour
    if (_lastFetched != null &&
        DateTime.now().difference(_lastFetched!).inMinutes < 60 &&
        _currentWeather != null) {
      return;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final url = Uri.parse(
        'https://api.open-meteo.com/v1/forecast'
        '?latitude=$lat&longitude=$lon'
        '&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code'
        '&daily=temperature_2m_max,temperature_2m_min,precipitation_sum'
        '&timezone=auto&forecast_days=7',
      );

      final response =
          await http.get(url).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final current = data['current'];

        _currentWeather = {
          'temperature': current['temperature_2m'],
          'humidity': current['relative_humidity_2m'],
          'precipitation': current['precipitation'],
          'wind_speed': current['wind_speed_10m'],
          'weather_code': current['weather_code'],
          'daily': data['daily'],
        };

        _lastFetched = DateTime.now();
        _logger.i('Weather fetched: ${_currentWeather!['temperature']}°C');
      } else {
        throw Exception('Weather API error: ${response.statusCode}');
      }
    } catch (e) {
      _error = 'Unable to fetch weather: $e';
      _logger.w('Weather fetch failed', error: e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Get weather description from WMO code
  String getWeatherDescription(int code) {
    const descriptions = {
      0: 'Clear sky',
      1: 'Mainly clear',
      2: 'Partly cloudy',
      3: 'Overcast',
      45: 'Foggy',
      48: 'Rime fog',
      51: 'Light drizzle',
      53: 'Moderate drizzle',
      55: 'Dense drizzle',
      61: 'Slight rain',
      63: 'Moderate rain',
      65: 'Heavy rain',
      71: 'Slight snow',
      73: 'Moderate snow',
      75: 'Heavy snow',
      80: 'Slight rain showers',
      81: 'Moderate rain showers',
      82: 'Violent rain showers',
      95: 'Thunderstorm',
      96: 'Thunderstorm with hail',
    };
    return descriptions[code] ?? 'Unknown';
  }
}
