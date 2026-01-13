import sys
import os
from pathlib import Path

# Add src to sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from flexi.core.tools import search_tavily, search_serper, search_ddg, web_search

def check_connectivity():
    print("=== Search Connectivity Diagnostics (REAL CALLS) ===")
    query = "Python vs Rust 2024 benchmarks"
    
    # 1. Check Serper
    print("\n[1] Checking Serper...")
    serper_out = search_serper(query, num_results=1)
    if serper_out.lower().startswith("error"):
        print(f"❌ Serper Failed: {serper_out}")
    else:
        print("✅ Serper is WORKING")
        print(f"   Sample: {serper_out[:100]}...")

    # 2. Check Tavily
    print("\n[2] Checking Tavily...")
    tavily_out = search_tavily(query, search_depth="basic", num_results=1)
    if tavily_out.lower().startswith("error"):
        print(f"❌ Tavily Failed: {tavily_out}")
    else:
        print("✅ Tavily is WORKING")
        print(f"   Sample: {tavily_out[:100]}...")

    # 3. Check DuckDuckGo
    print("\n[3] Checking DuckDuckGo...")
    ddg_out = search_ddg(query, num_results=1)
    if ddg_out.lower().startswith("error"):
        print(f"❌ DDG Failed: {ddg_out}")
    else:
        print("✅ DDG is WORKING")
        print(f"   Sample: {ddg_out[:100]}...")

    # 4. Check Unified web_search (Fallback Test)
    print("\n[4] Checking Unified web_search (Fallback Logic)...")
    unified_out = web_search(query, mode="fallback", num_results=1)
    if "Error" in unified_out and "All providers failed" in unified_out:
        print(f"❌ All Search Providers Failed.")
    else:
        print(f"✅ web_search returned results (using available provider)")
        print(f"   Sample: {unified_out[:100]}...")

if __name__ == "__main__":
    check_connectivity()
