import sys
import os
from pathlib import Path
from unittest.mock import patch

# Add src to sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from flexi.core.tools import web_search

def test_web_search_fallback():
    print("Testing web_search Fallback Logic...")
    query = "test query"
    
    # CASE 1: Serper succeeds
    with patch('flexi.core.tools.search_serper') as mock_serper:
        mock_serper.return_value = "Serper Success"
        result = web_search(query, mode="fallback")
        print(f"Case 1 (Serper works): {result}")
        assert result == "Serper Success"

    # CASE 2: Serper fails, Tavily succeeds
    with patch('flexi.core.tools.search_serper') as mock_serper:
        with patch('flexi.core.tools.search_tavily') as mock_tavily:
            mock_serper.return_value = "Error: Serper Quota"
            mock_tavily.return_value = "Tavily Success"
            result = web_search(query, mode="fallback")
            print(f"Case 2 (Serper fails, Tavily works): {result}")
            assert result == "Tavily Success"

    # CASE 3: Both Serper and Tavily fail, DDG succeeds
    with patch('flexi.core.tools.search_serper') as mock_serper:
        with patch('flexi.core.tools.search_tavily') as mock_tavily:
            with patch('flexi.core.tools.search_ddg') as mock_ddg:
                mock_serper.return_value = "Error: Serper Quota"
                mock_tavily.return_value = "Error: Tavily Quota"
                mock_ddg.return_value = "DDG Success"
                result = web_search(query, mode="fallback")
                print(f"Case 3 (Serper/Tavily fail, DDG works): {result}")
                assert result == "DDG Success"

    print("\n✅ web_search fallback logic verified!")

if __name__ == "__main__":
    test_web_search_fallback()
