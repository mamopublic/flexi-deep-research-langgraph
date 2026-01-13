import unittest
import json
import re
from typing import Dict, Any

def mock_extract_json(response_text: str) -> Dict[str, Any]:
    """Extracted JSON extraction logic from architect.py for testing."""
    response_text = response_text.strip()
    
    # Step 1: Handle markdown code blocks
    if "```" in response_text:
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1).strip()
        else:
            # Fallback for messy markdown: just strip the tokens
            response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    # Step 2: Try parsing directly. If it fails, try to find the outermost { }
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: Find outermost {}
        if "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}")
            potential_json = response_text[start:end+1]
            return json.loads(potential_json)
        else:
            raise

class TestArchitectExtraction(unittest.TestCase):
    def test_clean_json_block(self):
        content = "Here is the config:\n```json\n{\"key\": \"value\"}\n```"
        result = mock_extract_json(content)
        self.assertEqual(result["key"], "value")

    def test_no_markdown_block(self):
        content = "{\"key\": \"value\"}"
        result = mock_extract_json(content)
        self.assertEqual(result["key"], "value")

    def test_messy_markdown(self):
        # Case where model might not use newlines or use text after block
        content = "```json{\"key\": \"value\"}```Some other text"
        result = mock_extract_json(content)
        self.assertEqual(result["key"], "value")

    def test_trailing_text_json_fallback(self):
        # The common failure case: JSON follow by explanation outside blocks
        content = "Here's the JSON:\n{\"key\": \"value\"}\n\nI chose this because..."
        result = mock_extract_json(content)
        self.assertEqual(result["key"], "value")

    def test_truncated_prefix(self):
        content = "Certainly! {\"key\": \"value\"}"
        result = mock_extract_json(content)
        self.assertEqual(result["key"], "value")

    def test_malformed_json_raises(self):
        content = "This is not JSON: {key: value}"
        with self.assertRaises(json.JSONDecodeError):
            mock_extract_json(content)

if __name__ == "__main__":
    unittest.main()
