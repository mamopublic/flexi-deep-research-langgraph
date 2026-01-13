import sys
import os
from pathlib import Path

# Add src to sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from flexi.core.tools import search_tavily
from flexi.config.settings import settings

def test_tavily_error_reporting():
    print("Testing Tavily Error Reporting...")
    print(f"API Key present: {'Yes' if settings.TAVILY_API_KEY else 'No'}")
    
    query = "test query for error reporting"
    
    # This should trigger the real API call and return the improved error message
    # if credits are exhausted or if there's any other API error.
    result = search_tavily(query=query)
    
    print("\n--- Result ---")
    print(result)
    print("--------------\n")
    
    if "Error calling Tavily API" in result:
        print("✅ SUCCESS: Error was correctly captured.")
        if "Tavily API Error" in result:
            print("✅ SUCCESS: Detailed API response included.")
    else:
        print("❌ FAILURE: Error was not captured as expected (or call unexpectedly succeeded).")

if __name__ == "__main__":
    test_tavily_error_reporting()
