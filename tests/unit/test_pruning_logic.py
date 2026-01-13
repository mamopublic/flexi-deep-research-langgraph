import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from flexi.agents.graph_builder import _prune_reasoning

class TestPruningLogic(unittest.TestCase):
    def test_standard_think_tags(self):
        content = "<think>I need to search for Python vs Rust.</think>The comparison shows..."
        expected = "The comparison shows..."
        self.assertEqual(_prune_reasoning(content), expected)

    def test_multiline_think_tags(self):
        content = """<think>
        Line 1 of reasoning
        Line 2
        </think>Actual Output"""
        expected = "Actual Output"
        self.assertEqual(_prune_reasoning(content), expected)

    def test_variant_tags(self):
        # [thought] variant
        content = "[thought]Some thinking[/thought]Final Answer"
        self.assertEqual(_prune_reasoning(content), "Final Answer")
        
        # <thinking> variant
        content = "<thinking>Deep reasoning</thinking>Result"
        self.assertEqual(_prune_reasoning(content), "Result")

    def test_unclosed_tag(self):
        # Handle cases where model is cut off
        content = "Fact 1. <think>I am thinking about Fact 2..."
        self.assertEqual(_prune_reasoning(content), "Fact 1.")

    def test_no_tags(self):
        content = "Just a normal response."
        self.assertEqual(_prune_reasoning(content), "Just a normal response.")

    def test_nested_tags_attempt(self):
        # Should handle it greedily or non-greedily depending on regex
        content = "<think>Think 1</think> Content <think>Think 2</think> Final"
        self.assertEqual(_prune_reasoning(content), "Content  Final")

if __name__ == "__main__":
    unittest.main()
