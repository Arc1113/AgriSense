# 🌐 Frontend Weather Integration Guide

## Overview

This guide shows how to integrate automatic weather fetching in the AgriSense frontend to leverage the new backend weather API.

---

## 🎯 Quick Start

### Option 1: Auto-fetch with Geolocation (Recommended)

```javascript
// Get user's location and send to backend
async function predictWithLocation(imageFile) {
  // Get user's location
  const position = await getCurrentPosition();
  
  const formData = new FormData();
  formData.append('file', imageFile);
  formData.append('model', 'mobile');
  formData.append('latitude', position.coords.latitude);
  formData.append('longitude', position.coords.longitude);
  
  const response = await fetch('http://localhost:8000/predict', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported'));
      return;
    }
    
    navigator.geolocation.getCurrentPosition(resolve, reject);
  });
}
```

### Option 2: Use Default Location (Manila)

```javascript
// Let backend use default Manila location
async function predictWithDefaults(imageFile) {
  const formData = new FormData();
  formData.append('file', imageFile);
  formData.append('model', 'mobile');
  // No latitude/longitude - backend uses Manila
  
  const response = await fetch('http://localhost:8000/predict', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
```

---

## 📍 Location Detection

### Browser Geolocation API

```javascript
async function getLocation() {
  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0
      });
    });
    
    return {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy
    };
  } catch (error) {
    console.error('Location error:', error.message);
    // Fallback to default (Manila)
    return {
      latitude: 14.5995,
      longitude: 120.9842,
      accuracy: null,
      isDefault: true
    };
  }
}
```

### Location Permission Handling

```javascript
async function requestLocationPermission() {
  try {
    const permission = await navigator.permissions.query({ name: 'geolocation' });
    
    if (permission.state === 'granted') {
      console.log('✅ Location permission granted');
      return true;
    } else if (permission.state === 'prompt') {
      console.log('📍 Requesting location permission...');
      // Permission will be requested when getCurrentPosition is called
      return true;
    } else {
      console.log('❌ Location permission denied');
      return false;
    }
  } catch (error) {
    console.error('Permission check error:', error);
    return false;
  }
}
```

---

## 🎨 UI Components

### Location Button

```jsx
// React component
import { useState } from 'react';

function LocationButton({ onLocationUpdate }) {
  const [loading, setLoading] = useState(false);
  const [location, setLocation] = useState(null);
  
  const handleGetLocation = async () => {
    setLoading(true);
    try {
      const pos = await getLocation();
      setLocation(pos);
      onLocationUpdate(pos);
      
      if (pos.isDefault) {
        alert('Using default location: Manila, Philippines');
      } else {
        alert(`Location detected: ${pos.latitude.toFixed(4)}, ${pos.longitude.toFixed(4)}`);
      }
    } catch (error) {
      alert('Could not get location. Using Manila as default.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <button onClick={handleGetLocation} disabled={loading}>
      {loading ? '📍 Getting location...' : '📍 Use My Location'}
    </button>
  );
}
```

### Location Display

```jsx
function LocationDisplay({ latitude, longitude }) {
  if (!latitude || !longitude) {
    return <p>📍 Using default: Manila, Philippines</p>;
  }
  
  return (
    <div>
      <p>📍 Location: {latitude.toFixed(4)}, {longitude.toFixed(4)}</p>
      <a 
        href={`https://www.google.com/maps?q=${latitude},${longitude}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        View on map →
      </a>
    </div>
  );
}
```

---

## 🔄 Complete Prediction Flow

### React Example

```jsx
import { useState } from 'react';

