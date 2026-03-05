import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("Testing Gemini 2.0 Flash...")
try:
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Hello")
    print(f"2.0 Response: {response.text}")
except Exception as e:
    print(f"2.0 Error: {e}")

print("\nTesting Gemini Flash Latest...")
try:
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Hello")
    print(f"Latest Response: {response.text}")
except Exception as e:
    print(f"Latest Error: {e}")
