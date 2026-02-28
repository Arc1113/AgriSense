import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
print(f"Testing API Key: {api_key[:5]}...{api_key[-4:]}")

client = Groq(api_key=api_key)

try:
    print("Sending request to Groq...")
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hello"}],
        model="llama3-70b-8192",
    )
    print("Success!")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"FAILED: {e}")
