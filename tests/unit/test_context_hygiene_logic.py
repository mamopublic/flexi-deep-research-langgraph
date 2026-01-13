import unittest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from flexi.agents.graph_builder import create_agent_executor
from flexi.agents.architect import AgentConfig

class TestContextHygieneLogic(unittest.TestCase):
    def setUp(self):
        self.agent_config = AgentConfig(
            role="researcher",
            description="test researcher",
            tools=["search_tavily"],
            system_prompt="You are a researcher.",
            context_dependencies=["analyst"]
        )
        self.agent_name = "js_researcher"
        self.model_name = "anthropic/claude-sonnet-4"

    @patch("flexi.agents.graph_builder.get_llm")
    def test_search_memory_restoration(self, mock_get_llm):
        # Setup mock LLM to capture messages
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Create executor
        executor = create_agent_executor(self.agent_name, self.agent_config, self.model_name)
        
        # Create a state with "Messy" history
        # 1. Someone else's tool call (should be ignored)
        # 2. This agent's previous tool call (should be restored)
        # 3. Previous supervisor instruction
        history = [
            SystemMessage(content="Ignore me"),
            AIMessage(content="Instruction 1", name="supervisor"),
            AIMessage(content="I am doing a search", name="js_researcher", tool_calls=[{"name": "search_tavily", "args": {"q": "test"}, "id": "1"}]),
            ToolMessage(content="Search result", tool_call_id="1"),
            AIMessage(content="Analyst thinking...", name="analyst"),
            HumanMessage(content="Next step: refine research")
        ]
        
        state = {
            "research_question": "What is AI?",
            "messages": history,
            "findings": {"analyst": "Analyst findings"},
            "iteration_count": 1
        }
        
        # Execute (mocking tools_registry too to avoid real calls)
        with patch("flexi.agents.graph_builder.tools_registry") as mock_tools:
            mock_llm.invoke.return_value = MagicMock(content="Final answer", tool_calls=[])
            executor(state)
            
            # Capture the messages sent to LLM
            sent_messages = mock_llm.invoke.call_args[0][0]
            
            # VERIFICATIONS:
            
            # 1. SystemMessage should be first
            self.assertIsInstance(sent_messages[0], SystemMessage)
            
            # 2. js_researcher's history SHOULD be present
            has_my_history = any(
                isinstance(m, AIMessage) and getattr(m, 'name', None) == "js_researcher" 
                for m in sent_messages
            )
            self.assertTrue(has_my_history, "Agent's own history was NOT restored")
            
            # 3. analyst's history (non-findings) SHOULD NOT be present
            # Analysts are only in findings, not in episodic message history
            has_analyst_msg = any(
                isinstance(m, AIMessage) and getattr(m, 'name', None) == "analyst" 
                for m in sent_messages
            )
            self.assertFalse(has_analyst_msg, "Other agent's raw messages leaked into context")
            
            # 4. ContextProvider (Findings) SHOULD be present (from analyst dependency)
            has_context_provider = any(
                isinstance(m, AIMessage) and getattr(m, 'name', None) == "ContextProvider" 
                for m in sent_messages
            )
            self.assertTrue(has_context_provider, "Findings from dependencies were NOT restored")

            print("✅ Context Hygiene Logic Verified: Filtered episodic memory correctly.")

if __name__ == "__main__":
    unittest.main()
