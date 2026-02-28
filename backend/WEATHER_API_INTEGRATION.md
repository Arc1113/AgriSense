# 🌤️ Weather API Integration Guide

## Overview

AgriSense now **automatically fetches weather data** before generating treatment advice! The system integrates with OpenWeatherMap API to provide:

- **Current weather conditions** (Sunny, Rainy, Cloudy, etc.)
- **7-day forecast** with rain pattern analysis
- **Optimal treatment timing** based on forecast
- **Automatic fallback** if API unavailable

---

## 🚀 Quick Setup

### 1. Get OpenWeatherMap API Key

1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a **FREE** account
3. Go to **API Keys** section
4. Copy your API key

### 2. Add to Environment

Edit `backend/.env`:

```bash
# Required: Groq API (for AI agents)
GROQ_API_KEY=your_groq_api_key_here

# Optional: OpenWeatherMap API (for automatic weather)
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

## 📡 How It Works

### Automatic Flow

```
User uploads image
       ↓
Backend checks if weather provided
       ↓
   NO? → Fetch from API (OpenWeatherMap)
       ↓
Run disease detection (ML)
       ↓
Generate treatment advice (AI + Weather)
       ↓
Return recommendations with optimal timing
```

### Location Options

1. **User provides coordinates**: Uses exact location
2. **No coordinates**: Defaults to Manila, Philippines (14.5995, 120.9842)
3. **API unavailable**: Falls back to "Sunny" condition

---

## 🔌 API Usage

### Option 1: Automatic Weather (Recommended)

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@leaf.jpg" \
  -F "model=mobile" \
  -F "latitude=14.5995" \
  -F "longitude=120.9842"
```

✅ **Backend automatically**:
- Fetches current weather
- Retrieves 7-day forecast
- Analyzes rain patterns
- Generates timing recommendations

### Option 2: Custom Location

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@leaf.jpg" \
  -F "latitude=10.3157" \  # Cebu City
  -F "longitude=123.8854"
```

### Option 3: Manual Override (If needed)

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@leaf.jpg" \
  -F "weather=Rainy" \
  -F "forecast=Mon: Sunny, Tue: Rain, Wed-Fri: Cloudy"
```

### Option 4: Use Defaults

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@leaf.jpg"
```

Uses Manila as default location.

---

## 📊 Response Format

```json
{
  "success": true,
  "disease": "Late Blight",
  "confidence": 0.94,
  "weather": "Cloudy",
  "advice": {
    "severity": "High",
    "action_plan": "...",
    "weather_advisory": "⚠️ RAIN EXPECTED: Tuesday (2 days). 
                         Optimal treatment window: Monday-Tuesday morning. 
                         Allow 24-48h before rain for best effectiveness...",
    "sources": [
      {
        "source": "FAO",
        "content_type": "Treatment",
        "confidence": 0.92
      }
    ],
    "rag_enabled": true
  }
}
```

---

## 🌍 Supported Locations

### Philippines (Popular)

| City | Latitude | Longitude |
|------|----------|-----------|
| Manila | 14.5995 | 120.9842 |
| Quezon City | 14.6760 | 121.0437 |
| Cebu City | 10.3157 | 123.8854 |
| Davao City | 7.0731 | 125.6128 |
| Baguio City | 16.4023 | 120.5960 |

### Other Countries

Works **worldwide**! Just provide any valid lat/lon coordinates.

---

## 🧪 Testing

### Test Weather Service

```bash
cd backend
python weather_service.py
```

Expected output:
```
==================================================================
🧪 Testing Weather Service
==================================================================

📍 Test 1: Manila, Philippines (default)
   Current: Cloudy
   Forecast: Mon: Clouds, Tue: Rain, Wed-Fri: Clear, Sat-Sun: Clouds (Rain expected)

📍 Test 2: Quezon City, Philippines
   Current: Sunny
   Forecast: Mon-Wed: Clear, Thu: Rain, Fri-Sun: Clouds (Rain expected)

✅ Weather Service Test Complete
==================================================================
```

### Test End-to-End

```bash
# Test with Manila (default)
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_image.jpg"

# Test with Cebu City
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_image.jpg" \
  -F "latitude=10.3157" \
  -F "longitude=123.8854"
```

---

## 🔧 Configuration

### Cache Duration

Weather data is cached for **1 hour** to reduce API calls.

```python
# In weather_service.py
CACHE_DURATION = 3600  # 1 hour
```

### API Timeout

```python
API_TIMEOUT = 10  # seconds
```

### Default Location

```python
DEFAULT_LAT = 14.5995   # Manila
DEFAULT_LON = 120.9842
```

---

## 📝 Logging

The system logs weather operations:

```
2024-02-01 10:30:15 | INFO | Processing image: leaf.jpg (245.3KB)
2024-02-01 10:30:15 | INFO | 🌤️ Auto-fetching weather for (14.5995, 120.9842)...
2024-02-01 10:30:16 | INFO |    ✅ Current weather: Cloudy
2024-02-01 10:30:16 | INFO |    ✅ Forecast retrieved
2024-02-01 10:30:17 | INFO | 🔬 Prediction: Late Blight (94.23%)
2024-02-01 10:30:18 | INFO | 🤖 Generating treatment advice with weather context...
```

---

## ⚠️ Error Handling

### API Key Not Set

```python
# Graceful fallback
logger.warning("⚠️ OPENWEATHER_API_KEY not set - using default 'Sunny'")
return "Sunny", ""
```

### API Request Failed

```python
# Exception handling
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except Exception as e:
    logger.error(f"❌ Weather API error: {e}")
    return "Sunny", ""  # Safe fallback
```

### Invalid Coordinates

```python
# Validation in endpoint
latitude: Optional[float] = Query(
    default=None,
    ge=-90,  # Minimum latitude
    le=90    # Maximum latitude
)
```

---

## 🔐 API Limits

### OpenWeatherMap Free Tier

- **1,000 calls/day**
- **60 calls/minute**
- **Free forever**

### AgriSense Optimization

- **Caching**: 1-hour cache reduces duplicate calls
- **Fallback**: Works without API key
- **Efficient**: Only calls API when needed

---

## 🛠️ Troubleshooting

### Issue: "API key not set"

**Solution**: Add to `.env`:
```bash
OPENWEATHER_API_KEY=your_actual_key_here
```

### Issue: "Weather request timeout"

**Solution**: 
1. Check internet connection
2. Try increasing timeout in `weather_service.py`
3. System will fallback to "Sunny"

### Issue: "Invalid coordinates"

**Solution**: Verify lat/lon:
- Latitude: -90 to 90
- Longitude: -180 to 180

---

## 📖 Related Documentation

- [RAG Setup Guide](RAG_SETUP.md)
- [Weather Forecast Guide](WEATHER_FORECAST_GUIDE.md)
- [Backend README](README_RAG.md)

---

## 💡 Best Practices

1. **Set API key** for production use
2. **Provide coordinates** for accurate local weather
3. **Monitor logs** for API issues
4. **Test fallback** scenarios
5. **Cache is automatic** - no action needed

---

## 🎯 Next Steps

1. ✅ Get OpenWeatherMap API key
2. ✅ Add to `.env` file
3. ✅ Test weather service
4. ✅ Test full prediction flow
5. ✅ Monitor logs for issues

---

## 📞 Support

- API Issues: [OpenWeatherMap Docs](https://openweathermap.org/api)
- Backend Errors: Check logs in terminal
- Integration Help: See [RAG_SETUP.md](RAG_SETUP.md)

**Weather API integration complete!** 🎉
