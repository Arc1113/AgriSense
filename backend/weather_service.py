"""
Weather Service for AgriSense
Fetches weather forecasts from OpenWeatherMap API

Features:
- 7-day weather forecast
- Current weather conditions
- Automatic formatting for AI agents
- Caching to reduce API calls
- Fallback to default location
"""

import os
import logging
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("WeatherService")


# =============================================================================
# Configuration
# =============================================================================

# Default location: Davao City, Philippines (for when location not provided)
DEFAULT_LAT = 7.0731
DEFAULT_LON = 125.6128
DEFAULT_LOCATION_NAME = "Davao City, Philippines"

# API Configuration - Open-Meteo (Free, No API Key Required)
API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
API_TIMEOUT = 10  # seconds
MAX_DAILY_CALLS = 9500  # Safety limit (Open-Meteo free tier is 10,000/day)
API_USAGE_FILE = Path(__file__).parent / ".weather_api_usage.json"

# Cache configuration
_forecast_cache: Dict[str, Tuple[str, float]] = {}
CACHE_DURATION = 3600  # 1 hour (forecasts don't change much)


# =============================================================================
# Geolocation
# =============================================================================

def geolocate_ip(ip_address: str) -> Optional[Tuple[float, float, str]]:
    """Best-effort geolocation for a public IP. Returns (lat, lon, city)."""
    try:
        # Skip obvious locals
        if ip_address.startswith("127.") or ip_address.startswith("192.168.") or ip_address.startswith("10."):
            return None

        # ipapi.co free endpoint (rate-limited but no key required)
        resp = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=5)
        resp.raise_for_status()
        data = resp.json()

        lat = data.get("latitude")
        lon = data.get("longitude")
        city = data.get("city") or data.get("region") or data.get("country_name")

        if lat is None or lon is None:
            return None

        return float(lat), float(lon), city or "Unknown location"
    except Exception as e:
        logger.debug(f"IP geolocation failed for {ip_address}: {e}")
        return None


# =============================================================================
# API Rate Limiting
# =============================================================================

def load_api_usage() -> Dict[str, Any]:
    """Load API usage data from file"""
    try:
        if API_USAGE_FILE.exists():
            with open(API_USAGE_FILE, 'r') as f:
                data = json.load(f)
                # Check if it's from today
                usage_date = datetime.fromisoformat(data.get('date', '2000-01-01'))
                if usage_date.date() == datetime.now().date():
                    return data
        # Return fresh data for today
        return {
            'date': datetime.now().isoformat(),
            'calls': 0,
            'limit': MAX_DAILY_CALLS  # 950 calls/day (safety buffer)
        }
    except Exception as e:
        logger.warning(f"Could not load API usage data: {e}")
        return {'date': datetime.now().isoformat(), 'calls': 0, 'limit': MAX_DAILY_CALLS}


