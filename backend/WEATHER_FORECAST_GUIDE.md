# Weather Forecast Integration - Quick Guide

## 🌦️ New Feature: Forecast-Based Treatment Timing

The RAG system now considers weather forecasts when recommending treatment application timing. This is crucial for:
- **Avoiding rain washoff**: Don't apply treatments if rain is expected within 24-48 hours
- **Optimal windows**: Identify 3+ day dry periods for best efficacy
- **Cost savings**: Prevent wasted treatments that get washed away
- **Environmental protection**: Reduce runoff of chemicals into soil/water

---

## API Usage

### Endpoint: POST /predict

**New Parameter:**
- `forecast` (optional): 7-day weather forecast as a string

### Example 1: Simple Forecast

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@tomato_leaf.jpg" \
  -F "model=mobile" \
  -F "weather=Sunny" \
  -F "forecast=Mon: Sunny, Tue: Rain, Wed-Fri: Cloudy, Sat-Sun: Sunny"
```

### Example 2: Detailed Forecast

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@leaf.jpg" \
  -F "weather=Cloudy" \
  -F "forecast=Today: Cloudy, Tomorrow: Heavy Rain, Day 3-4: Light Rain, Day 5-7: Sunny"
```

### Example 3: No Rain Expected (Optimal Window)

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@diseased_leaf.jpg" \
  -F "weather=Sunny" \
  -F "forecast=Entire week: Sunny and dry, no rain expected"
