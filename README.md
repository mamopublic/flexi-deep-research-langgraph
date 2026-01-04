# Flexi Deep Research LangGraph

A flexible, agentic deep research system built with LangGraph.

## Overview
## Overview
This system uses an "Architect" agent to dynamically design a team of research agents based on a user's query. It supports dynamic role creation, tool delegation, and multiple LLM providers (Anthropic, OpenRouter).

## Key Features
- **Dynamic Architecture**: Architect designs custom teams (Supervisor/Workers).
- **Hybrid Context**: Efficient context window management.
- **Persistent Knowledge Base**: Local Chroma vector DB for long-term memory (See [Knowledge Base Setup](docs/knowledge_base_setup.md)).


## Structure
- `src/`: Source code
  - `config/`: Configuration and prompts
  - `core/`: Core utilities (LLM, State, Tools)
  - `agents/`: Agent implementations
- `tests/`: Project tests
- `docs/`: Documentation
- `perplexity/`: Initial prototype (kept for reference)

## Development
1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
2. Create `.env` file (see `.env.example`).
3. Run tests:
   ```bash
   pytest
   ```
