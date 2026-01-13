import unittest
import re
import json
import os
from typing import List, Dict, Any

def mock_extract_markdown_tool_calls(content: str) -> List[Dict[str, Any]]:
    """Equivalent to the logic in graph_builder.py."""
    if not content or "```" not in content:
        return []
    
    tool_calls = []
    # Match ```json ... ``` blocks
    pattern = r'```(?:json)?\s*(.*?)\s*```'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            potential_json = match.group(1).strip()
            # Handle list of calls or single call object
            data = json.loads(potential_json)
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and ("name" in item or "action" in item):
                        tool_calls.append({
                            "name": item.get("name") or item.get("action"),
                            "args": item.get("arguments") or item.get("args") or item.get("action_input") or {},
                            "id": f"markdown_tc_mock"
                        })
            elif isinstance(data, dict):
                if "name" in data or "action" in data:
                    tool_calls.append({
                        "name": data.get("name") or data.get("action"),
                        "args": data.get("arguments") or data.get("args") or data.get("action_input") or {},
                        "id": f"markdown_tc_mock"
                    })
        except Exception:
            continue
            
    return tool_calls

class TestMarkdownToolExtraction(unittest.TestCase):
    def test_single_call_json_block(self):
        content = "I'll search for this:\n```json\n{\"name\": \"search_tavily\", \"args\": {\"query\": \"test\"}}\n```"
        result = mock_extract_markdown_tool_calls(content)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "search_tavily")
        self.assertEqual(result[0]["args"]["query"], "test")

    def test_multi_call_list(self):
        content = "```json\n[{\"name\": \"tool1\"}, {\"name\": \"tool2\"}]\n```"
        result = mock_extract_markdown_tool_calls(content)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "tool1")
        self.assertEqual(result[1]["name"], "tool2")

    def test_action_format(self):
        # DeepSeek often uses this format
        content = "```json\n{\"action\": \"search_tavily\", \"action_input\": {\"query\": \"test\"}}\n```"
        result = mock_extract_markdown_tool_calls(content)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "search_tavily")
        self.assertEqual(result[0]["args"]["query"], "test")

    def test_no_blocks(self):
        content = "I will not call any tools."
        result = mock_extract_markdown_tool_calls(content)
        self.assertEqual(len(result), 0)

    def test_messy_blocks(self):
        content = "Some text\n```json\n{\"name\": \"tool1\"}\n```\nMore text\n```\n{\"name\": \"tool2\"}\n```"
        result = mock_extract_markdown_tool_calls(content)
        self.assertEqual(len(result), 2)

if __name__ == "__main__":
    unittest.main()