```

---

## Response Examples

### Scenario 1: Rain Expected Soon - DELAY Application

**Request:**
```
weather: "Sunny"
forecast: "Today: Sunny, Tomorrow: Heavy Rain, Day 3-4: Light Rain, Day 5-7: Sunny"
```

**Response:**
```json
{
  "disease": "Early Blight",
  "confidence": 0.94,
  "advice": {
    "severity": "Medium",
    "action_plan": "Do NOT apply treatments today. Heavy rain is forecast for tomorrow which will wash away fungicides. Wait until Day 5-7 when sunny weather is expected, then apply chlorothalonil fungicide.",
    "safety_warning": "Wear PPE including gloves, goggles, long sleeves. Store treatments properly until application window.",
    "weather_advisory": "⚠️ CRITICAL: Rain forecast in 24 hours. Delay all applications until 3+ consecutive dry days (Day 5-7). This will save costs and improve efficacy. Monitor plants for disease progression during wait period.",
    "sources": [
      {"source": "FAO", "content_type": "Treatment", "confidence": 0.89}
    ],
    "rag_enabled": true
  }
}
```

### Scenario 2: No Rain - OPTIMAL Application Window

**Request:**
```
weather: "Sunny"
forecast: "Entire week sunny and dry, no rain expected"
```

**Response:**
```json
{
  "disease": "Late Blight",
  "confidence": 0.91,
  "advice": {
    "severity": "High",
    "action_plan": "OPTIMAL APPLICATION WINDOW: No rain expected for 7+ days. Apply copper fungicide immediately in early morning (6-8 AM). Repeat application in 7 days if no symptoms improve.",
    "safety_warning": "Wear full PPE: gloves, goggles, long sleeves, mask. Copper can irritate skin.",
    "weather_advisory": "✅ EXCELLENT CONDITIONS: Sunny forecast with no rain for entire week. Apply treatments now for maximum efficacy. Fungicides need 24-48 hours to dry and bond to leaves. Early morning application prevents leaf burn.",
    "sources": [
      {"source": "UC IPM", "content_type": "Treatment", "confidence": 0.92},
      {"source": "PCAARRD", "content_type": "Application Timing", "confidence": 0.87}
    ],
    "rag_enabled": true
  }
}
```

### Scenario 3: Mixed Week - Strategic Timing

**Request:**
```
weather: "Cloudy"
forecast: "Mon-Tue: Cloudy, Wed: Rain, Thu-Sun: Sunny"
```

**Response:**
```json
{
  "disease": "Bacterial Spot",
  "confidence": 0.88,
  "advice": {
    "severity": "Medium",
    "action_plan": "Wait until Thursday when rain has passed and sunny weather begins. Apply copper-based bactericide Thursday morning. This gives 4 days of dry weather for treatment to work effectively.",
    "safety_warning": "Wear protective gloves and goggles. Avoid application in windy conditions.",
    "weather_advisory": "⏱️ TIMING STRATEGY: Rain on Wednesday requires waiting. Best application window is Thursday-Friday morning (post-rain, before next potential weather change). Cloudy weather today is acceptable but Thursday offers better drying conditions.",
    "sources": [
      {"source": "FAO", "content_type": "Treatment", "confidence": 0.86}
    ],
    "rag_enabled": true
  }
}
```

---

## Frontend Integration

### JavaScript Example

```javascript
async function predictDisease(imageFile, currentWeather, weekForecast) {
  const formData = new FormData();
  formData.append('file', imageFile);
  formData.append('model', 'mobile');
  formData.append('weather', currentWeather);
  
  // NEW: Add forecast if available
  if (weekForecast) {
    formData.append('forecast', weekForecast);
  }
  
  const response = await fetch('http://localhost:8000/predict', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

// Usage
const forecast = "Mon: Sunny, Tue: Rain, Wed-Sun: Cloudy";
const result = await predictDisease(imageFile, 'Sunny', forecast);

// Display warning if rain is mentioned in weather_advisory
if (result.advice.weather_advisory.includes('rain') || 
    result.advice.weather_advisory.includes('Rain')) {
  showWarningBanner('⚠️ Rain forecast - check timing advice carefully');
}
```

### React Component Example

```jsx
function DiseaseResult({ result }) {
  const hasRainWarning = 
    result.advice.weather_advisory.toLowerCase().includes('rain') ||
    result.advice.weather_advisory.includes('⚠️');
  
  return (
    <div className="result-card">
      <h2>{result.disease}</h2>
      
      {hasRainWarning && (
        <div className="alert alert-warning">
          <strong>⚠️ Weather Advisory:</strong>
          Check forecast before applying treatments
        </div>
      )}
      
      <div className="advice-section">
        <h3>Action Plan</h3>
        <p>{result.advice.action_plan}</p>
      </div>
      
      <div className="weather-section">
        <h3>Weather Considerations</h3>
        <p>{result.advice.weather_advisory}</p>
        
        {/* Highlight optimal windows */}
        {result.advice.weather_advisory.includes('OPTIMAL') && (
          <span className="badge badge-success">
            ✅ Optimal Application Window
          </span>
        )}
      </div>
    </div>
  );
}
```

---

## Weather Forecast Formats (Flexible)

The system accepts various forecast formats:

### Format 1: Day-by-Day
```
"Mon: Sunny, Tue: Rain, Wed: Cloudy, Thu-Sun: Sunny"
```

### Format 2: Relative Days
```
"Today: Sunny, Tomorrow: Rain, Day 3: Cloudy, Day 4-7: Sunny"
```

### Format 3: Descriptive
```
"No rain expected this week. Sunny conditions throughout."
```

### Format 4: Detailed Conditions
```
"Monday 70°F Sunny, Tuesday 65°F Heavy Rain 80% chance, Wednesday 68°F Light Showers, Thursday-Sunday 75°F Clear Skies"
```

**The AI agent will parse and interpret any reasonable format!**

---

## Getting Weather Data

### Option 1: OpenWeatherMap API (Recommended)

```javascript
async function get7DayForecast(lat, lon, apiKey) {
  const url = `https://api.openweathermap.org/data/2.5/forecast?lat=${lat}&lon=${lon}&appid=${apiKey}&units=metric`;
  const response = await fetch(url);
  const data = await response.json();
  
  // Parse forecast into simple format
  const forecast = data.list
    .filter((item, i) => i % 8 === 0) // One per day
    .slice(0, 7)
    .map(day => {
      const date = new Date(day.dt * 1000);
      const dayName = date.toLocaleDateString('en', { weekday: 'short' });
      const weather = day.weather[0].main;
      return `${dayName}: ${weather}`;
    })
    .join(', ');
  
  return forecast;
}

// Usage
const forecast = await get7DayForecast(14.5995, 120.9842, 'your_api_key'); // Manila
// Returns: "Mon: Clear, Tue: Rain, Wed: Clouds, Thu: Clear, Fri: Clear, Sat: Rain, Sun: Clear"
```

### Option 2: User Input

```html
<label>Weather Forecast (Optional):</label>
<input 
  type="text" 
  placeholder="e.g., Mon: Sunny, Tue: Rain, Wed-Sun: Cloudy"
  id="forecast-input"
/>
```

### Option 3: Weather Service Integration

```javascript
// Example: Integrate with local weather service
async function getLocalForecast() {
  // Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA)
  const response = await fetch('https://api.pagasa.dost.gov.ph/forecast');
  const data = await response.json();
  
  // Format for AgriSense
  return formatPAGASAForecast(data);
}
```

---

## Benefits

### 1. **Cost Savings**
- Avoid applying treatments that will be washed away by rain
- Typical fungicide costs: ₱500-1000 per application
- Wasted application = 100% loss + environmental damage

### 2. **Improved Efficacy**
- Treatments need 24-48 hours to dry and bond to leaves
- Rain-free periods ensure maximum effectiveness
- Better disease control with properly timed applications

### 3. **Environmental Protection**
- Prevent chemical runoff into soil and water
- Reduce pesticide/fungicide waste
- Protect beneficial insects and pollinators

### 4. **User Trust**
- Transparent AI reasoning based on weather
- Clear warnings about rain
- Actionable timing recommendations

### 5. **Agricultural Best Practices**
- Aligns with IPM (Integrated Pest Management) principles
- Follows FAO and PCAARRD guidelines
- Professional farm management approach

---

## AI Agent Behavior

The **Field Specialist** agent now:

1. **Analyzes forecast** for rain patterns
2. **Identifies optimal windows** (3+ dry days)
3. **Issues warnings** if rain is imminent
4. **Recommends delays** when appropriate
5. **Suggests specific days** for application
6. **Considers drying time** (24-48 hours)
7. **Optimizes timing** for best efficacy

---

## Testing

### Test Case 1: Rain Tomorrow
```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_early_blight.jpg" \
  -F "weather=Sunny" \
  -F "forecast=Today: Sunny, Tomorrow: Heavy Rain"
```

**Expected:** Should recommend DELAYING application

### Test Case 2: All Week Clear
```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_late_blight.jpg" \
  -F "weather=Sunny" \
  -F "forecast=Entire week: Sunny and dry"
```

**Expected:** Should emphasize OPTIMAL WINDOW and recommend immediate application

### Test Case 3: No Forecast Provided
```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_leaf.jpg" \
  -F "weather=Sunny"
```

**Expected:** Should work normally without forecast-specific advice

---

## Backward Compatibility

✅ **Fully backward compatible**
- `forecast` parameter is optional
- System works without forecast data
- Existing integrations continue to function
- No breaking changes to API

---

## Future Enhancements

Potential additions:
1. ⏰ **Specific hour recommendations** (e.g., "Apply between 6-8 AM Thursday")
2. 🌡️ **Temperature considerations** (avoid extreme heat/cold)
3. 💨 **Wind speed warnings** (spray drift concerns)
4. 🌅 **Sunrise/sunset timing** (optimal application times)
5. 📅 **Calendar integration** (schedule reminders)

---

**Status**: ✅ Forecast integration fully implemented and ready to use!
