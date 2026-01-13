import os
import requests
from dotenv import load_dotenv

def test_tavily_direct():
    # Load .env
    load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        print("❌ Error: TAVILY_API_KEY not found in environment variables.")
        return

    print(f"Testing Tavily API Key: {api_key[:5]}...{api_key[-5:]}")
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": "What is the capital of France?",
        "search_depth": "basic",
        "max_results": 1
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                print("✅ Success! Tavily returned results:")
                print(f"   Title: {results[0].get('title')}")
                print(f"   URL: {results[0].get('url')}")
            else:
                print("⚠️ Connected but no results found.")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")

if __name__ == "__main__":
    test_tavily_direct()
