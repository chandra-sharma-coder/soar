"""
Simple Test Script for URLscan.io FastAPI Application
Tests all available endpoints
"""
import requests
import time
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000/api/v1"


def print_response(title: str, response: requests.Response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_health_check():
    """Test the health check endpoint."""
    response = requests.get("http://localhost:8000/health")
    print_response("Health Check", response)
    return response.status_code == 200


def test_detonate_url():
    """Test URL detonation endpoint."""
    payload = {
        "url": "https://www.example.com"
    }
    response = requests.post(f"{BASE_URL}/detonate_url", json=payload)
    print_response("Detonate URL", response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success" and data.get("data"):
            return data["data"][0].get("scan_id")
    return None


def test_get_report(scan_id: str):
    """Test get report endpoint."""
    if not scan_id:
        print("\n⚠️  Skipping get_report test - no scan_id available")
        return
    
    print(f"\n⏳ Waiting 10 seconds for scan to complete...")
    time.sleep(10)
    
    payload = {
        "uuid": scan_id
    }
    response = requests.post(f"{BASE_URL}/get_report", json=payload)
    print_response("Get Report", response)


def test_lookup_domain():
    """Test domain lookup endpoint."""
    payload = {
        "domain": "example.com"
    }
    response = requests.post(f"{BASE_URL}/lookup_domain", json=payload)
    print_response("Lookup Domain", response)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("URLscan.io FastAPI Application - Test Suite")
    print("="*60)
    print("\n⚠️  Make sure the server is running on http://localhost:8000")
    print("   Run: python app/run.py\n")
    
    try:
        # Test 1: Health Check
        if not test_health_check():
            print("\n❌ Server is not responding. Please start the server first.")
            return
        
        # Test 2: Detonate URL
        scan_id = test_detonate_url()
        
        # Test 3: Lookup Domain
        test_lookup_domain()
        
        # Test 4: Get Report (if we have a scan_id)
        if scan_id:
            test_get_report(scan_id)
        
        print("\n" + "="*60)
        print("✅ Test Suite Completed")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server.")
        print("   Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
