import requests

def test_pincode_api(pincode):
    url = f"http://127.0.0.1:5000/api/pincode/{pincode}"
    print(f"Testing pincode: {pincode}")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test with a known valid pincode (Mumbai)
    test_pincode_api("400001")
    # Test with another (Bangalore)
    test_pincode_api("560001")
    # Test with invalid format
    test_pincode_api("12345")
    # Test with non-existent pincode
    test_pincode_api("999999")
