import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
# No explicit api_version parameter in genai.configure in some versions, 
# but we can try to see if it works or if there's another way.
# Actually, the SDK 0.8.6 should handle it.

print("Testing Gemini with explicit configuration...")
try:
    genai.configure(api_key=api_key)
    # Some versions allow passing api_version to the model
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
