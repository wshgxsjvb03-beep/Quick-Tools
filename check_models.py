import os
import json
from google import genai

# Load key from config if possible, or expect manual input
# For this script we'll try to read from config.json
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
        api_key_data = config_data.get("google_ai_keys", [{}])[0]
        api_key = api_key_data.get("key")
except Exception as e:
    print(f"Error reading config: {e}")
    api_key = None

if not api_key:
    print("No API Key found in config.json")
    exit(1)

client = genai.Client(api_key=api_key)

print(f"Using Key: {api_key[:5]}...{api_key[-4:]}")
print("Fetching available models...")

try:
    for model in client.models.list(config={"page_size": 100}):
        print(f"Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Supported Actions: {model.supported_actions}")
        print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")
