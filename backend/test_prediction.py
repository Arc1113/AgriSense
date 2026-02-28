"""Test the full prediction endpoint with RAG advice generation."""
import requests
from PIL import Image
import io

# Create a simple green test image (simulates a leaf)
img = Image.new('RGB', (224, 224), color='green')
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

# Prepare the multipart/form-data request
url = "http://localhost:8000/predict"
files = {
    'file': ('test_leaf.jpg', buf, 'image/jpeg')
}
params = {
    'model': 'mobile'
}

print("=" * 60)
print("  Testing /predict endpoint with RAG advice")
print("=" * 60)

try:
    response = requests.post(url, files=files, params=params, timeout=120)
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✅ Prediction Result:")
        print(f"   Disease: {data.get('disease', 'N/A')}")
        print(f"   Confidence: {data.get('confidence', 0):.1%}")
        print(f"   Model Used: {data.get('model_used', 'N/A')}")
        print(f"   Is Healthy: {data.get('is_healthy', 'N/A')}")
        print(f"   Weather: {data.get('weather', 'N/A')}")
        
        advice = data.get('advice', {})
        if advice:
            print(f"\n✅ RAG Advice Generated:")
            print(f"   Severity: {advice.get('severity', 'N/A')}")
            print(f"   RAG Enabled: {advice.get('rag_enabled', False)}")
            
            # Action plan
            action = advice.get('action_plan', '')
            if action:
                print(f"\n   Action Plan (first 300 chars):")
                print(f"   {action[:300]}...")
            
            # Safety warning
            safety = advice.get('safety_warning', '')
            if safety:
                print(f"\n   Safety Warning (first 150 chars):")
                print(f"   {safety[:150]}...")
            
            # Sources (as list of dicts)
            sources = advice.get('sources', [])
            if sources:
                print(f"\n   Sources ({len(sources)} docs):")
                for i, src in enumerate(sources[:3]):
                    if isinstance(src, dict):
                        print(f"     {i+1}. {src.get('source', 'Unknown')} - {src.get('content_type', 'N/A')} (conf: {src.get('confidence', 0):.2f})")
                    else:
                        print(f"     {i+1}. {src}")
            
            print("\n" + "=" * 60)
            print("✅ RAG ADVICE IS WORKING!")
            print("=" * 60)
        else:
            print("\n⚠️  No advice returned - RAG may not be fully integrated")
    else:
        print(f"\n❌ Error: {response.text}")

except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to server at localhost:8000")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 60)
