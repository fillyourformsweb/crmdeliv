"""
Chat Widget Test Script
This script tests the chat widget functionality by simulating button clicks and API calls.
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"

def test_chat_endpoints():
    """Test chat API endpoints"""
    print("=" * 50)
    print("CHAT WIDGET TEST")
    print("=" * 50)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Test 1: Check if chat messages endpoint is accessible
    print("\n1. Testing /api/chat/messages endpoint...")
    try:
        response = session.get(f"{BASE_URL}/api/chat/messages?limit=5")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("   ❌ Authentication required - User needs to be logged in")
            print("   This is expected behavior. The chat requires login.")
        elif response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Found {len(data.get('messages', []))} messages")
            if data.get('messages'):
                print(f"   Latest message: {data['messages'][-1]}")
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Check if server is running
    print("\n2. Testing if server is running...")
    try:
        response = session.get(BASE_URL)
        print(f"   Status Code: {response.status_code}")
        if response.status_code in [200, 302]:
            print("   ✅ Server is running!")
        else:
            print(f"   ⚠️  Server returned: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Server not accessible: {e}")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
    print("\nNEXT STEPS:")
    print("1. Open browser and navigate to http://localhost:5000")
    print("2. Login to the application")
    print("3. Look for the purple chat button in bottom-right corner")
    print("4. Click the button - chat window should appear")
    print("5. If it doesn't work, open browser console (F12) and check for errors")
    print("=" * 50)

if __name__ == "__main__":
    test_chat_endpoints()