def save_api_usage(usage_data: Dict[str, Any]) -> None:
    """Save API usage data to file"""
    try:
        with open(API_USAGE_FILE, 'w') as f:
            json.dump(usage_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save API usage data: {e}")


def increment_api_call() -> bool:
    """Increment API call counter and check if within limits. Returns False if limit reached."""
    usage = load_api_usage()
    
    # CRITICAL CHECK: Prevent ANY calls after reaching limit
    if usage['calls'] >= MAX_DAILY_CALLS:
        logger.error(f"🚫 API CALL BLOCKED: Limit reached {usage['calls']}/{MAX_DAILY_CALLS} calls today")
        logger.error(f"   NO API CALL WILL BE MADE. Limit resets at midnight.")
        logger.error(f"   System will use cached data or safe fallbacks.")
        return False  # BLOCK THE CALL
    
    # Increment counter (only if under limit)
    usage['calls'] += 1
    save_api_usage(usage)
    
    # Log warnings at thresholds
    calls_remaining = MAX_DAILY_CALLS - usage['calls']
    
    if usage['calls'] >= MAX_DAILY_CALLS:
        logger.error(f"🚫 LIMIT REACHED: {usage['calls']}/{MAX_DAILY_CALLS} calls. NO MORE API CALLS TODAY.")
    elif usage['calls'] == MAX_DAILY_CALLS - 100:
        logger.warning(f"⚠️ API calls approaching limit: {calls_remaining} calls remaining today")
    elif usage['calls'] == MAX_DAILY_CALLS - 10:
        logger.warning(f"🚨 API calls critically low: {calls_remaining} calls remaining today")
    elif usage['calls'] == MAX_DAILY_CALLS - 1:
        logger.warning(f"⚠️ LAST API CALL available today! Next call will be BLOCKED.")
    elif usage['calls'] % 100 == 0:
        logger.info(f"📊 API usage: {usage['calls']}/{MAX_DAILY_CALLS} calls today ({calls_remaining} remaining)")
    
    return True  # ALLOW THE CALL


def get_api_usage_stats() -> Dict[str, Any]:
    """Get current API usage statistics"""
    usage = load_api_usage()
    return {
        'calls_today': usage['calls'],
        'limit': usage['limit'],
        'remaining': usage['limit'] - usage['calls'],
        'percentage_used': (usage['calls'] / usage['limit'] * 100) if usage['limit'] > 0 else 0,
        'date': usage['date']
    }


def can_make_api_call() -> bool:
    """Check if we can make an API call without incrementing counter (read-only check)"""
    usage = load_api_usage()
    return usage['calls'] < MAX_DAILY_CALLS


# =============================================================================
# Weather Service
# =============================================================================

def get_api_key() -> Optional[str]:
    """Open-Meteo doesn't require an API key - always returns None"""
    return None  # Open-Meteo is completely free, no key needed


def format_forecast_for_agent(forecast_data: Dict[str, Any]) -> str:
    """
    Format Open-Meteo forecast data into a simple string for AI agents.
    
    Args:
        forecast_data: Raw forecast data from Open-Meteo API
        
    Returns:
        Formatted string like "Mon: Sunny, Tue: Rain, Wed: Cloudy, Thu-Fri: Sunny, Sat-Sun: Clear"
    """
    try:
        daily_data = forecast_data.get('daily', {})
        if not daily_data:
            return ""
        
        times = daily_data.get('time', [])
        weather_codes = daily_data.get('weathercode', [])
        precipitation_prob = daily_data.get('precipitation_probability_max', [])
        
        if not times or not weather_codes:
            return ""
        
        # Map WMO weather codes to readable conditions
        weather_map = {
            0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Cloudy",
            45: "Foggy", 48: "Foggy",
            51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
            61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
            71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
            80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
            95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Severe Thunderstorm"
        }
        
        # Build forecast string with today/tomorrow labels
        forecast_parts = []
        today = datetime.now().date()
        for i, (date_str, code) in enumerate(zip(times[:7], weather_codes[:7])):
            dt = datetime.fromisoformat(date_str)
            forecast_date = dt.date() if hasattr(dt, 'date') else dt
            day_name = dt.strftime('%A')  # Full day name (Monday, Tuesday...)
            
            # Add relative label: today, tomorrow, day-after-tomorrow
            days_from_now = (forecast_date - today).days
            if days_from_now == 0:
                day_label = f"{day_name} (today)"
            elif days_from_now == 1:
                day_label = f"{day_name} (tomorrow)"
            elif days_from_now == 2:
                day_label = f"{day_name} (day after tomorrow)"
            else:
                day_label = f"{day_name} ({dt.strftime('%b %d')})"
            
            weather = weather_map.get(code, "Cloudy")
            
            # Add rain probability if available and significant
            if i < len(precipitation_prob) and precipitation_prob[i] > 50:
                weather_str = f"{weather} ({int(precipitation_prob[i])}% rain)"
            else:
                weather_str = weather
            
            forecast_parts.append(f"{day_label}: {weather_str}")
        
        forecast_string = ", ".join(forecast_parts)
        
        logger.info(f"Formatted forecast: {forecast_string[:100]}...")
        return forecast_string
        
    except Exception as e:
        logger.error(f"Error formatting forecast: {e}")
        return ""


def get_current_weather(lat: float, lon: float) -> Optional[str]:
    """
    Get current weather condition from Open-Meteo API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Weather condition string (e.g., "Sunny", "Rainy", "Cloudy")
    """
    try:
        # CRITICAL: Check rate limit before making API call
        if not increment_api_call():
            logger.error("🚫 BLOCKED: Rate limit reached. NO API call made.")
            return "Sunny"  # Safe fallback
        
        # Double-check before actual HTTP request (extra safety)
        if not can_make_api_call():
            logger.error("🚫 BLOCKED: Double-check failed. NO API call made.")
            return "Sunny"  # Safe fallback
        
        # ONLY NOW do we make the actual API call to Open-Meteo
        params = {
            'latitude': lat,
            'longitude': lon,
            'current_weather': 'true'
        }
        
        logger.debug(f"Making API call to: {API_BASE_URL}")
        response = requests.get(API_BASE_URL, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        current = data.get('current_weather', {})
        weather_code = current.get('weathercode', 0)
        
        # Map WMO weather codes to our WeatherCondition enum
        if weather_code == 0 or weather_code == 1:
            return 'Sunny'
        elif weather_code == 2:
            return 'Cloudy'
        elif weather_code == 3:
            return 'Cloudy'
        elif 45 <= weather_code <= 48:
            return 'Humid'
        elif 51 <= weather_code <= 67 or 80 <= weather_code <= 82:
            return 'Rainy'
        elif 71 <= weather_code <= 77 or 85 <= weather_code <= 86:
            return 'Cold'
        elif 95 <= weather_code <= 99:
            return 'Rainy'
        else:
            return 'Cloudy'
        
    except Exception as e:
        logger.error(f"Error fetching current weather: {e}")
        return None


def get_weather_forecast(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get 7-day weather forecast and current conditions.
    
    Args:
        lat: Latitude (optional, defaults to Manila)
        lon: Longitude (optional, defaults to Manila)
        location_name: Location name for logging (optional)
        
    Returns:
        Tuple of (current_weather, forecast_string)
        Example: ("Sunny", "Mon: Sunny, Tue: Rain, Wed: Cloudy...")
    """
    # Use defaults if not provided
    if lat is None or lon is None:
        lat = DEFAULT_LAT
        lon = DEFAULT_LON
        location_name = location_name or DEFAULT_LOCATION_NAME
        logger.info(f"Using default location: {location_name}")
    
    # Check cache
    cache_key = f"{lat:.4f},{lon:.4f}"
    if cache_key in _forecast_cache:
        cached_forecast, cache_time = _forecast_cache[cache_key]
        if time.time() - cache_time < CACHE_DURATION:
            logger.info(f"📦 Using cached forecast for {location_name or cache_key}")
            # Get current weather (no API key needed)
            current = get_current_weather(lat, lon)
            return current, cached_forecast
    
    try:
        logger.info(f"🌤️ Fetching weather forecast for {location_name or f'({lat}, {lon})'}...")
        
        # CRITICAL: Check rate limit before making API call
        if not increment_api_call():
            logger.error("🚫 BLOCKED: Rate limit reached. NO forecast API call made.")
            return None, None
        
        # Double-check before actual HTTP request (extra safety)
        if not can_make_api_call():
            logger.error("🚫 BLOCKED: Double-check failed. NO forecast API call made.")
            return None, None
        
        # ONLY NOW do we make the actual API call to Open-Meteo
        params = {
            'latitude': lat,
            'longitude': lon,
            'current_weather': 'true',
            'daily': 'weathercode,precipitation_probability_max',
            'forecast_days': 7,
            'timezone': 'auto'
        }
        
        logger.debug(f"Making API call to: {API_BASE_URL}")
        response = requests.get(API_BASE_URL, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        forecast_data = response.json()
        
        # Format forecast for AI agent
        forecast_string = format_forecast_for_agent(forecast_data)
        
        if not forecast_string:
            logger.warning("Failed to format forecast data")
            return None, None
        
        # Cache the forecast
        _forecast_cache[cache_key] = (forecast_string, time.time())
        
        # Get current weather from the same response
        current_weather = forecast_data.get('current_weather', {})
        weather_code = current_weather.get('weathercode', 0)
        
        # Map weather code to condition
        if weather_code == 0 or weather_code == 1:
            current_condition = 'Sunny'
        elif weather_code == 2:
            current_condition = 'Cloudy'
        elif weather_code == 3:
            current_condition = 'Cloudy'
        elif 45 <= weather_code <= 48:
            current_condition = 'Humid'
        elif 51 <= weather_code <= 67 or 80 <= weather_code <= 82:
            current_condition = 'Rainy'
        elif 71 <= weather_code <= 77 or 85 <= weather_code <= 86:
            current_condition = 'Cold'
        elif 95 <= weather_code <= 99:
            current_condition = 'Rainy'
        else:
            current_condition = 'Cloudy'
        
        logger.info(f"✅ Weather data retrieved: Current={current_condition}, Forecast={forecast_string[:50]}...")
        
        return current_condition, forecast_string
        
    except requests.Timeout:
        logger.error("⏱️ Weather API request timed out")
        return None, None
    except requests.RequestException as e:
        logger.error(f"❌ Weather API request failed: {e}")
        return None, None
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching weather: {e}")
        return None, None


# Geocoding removed - Open-Meteo works directly with lat/lon
# Users should provide coordinates or use browser geolocation


# =============================================================================
# Test Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Testing Weather Service with Open-Meteo API")
    print("=" * 70)
    
    # Show current API usage
    stats = get_api_usage_stats()
    print(f"\n📊 Current API Usage:")
    print(f"   Calls today: {stats['calls_today']}/{stats['limit']}")
    print(f"   Remaining: {stats['remaining']}")
    print(f"   Usage: {stats['percentage_used']:.1f}%")
    print(f"   Note: Open-Meteo is FREE - no API key needed!")
    
    # Test with default location (Manila)
    print("\n📍 Testing default location (Manila)...")
    current, forecast = get_weather_forecast()
    
    if current and forecast:
        print(f"\n✅ Success!")
        print(f"   Current Weather: {current}")
        print(f"   7-Day Forecast: {forecast[:80]}...")
    else:
        print("\n❌ Failed to fetch weather data")
    
    # Test with custom location (Cebu)
    print("\n📍 Testing custom location (Cebu)...")
    current, forecast = get_weather_forecast(10.3157, 123.8854, "Cebu, Philippines")
    
    if current and forecast:
        print(f"\n✅ Success!")
        print(f"   Current Weather: {current}")
        print(f"   7-Day Forecast: {forecast[:80]}...")
    
    # Show updated API usage
    stats = get_api_usage_stats()
    print(f"\n📊 Updated API Usage:")
    print(f"   Calls today: {stats['calls_today']}/{stats['limit']}")
    print(f"   Remaining: {stats['remaining']}")
    print(f"   Usage: {stats['percentage_used']:.1f}%")
    
    print("\n" + "=" * 70)
    print("✅ Test Complete - Open-Meteo API Working!")
    print("=" * 70)