function DiseasePrediction() {
  const [image, setImage] = useState(null);
  const [location, setLocation] = useState({ latitude: null, longitude: null });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleImageUpload = (e) => {
    setImage(e.target.files[0]);
  };
  
  const handleLocationDetect = async () => {
    try {
      const pos = await getLocation();
      setLocation({
        latitude: pos.latitude,
        longitude: pos.longitude
      });
    } catch (error) {
      console.error('Location error:', error);
      // Use defaults
      setLocation({
        latitude: 14.5995,
        longitude: 120.9842
      });
    }
  };
  
  const handlePredict = async () => {
    if (!image) {
      alert('Please select an image');
      return;
    }
    
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', image);
      formData.append('model', 'mobile');
      
      // Add location if available
      if (location.latitude && location.longitude) {
        formData.append('latitude', location.latitude);
        formData.append('longitude', location.longitude);
      }
      
      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Prediction error:', error);
      alert('Prediction failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <h2>🌱 Tomato Disease Detection</h2>
      
      {/* Image Upload */}
      <div>
        <label>Upload Image:</label>
        <input type="file" accept="image/*" onChange={handleImageUpload} />
      </div>
      
      {/* Location */}
      <div>
        <button onClick={handleLocationDetect}>📍 Detect My Location</button>
        {location.latitude && (
          <p>Location: {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</p>
        )}
      </div>
      
      {/* Predict Button */}
      <button onClick={handlePredict} disabled={loading || !image}>
        {loading ? '🔬 Analyzing...' : '🔬 Predict Disease'}
      </button>
      
      {/* Results */}
      {result && (
        <div>
          <h3>Results</h3>
          <p><strong>Disease:</strong> {result.disease}</p>
          <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(1)}%</p>
          <p><strong>Weather:</strong> {result.weather}</p>
          
          <div>
            <h4>Treatment Advice</h4>
            <p><strong>Severity:</strong> {result.advice.severity}</p>
            <p>{result.advice.action_plan}</p>
            
            {/* Weather Advisory */}
            <div style={{background: '#fff3cd', padding: '10px', borderRadius: '5px'}}>
              <strong>🌤️ Weather Advisory:</strong>
              <p>{result.advice.weather_advisory}</p>
            </div>
            
            {/* Sources */}
            <h5>Sources:</h5>
            <ul>
              {result.advice.sources.map((source, i) => (
                <li key={i}>
                  {source.source} - {source.content_type} ({(source.confidence * 100).toFixed(0)}%)
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function
async function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported'));
      return;
    }
    
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      }),
      (error) => {
        console.error('Geolocation error:', error);
        // Fallback to Manila
        resolve({
          latitude: 14.5995,
          longitude: 120.9842,
          isDefault: true
        });
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  });
}
```

---

## 🎨 Weather Display Components

### Weather Icon

```jsx
function WeatherIcon({ weather }) {
  const icons = {
    'Sunny': '☀️',
    'Cloudy': '☁️',
    'Rainy': '🌧️',
    'Windy': '💨',
    'Humid': '💧',
    'Hot': '🔥',
    'Cold': '❄️'
  };
  
  return <span style={{fontSize: '2rem'}}>{icons[weather] || '🌤️'}</span>;
}
```

### Weather Advisory Card

```jsx
function WeatherAdvisoryCard({ advisory }) {
  const hasRainWarning = advisory.includes('RAIN EXPECTED');
  
  return (
    <div style={{
      background: hasRainWarning ? '#fff3cd' : '#d1ecf1',
      border: `2px solid ${hasRainWarning ? '#ffc107' : '#0c5460'}`,
      borderRadius: '8px',
      padding: '15px',
      margin: '10px 0'
    }}>
      <h4>
        {hasRainWarning ? '⚠️' : '🌤️'} Weather Advisory
      </h4>
      <p style={{whiteSpace: 'pre-wrap'}}>{advisory}</p>
    </div>
  );
}
```

---

## 📱 Mobile Considerations

### Check for Mobile Browser

```javascript
function isMobile() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

// Use in component
if (isMobile()) {
  console.log('📱 Mobile device detected - optimizing experience');
  // Show mobile-friendly location UI
}
```

### Mobile Geolocation Options

```javascript
const geoOptions = {
  enableHighAccuracy: true,  // Use GPS on mobile
  timeout: 10000,            // Wait up to 10 seconds
  maximumAge: 300000         // Cache for 5 minutes
};

navigator.geolocation.getCurrentPosition(success, error, geoOptions);
```

---

## 🔧 Error Handling

### Complete Error Handler

```javascript
async function predictWithErrorHandling(imageFile, latitude, longitude) {
  try {
    const formData = new FormData();
    formData.append('file', imageFile);
    formData.append('model', 'mobile');
    
    if (latitude && longitude) {
      formData.append('latitude', latitude);
      formData.append('longitude', longitude);
    }
    
    const response = await fetch('http://localhost:8000/predict', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Prediction failed');
    }
    
    return await response.json();
    
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Cannot connect to server. Please check if backend is running.');
    } else if (error.message.includes('timeout')) {
      throw new Error('Request timeout. Please try again.');
    } else {
      throw error;
    }
  }
}
```

---

## 🧪 Testing

### Test Location Detection

```javascript
async function testLocation() {
  console.log('🧪 Testing location detection...');
  
  try {
    const location = await getLocation();
    console.log('✅ Location detected:', location);
    console.log(`   Latitude: ${location.latitude}`);
    console.log(`   Longitude: ${location.longitude}`);
    console.log(`   Is Default: ${location.isDefault || false}`);
  } catch (error) {
    console.error('❌ Location test failed:', error);
  }
}

// Run test
testLocation();
```

### Test Prediction with Location

```javascript
async function testPrediction() {
  console.log('🧪 Testing prediction with location...');
  
  // Get test image
  const input = document.querySelector('input[type="file"]');
  const imageFile = input.files[0];
  
  if (!imageFile) {
    console.error('❌ No image selected');
    return;
  }
  
  try {
    // Get location
    const location = await getLocation();
    console.log('📍 Location:', location);
    
    // Predict
    const result = await predictWithLocation(imageFile, location.latitude, location.longitude);
    console.log('✅ Prediction result:', result);
    console.log(`   Disease: ${result.disease}`);
    console.log(`   Weather: ${result.weather}`);
    console.log(`   Advisory: ${result.advice.weather_advisory}`);
  } catch (error) {
    console.error('❌ Prediction test failed:', error);
  }
}
```

---

## 📋 Best Practices

1. **Always request permission** before accessing location
2. **Provide fallback** to default location (Manila)
3. **Show loading states** during location detection
4. **Cache location** for repeated predictions
5. **Handle errors gracefully** with user-friendly messages
6. **Test on mobile** - location APIs behave differently
7. **Respect privacy** - explain why location is needed

---

## 🎯 Quick Checklist

- [ ] Add location detection button
- [ ] Request geolocation permission
- [ ] Send lat/lon to `/predict` endpoint
- [ ] Display weather information in results
- [ ] Show weather advisory prominently
- [ ] Handle location errors gracefully
- [ ] Test on desktop and mobile
- [ ] Add loading states
- [ ] Implement fallback to Manila

---

## 📚 References

- [Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API)
- [Permissions API](https://developer.mozilla.org/en-US/docs/Web/API/Permissions_API)
- [FormData API](https://developer.mozilla.org/en-US/docs/Web/API/FormData)

---

**Ready to integrate! 🚀**
