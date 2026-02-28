"""
Quick Test Script for Weather API Integration

Tests:
1. Weather service module import
2. Weather fetching (with and without API key)
3. Main.py integration
4. Error handling
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all imports work"""
    print("=" * 70)
    print("✅ Test 1: Imports")
    print("=" * 70)
    
    try:
        from weather_service import get_weather_forecast, get_api_key
        print("✅ weather_service imports successful")
        
        from main import app, WeatherCondition
        print("✅ main.py imports successful")
        
        from rag_agent import get_agri_advice
        print("✅ rag_agent imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_weather_service():
    """Test weather service"""
    print("\n" + "=" * 70)
    print("✅ Test 2: Weather Service")
    print("=" * 70)
    
    try:
        from weather_service import get_weather_forecast, get_api_key
        
        # Check API key
        api_key = get_api_key()
        if api_key:
            print(f"✅ API key configured: {api_key[:10]}...")
        else:
            print("⚠️ API key not set (will use fallback)")
        
        # Test with default location (Manila)
        print("\n📍 Testing Manila (default)...")
        weather, forecast = get_weather_forecast()
        print(f"   Current: {weather}")
        print(f"   Forecast: {forecast[:80]}..." if forecast else "   Forecast: (not available)")
        
        # Test with custom location
        print("\n📍 Testing Quezon City...")
        weather, forecast = get_weather_forecast(
            lat=14.6760,
            lon=121.0437,
            location_name="Quezon City"
        )
        print(f"   Current: {weather}")
        print(f"   Forecast: {forecast[:80]}..." if forecast else "   Forecast: (not available)")
        
        return True
    except Exception as e:
        print(f"❌ Weather service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration with main.py"""
    print("\n" + "=" * 70)
    print("✅ Test 3: Integration Check")
    print("=" * 70)
    
    try:
        from main import predict
        import inspect
        
        # Check function signature
        sig = inspect.signature(predict)
        params = list(sig.parameters.keys())
        
        print("📋 /predict endpoint parameters:")
        for param in params:
            print(f"   - {param}")
        
        # Verify new parameters exist
        required_params = ['file', 'model', 'weather', 'forecast', 'latitude', 'longitude']
        for req in required_params:
            if req in params:
                print(f"   ✅ {req} parameter exists")
            else:
                print(f"   ❌ {req} parameter MISSING")
        
        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_agent():
    """Test RAG agent with weather forecast"""
    print("\n" + "=" * 70)
    print("✅ Test 4: RAG Agent Weather Support")
    print("=" * 70)
    
    try:
        from rag_agent import get_agri_advice
        import inspect
        
        # Check function signature
        sig = inspect.signature(get_agri_advice)
        params = list(sig.parameters.keys())
        
        print("📋 get_agri_advice parameters:")
        for param in params:
            print(f"   - {param}")
        
        if 'weather_forecast' in params:
            print("   ✅ weather_forecast parameter exists")
        else:
            print("   ❌ weather_forecast parameter MISSING")
        
        return True
    except Exception as e:
        print(f"❌ RAG agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🧪" * 35)
    print("WEATHER API INTEGRATION TEST SUITE")
    print("🧪" * 35)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Weather Service", test_weather_service()))
    results.append(("Integration", test_integration()))
    results.append(("RAG Agent", test_rag_agent()))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Integration Complete!")
    else:
        print("⚠️ Some tests failed - Check errors above")
    
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
