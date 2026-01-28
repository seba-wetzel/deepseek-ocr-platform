import requests
import os

URL = "http://localhost:8000/api/upload"
TEST_FILE = "test_upload.pdf"

# Create dummy PDF
with open(TEST_FILE, "wb") as f:
    f.write(b"%PDF-1.4 header dummy content")

print(f"Testing upload to {URL}...")
try:
    with open(TEST_FILE, "rb") as f:
        files = {"file": (TEST_FILE, f, "application/pdf")}
        response = requests.post(URL, files=files, timeout=5)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Backend upload works!")
    else:
        print("❌ Backend returned error.")

except requests.exceptions.ConnectionError:
    print("❌ Connection Refused. Is the backend running?")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
