#!/usr/bin/env python3
"""
Parallel API Discovery Tool

This script helps discover the actual Parallel API format by:
1. Testing the API key
2. Attempting various request formats
3. Logging the actual response structure
4. Helping adapt the fetcher to the real API

Usage:
    export PARALLEL_API_KEY=HKkalLeE4YIrDJYnZDInOM7tL6CXZKmRTbCHrQEe
    python scripts/discover_parallel_api.py
"""

import os
import sys
import httpx
import json
from datetime import date, timedelta

# API Configuration
API_KEY = os.getenv("PARALLEL_API_KEY")
if not API_KEY:
    print("❌ ERROR: PARALLEL_API_KEY not set")
    sys.exit(1)

print("🔍 Parallel API Discovery Tool")
print("=" * 70)
print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
print()

# Common flight API endpoint patterns
POSSIBLE_ENDPOINTS = [
    "https://api.parallel.com/v1/flights/search",
    "https://api.parallel.com/v1/flights",
    "https://api.parallel.com/flights/search",
    "https://api.parallel.com/search",
    "https://parallel-api.com/v1/search",
]

# Test request formats (different APIs use different structures)
TEST_FORMATS = {
    "Format 1 (Bulk queries array)": {
        "queries": [{
            "origin": "JFK",
            "destination": "MIA",
            "depart_date_start": date.today().isoformat(),
            "depart_date_end": (date.today() + timedelta(days=30)).isoformat(),
            "cabin": "economy"
        }],
        "currency": "USD",
        "max_results_per_query": 10
    },

    "Format 2 (Single query)": {
        "origin": "JFK",
        "destination": "MIA",
        "depart_date": date.today().isoformat(),
        "cabin_class": "economy",
        "currency": "USD"
    },

    "Format 3 (Search params)": {
        "from": "JFK",
        "to": "MIA",
        "date": date.today().isoformat(),
        "class": "economy"
    },

    "Format 4 (Routes array)": {
        "routes": [{
            "origin": "JFK",
            "dest": "MIA",
            "date_range": {
                "start": date.today().isoformat(),
                "end": (date.today() + timedelta(days=30)).isoformat()
            }
        }]
    }
}


def test_endpoint(endpoint: str, payload: dict, format_name: str):
    """Test an endpoint with a specific payload format"""

    print(f"\n{'=' * 70}")
    print(f"Testing: {format_name}")
    print(f"Endpoint: {endpoint}")
    print(f"{'=' * 70}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print("\n📤 Request Payload:")
    print(json.dumps(payload, indent=2))
    print()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, headers=headers, json=payload)

            print(f"📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✅ SUCCESS!")
                print("\n📥 Response:")
                try:
                    data = response.json()
                    print(json.dumps(data, indent=2)[:1000])  # First 1000 chars

                    # Save successful format
                    with open("parallel_api_success.json", "w") as f:
                        json.dump({
                            "endpoint": endpoint,
                            "request": payload,
                            "response": data
                        }, f, indent=2)

                    print(f"\n💾 Saved successful format to: parallel_api_success.json")
                    return True

                except Exception as e:
                    print(f"Response (text): {response.text[:500]}")

            elif response.status_code == 401:
                print("❌ UNAUTHORIZED - API key may be invalid")
                print(f"Response: {response.text}")

            elif response.status_code == 403:
                print("❌ FORBIDDEN - API key may lack permissions")
                print(f"Response: {response.text}")

            elif response.status_code == 400:
                print("⚠️  BAD REQUEST - Payload format incorrect")
                print(f"Response: {response.text}")

            elif response.status_code == 404:
                print("⚠️  NOT FOUND - Endpoint doesn't exist")

            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                print(f"Response: {response.text[:500]}")

    except httpx.ConnectError as e:
        print(f"❌ CONNECTION ERROR: {e}")

    except httpx.TimeoutException:
        print("⏱️  TIMEOUT - Request took too long")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    return False


def main():
    """Test all endpoint and format combinations"""

    print("\n🎯 Testing Endpoint/Format Combinations")
    print("This will help us discover the correct API format.\n")

    success = False

    # Test each endpoint with each format
    for endpoint in POSSIBLE_ENDPOINTS:
        if success:
            break

        for format_name, payload in TEST_FORMATS.items():
            if success:
                break

            success = test_endpoint(endpoint, payload, format_name)

            if success:
                print("\n" + "=" * 70)
                print("🎉 FOUND WORKING FORMAT!")
                print("=" * 70)
                print(f"\nEndpoint: {endpoint}")
                print(f"Format: {format_name}")
                print("\nCheck 'parallel_api_success.json' for details")
                print("\nNext steps:")
                print("1. Review the successful format")
                print("2. Update src/adapters/prices_parallel.py if needed")
                print("3. Update PARALLEL_API_ENDPOINT environment variable")
                break

    if not success:
        print("\n" + "=" * 70)
        print("❌ NO WORKING FORMAT FOUND")
        print("=" * 70)
        print("\nPossible issues:")
        print("1. API key is invalid or expired")
        print("2. API endpoint is different than expected")
        print("3. API requires different authentication")
        print("4. API payload format is different")
        print("\nRecommended actions:")
        print("1. Check Parallel API documentation")
        print("2. Verify API key is active")
        print("3. Contact Parallel API support for correct endpoint/format")
        print("4. Check if API requires additional headers or auth")

        # Ask user for API documentation
        print("\n" + "=" * 70)
        print("📚 DO YOU HAVE PARALLEL API DOCUMENTATION?")
        print("=" * 70)
        print("\nPlease provide:")
        print("- Correct API endpoint URL")
        print("- Expected request format")
        print("- Example response format")
        print("- Any authentication requirements")
        print("\nThis will help us adapt the fetcher correctly.")


if __name__ == "__main__":
    main()
