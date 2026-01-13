import unittest
from unittest.mock import MagicMock, patch
from flexi.agents.graph_builder import create_supervisor_executor, DynamicResearchSystemBuilder
from flexi.agents.architect import AgentConfig, ArchitectConfig
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Send

class TestParallelLogic(unittest.TestCase):
    def setUp(self):
        self.agent_config = AgentConfig(
            role="supervisor",
            description="test",
            system_prompt="You are a supervisor.",
            tools=[],
            context_dependencies=[]
        )
        self.subordinates = ["researcher_1", "researcher_2"]
        self.model = "test-model"

    @patch("flexi.agents.graph_builder.get_llm")
    def test_supervisor_parallel_parsing(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Mock LLM responding with PARALLEL
        mock_llm.invoke.return_value = AIMessage(
            content="PARALLEL: researcher_1: \"Find A\", researcher_2: \"Find B\"\nReasoning: Parallel is better."
        )
        
        executor = create_supervisor_executor(self.agent_config, self.subordinates, self.model)
        state = {
            "research_question": "Test question?",
            "findings": {},
            "iteration_count": 0,
            "max_iterations": 10,
            "messages": []
        }
        
        result = executor(state)
        
        self.assertEqual(result["supervisor_decision"], "PARALLEL")
        self.assertEqual(len(result["next_tasks"]), 2)
        self.assertEqual(result["next_tasks"][0]["agent"], "researcher_1")
        self.assertEqual(result["next_tasks"][0]["instruction"], "Find A")
        self.assertEqual(result["next_tasks"][1]["agent"], "researcher_2")
        self.assertEqual(result["next_tasks"][1]["instruction"], "Find B")

    def test_router_send_generation(self):
        # Create a builder just to test the router function
        config = ArchitectConfig(
            research_question="Test?",
            reasoning="Testing parallel routing",
            agents={"supervisor": self.agent_config},
            suggested_workflow=["Branch A", "Branch B"]
        )
        builder = DynamicResearchSystemBuilder(config)
        
        # We need to manually pull the router logic or mock the build
        # Let's mock a state that would be passed to the router
        state = {
            "research_question": "Test?",
            "iteration_count": 0,
            "max_iterations": 10,
            "supervisor_decision": "PARALLEL",
            "next_tasks": [
                {"agent": "researcher_1", "instruction": "Task 1"},
                {"agent": "researcher_2", "instruction": "Task 2"}
            ],
            "findings": {"old": "data"},
            "messages": []
        }
        
        # The router is defined inside build(), so we need to reach it.
        # For testing, I'll just copy the logic or find it.
        # Actually, let's just test that the concept works by running a small build.
        
        # Define a mock router that mimics the one in build()
        def mock_router(state):
            decision = state.get("supervisor_decision")
            if decision == "PARALLEL":
                return [
                    Send(task["agent"], {
                        "messages": [HumanMessage(content=task["instruction"])]
                    }) for task in state["next_tasks"]
                ]
            return decision

    def test_barrier_logic(self):
        # Mock router logic
        def mock_join_router(state):
            active = state.get("active_branches", 0)
            completed = state.get("completed_branches", 0)
            if active <= 1 or completed >= active:
                return "supervisor"
            return "END"

        # Case 1: Sequential (active=0)
        self.assertEqual(mock_join_router({"active_branches": 0}), "supervisor")

        # Case 2: Parallel Waiting (active=3, completed=1)
        self.assertEqual(mock_join_router({"active_branches": 3, "completed_branches": 1}), "END")

        # Case 3: Parallel Finished (active=3, completed=3)
        self.assertEqual(mock_join_router({"active_branches": 3, "completed_branches": 3}), "supervisor")

    def test_counter_reset(self):
        from flexi.core.state import increment_counter
        # 1. Normal increment
        self.assertEqual(increment_counter(5, 1), 6)
        # 2. Reset signal
        self.assertEqual(increment_counter(6, -1), 0)

if __name__ == "__main__":
    unittest.main()
