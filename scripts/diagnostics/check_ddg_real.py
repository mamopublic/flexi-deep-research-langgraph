import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from flexi.core.tools import search_ddg

print("\n🦆 Checking DuckDuckGo Connectivity...")
print("Query: 'Python vs Rust'")
print("-" * 50)

try:
    result = search_ddg("Python vs Rust", num_results=1)
    print(result)
    
    if "Error" in result or "No DuckDuckGo results" in result:
        print("\n❌ DDG Test FAILED")
        sys.exit(1)
    else:
        print("\n✅ DDG Test PASSED")
        
except Exception as e:
    print(f"\n❌ DDG Test CRASHED: {e}")
    sys.exit(1)
