import unittest
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# We need to mock the ResearchState and other dependencies or just test the logic
# Since create_supervisor_executor creates a closure, we might need a way to test it.
# For now, I'll extract the core parsing logic if possible, or just mock the LLM.

# Actually, the parsing logic is inside the supervisor_executor function.
# I'll create a minimal test that calls a modified version of it or just test the regexes.

import re

def mock_parse_decision(content: str, subordinate_roles: List[str]) -> Dict[str, Any]:
    """Extracted parsing logic from graph_builder.py for testing."""
    next_agent = None
    next_tasks = []
    
    # 1. Look for a line containing a decision instruction
    decision_line = None
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    
    for line in lines:
        if line.upper().startswith("PARALLEL:"):
            decision_line = line
            break
    if not decision_line:
        for line in lines:
            if line.upper().startswith("NEXT:"):
                decision_line = line
                break
    if not decision_line:
        decision_line = lines[0] if lines else ""

    # Clean the decision line for parsing
    parser_line = decision_line
    while True:
        upper_line = parser_line.upper()
        if upper_line.startswith("NEXT:"):
            parser_line = parser_line[5:].strip()
        elif upper_line.startswith("PARALLEL:"):
            parser_line = parser_line[9:].strip()
        else:
            break
    
    # 1. Check for PARALLEL (Explicit or inferred from commas)
    is_parallel_prefix = decision_line.upper().startswith("PARALLEL:") or "PARALLEL:" in decision_line.upper()
    if is_parallel_prefix or "," in parser_line:
        # We use parser_line which is now stripped of NEXT: and PARALLEL:
        task_blob = parser_line
        parts = re.split(r',\s*(?=[^"]*(?:"[^"]*"[^"]*)*$)', task_blob)
        for part in parts:
            if ":" in part:
                agent_part, inst_part = part.split(":", 1)
                a_name = agent_part.strip().strip("[]")
                a_instruction = inst_part.strip().strip('"').strip("'")
                if a_name in subordinate_roles:
                    next_tasks.append({"agent": a_name, "instruction": a_instruction})
            else:
                a_name = part.strip().strip("[]")
                if a_name in subordinate_roles:
                    next_tasks.append({"agent": a_name, "instruction": "Proceed with assigned research task."})
        if next_tasks:
            next_agent = "PARALLEL"
    
    # 2. Check for NEXT (Fallback or explicit)
    if not next_agent:
        # Check parser_line first (it's stripped of prefixes)
        if parser_line in subordinate_roles:
            next_agent = parser_line
        else:
            # Last resort: generic regex search anywhere in the decision line
            match = re.search(r'(?:NEXT:|PARALLEL:)?\s*(\w+)', decision_line, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if candidate in subordinate_roles:
                    next_agent = candidate
                    
    return {"next_agent": next_agent, "next_tasks": next_tasks}

class TestSupervisorParsing(unittest.TestCase):
    def setUp(self):
        self.roles = ["researcher_python", "researcher_rust", "analyst", "summarizer"]

    def test_standard_next(self):
        result = mock_parse_decision("NEXT: analyst\nReasoning here.", self.roles)
        self.assertEqual(result["next_agent"], "analyst")
        self.assertEqual(len(result["next_tasks"]), 0)

    def test_comma_next_as_parallel(self):
        # This is the "Python vs Rust" failure case
        result = mock_parse_decision("NEXT: researcher_python, researcher_rust\nReasoning...", self.roles)
        self.assertEqual(result["next_agent"], "PARALLEL")
        self.assertEqual(len(result["next_tasks"]), 2)
        self.assertEqual(result["next_tasks"][0]["agent"], "researcher_python")
        self.assertEqual(result["next_tasks"][1]["agent"], "researcher_rust")

    def test_standard_parallel(self):
        content = 'PARALLEL: researcher_python: "search py", researcher_rust: "search rust"'
        result = mock_parse_decision(content, self.roles)
        self.assertEqual(result["next_agent"], "PARALLEL")
        self.assertEqual(len(result["next_tasks"]), 2)
        self.assertEqual(result["next_tasks"][0]["instruction"], "search py")

    def test_bracketed_names(self):
        result = mock_parse_decision("NEXT: [researcher_python], [researcher_rust]", self.roles)
        self.assertEqual(result["next_agent"], "PARALLEL")
        self.assertEqual(result["next_tasks"][0]["agent"], "researcher_python")

    def test_hybrid_prefix(self):
        # The specific failure case from Jan 6
        content = 'NEXT: PARALLEL: researcher_python: "search py", researcher_rust: "search rust"'
        result = mock_parse_decision(content, self.roles)
        self.assertEqual(result["next_agent"], "PARALLEL")
        self.assertEqual(len(result["next_tasks"]), 2)
        self.assertEqual(result["next_tasks"][0]["agent"], "researcher_python")

    def test_multiline_decision(self):
        # The specific failure from the Jan 8 Baseline run
        content = "We need more data.\n\nNEXT: analyst\nBecause reason."
        result = mock_parse_decision(content, self.roles)
        self.assertEqual(result["next_agent"], "analyst")

    def test_multiline_parallel(self):
        content = "Starting research phase.\nPARALLEL: researcher_python: \"X\", researcher_rust: \"Y\""
        result = mock_parse_decision(content, self.roles)
        self.assertEqual(result["next_agent"], "PARALLEL")
        self.assertEqual(len(result["next_tasks"]), 2)

if __name__ == "__main__":
    unittest.main()
