import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Config 
MODELS_TO_TEST = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

API_KEY = os.getenv("GEMINI_API_KEY")

# Validate API key exists 
if not API_KEY:
    print("GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key = API_KEY)

print("=" * 55)
print("  Gemini Model Availability Test")
print("=" * 55)



# Test each model 
for model in MODELS_TO_TEST:
    try:
        response = client.models.generate_content(
            model    = model,
            contents = "Reply with exactly one word: working",
        )
        reply = response.text.strip()
        print(f"✅  {model:<30} → {reply}")

    except Exception as e:
        print(f"❌  {model:<30} → {str(e)[:60]}")

print("=" * 55)
print("Use any ✅ model in your ai_service.py")