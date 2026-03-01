import sys
from google.genai import types

# Fix console encoding
sys.stdout.reconfigure(encoding='utf-8')

print("Inspecting google.genai.types for voice information...")

# 1. Check if there are any Enums related to Voice
for name in dir(types):
    if "Voice" in name:
        print(f"Found type: {name}")
        obj = getattr(types, name)
        # Try to inspect its members if it's an enum-like class
        try:
            # Check pydantic fields or standard attributes
            if hasattr(obj, "__fields__"):
                print(f"  Fields: {list(obj.__fields__.keys())}")
            if hasattr(obj, "__members__"):
                print(f"  Members: {list(obj.__members__.keys())}")
        except:
            pass

print("-" * 20)

# 2. Check explicitly for PrebuiltVoiceConfig or similar constants
try:
    # Sometimes voices are listed in docstrings or constants
    pass
except:
    pass

# 3. Known voices list from documentation (embedded here for verification if SDK doesn't help)
# Based on Google AI Studio
candidates = [
    "Aoede", "Charon", "Fenrir", "Kore", "Puck", "Zephyr",
    "Algenib", "Callisto", "Despina", "Dia", "Enceladus", "Erinome", "Himalia",
    "Io", "Jupiter", "Laomedeia", "Mimas", "Moon", "Oberon", "Phobos", "Rasalgethi",
    "Rhea", "Telesto", "Titan", "Triton", "Umbriel"
]

print("Candidate voices to verify (if possible via API):")
print(", ".join(candidates))

# Note: The API currently doesn't seem to have a 'list_voices' endpoint for Gemini (unlike Google Cloud TTS).
# We might rely on the user's provided screenshot and official docs.
