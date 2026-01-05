"""
Enhanced Tools Registry with Better Architect Visibility

Each tool now includes:
- Detailed description of capabilities
- When to use (and when NOT to use)
- Output quality expectations
- Cost/performance characteristics
- Example queries
- Parameter guidance
"""

import inspect
import requests
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from flexi.config.settings import settings


@dataclass
class ToolMetadata:
    """Metadata about a tool for introspection by the architect."""
    name: str
    description: str
    docstring: str
    parameters: Dict[str, str]
    use_cases: List[str] = None
    output_quality: str = "medium"  # low, medium, high
    latency: str = "medium"  # fast, medium, slow
    cost: str = "cheap"  # free, cheap, expensive
    reliability: str = "production"  # experimental, beta, production
    best_for: str = ""
    avoid_when: str = ""


class ToolsRegistry:
    """Centralized registry of tools with rich metadata for architect awareness."""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
    
    def register(
        self,
        use_cases: List[str] = None,
        output_quality: str = "medium",
        latency: str = "medium",
        cost: str = "cheap",
        reliability: str = "production",
        best_for: str = "",
        avoid_when: str = ""
    ):
        """Decorator to register a tool with rich metadata."""
        def decorator(func: Callable) -> Callable:
            name = func.__name__
            docstring = inspect.getdoc(func) or ""
            
            # Extract parameters from signature
            sig = inspect.signature(func)
            parameters = {
                param_name: str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                for param_name, param in sig.parameters.items()
                if param_name != "self"
            }
            
            # First line of docstring is description
            description = docstring.split('\n')[0] if docstring else name
            
            self.tools[name] = func
            self.metadata[name] = ToolMetadata(
                name=name,
                description=description,
                docstring=docstring,
                parameters=parameters,
                use_cases=use_cases or [],
                output_quality=output_quality,
                latency=latency,
                cost=cost,
                reliability=reliability,
                best_for=best_for,
                avoid_when=avoid_when
            )
            return func
        return decorator
    
    def get_tool(self, name: str) -> Callable:
        return self.tools.get(name)
    
    def call_tool(self, name: str, **kwargs) -> Any:
        """Call a registered tool by name with arguments."""
        tool_func = self.get_tool(name)
        if not tool_func:
            raise ValueError(f"Tool '{name}' not found in registry.")
        
        # In this implementation, tools are just functions
        return tool_func(**kwargs)
    
    def list_all_metadata(self) -> List[ToolMetadata]:
        return list(self.metadata.values())
    
    def get_metadata_text(self) -> str:
        """Generate comprehensive tool descriptions for architect."""
        text = "AVAILABLE TOOLS FOR ARCHITECT:\n\n"
        for meta in self.list_all_metadata():
            text += f"Tool: {meta.name}\n"
            text += f"Description: {meta.description}\n"
            text += f"Reliability: {meta.reliability} | Quality: {meta.output_quality} | Latency: {meta.latency} | Cost: {meta.cost}\n"
            if meta.best_for:
                text += f"Best for: {meta.best_for}\n"
            if meta.avoid_when:
                text += f"Avoid when: {meta.avoid_when}\n"
            if meta.use_cases:
                text += f"Use cases: {', '.join(meta.use_cases)}\n"
            text += f"Parameters: {meta.parameters}\n"
            text += f"Docstring:\n{meta.docstring}\n"
            text += "-" * 80 + "\n\n"
        return text


# Global registry instance
tools_registry = ToolsRegistry()


# ============================================================================
# MCP TOOL INTEGRATION
# ============================================================================

# Initialize MCP tools if configured
try:
    from flexi.core.mcp_manager import MCPToolManager
    import logging
    
    logger = logging.getLogger(__name__)
    mcp_manager = MCPToolManager()
    
    # Register MCP servers from settings
    for server_name, config in settings.MCP_SERVERS.items():
        if config.get("enabled", False):
            logger.info(f"Registering MCP server: {server_name}")
            success = mcp_manager.register_server(
                server_name, 
                config["command"], 
                config.get("args", [])
            )
            if success:
                logger.info(f"MCP server '{server_name}' registered successfully")
    
    # Discover and register all tools from MCP servers
    num_tools = mcp_manager.discover_and_register_tools(tools_registry)
    logger.info(f"Registered {num_tools} MCP tools")
    
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"MCP integration failed (non-fatal): {e}")
    # Continue without MCP tools - this is non-fatal


# ============================================================================
# SEARCH TOOLS
# ============================================================================


@tools_registry.register(
    use_cases=["research", "technical topics", "recent data", "quality sources"],
    output_quality="high",
    latency="medium",
    cost="cheap",
    reliability="production",
    best_for="Deep technical research, academic topics, recent developments, comprehensive fact-finding",
    avoid_when="Simple definitions, quick facts, when Serper is sufficient"
)
def search_tavily(query: str, search_depth: str = "smart", num_results: int = 5) -> str:
    """
    Search the web using Tavily API for high-quality, research-oriented results.
    
    Provides comprehensive search with content summaries and source quality filtering.
    Excellent for technical research and finding credible sources.
    
    Parameters:
    - query (str): Search query. Use specific technical terms for best results.
      Example: "FastAPI performance benchmarks 2024"
    - search_depth (str): "basic" (fast, standard) or "smart" (comprehensive, slower)
      Default: "smart" - recommended for research tasks
    - num_results (int): Number of results (5-20 recommended, max 20)
      Default: 5
    
    Returns:
    - Formatted string with title, URL, and content summary for each result
    - Content includes relevance analysis
    
    Example queries:
    - "Python FastAPI async performance vs Rust Actix"
    - "Rust borrow checker learning curve real experience"
    - "Docker containerization Rust vs Python production"
    
    Cost: ~$0.001-0.003 per query (cheap API)
    """
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return "Error: TAVILY_API_KEY not found in environment."
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": num_results
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        formatted = []
        for res in results:
            formatted.append(f"Title: {res.get('title')}\nURL: {res.get('url')}\nContent: {res.get('content')}\n")
        return "\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Error calling Tavily API: {str(e)}"


@tools_registry.register(
    use_cases=["quick search", "news", "general queries", "speed over depth"],
    output_quality="medium",
    latency="fast",
    cost="cheap",
    reliability="production",
    best_for="Quick fact-finding, breaking news, general web search, when speed is priority",
    avoid_when="Deep technical research, need content summaries, require credibility assessment"
)
def search_serper(query: str, num_results: int = 5) -> str:
    """
    Search Google using Serper API for fast, general web search results.
    
    Good for quick lookups, breaking news, and general information.
    Faster than Tavily but less comprehensive analysis.
    
    Parameters:
    - query (str): Google search query
      Example: "latest Python release date"
    - num_results (int): Number of results (1-20, default 5)
    
    Returns:
    - Formatted results with title, URL, and snippet
    - Results sorted by Google ranking
    
    Example queries:
    - "Rust web framework comparison 2024"
    - "Python async programming tutorial"
    - "Docker performance overhead"
    
    Cost: Free tier available, ~$0.0005 per query (very cheap)
    Latency: ~1-2 seconds typical
    """
    api_key = settings.SERPER_API_KEY
    if not api_key:
        return "Error: SERPER_API_KEY not found in environment."
    
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload = {"q": query, "num": num_results}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        organic = data.get("organic", [])
        formatted = []
        for res in organic:
            formatted.append(f"Title: {res.get('title')}\nURL: {res.get('link')}\nSnippet: {res.get('snippet')}\n")
        return "\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Error calling Serper API: {str(e)}"


@tools_registry.register(
    use_cases=["content extraction", "page analysis", "markdown conversion"],
    output_quality="high",
    latency="fast",
    cost="cheap",
    reliability="production",
    best_for="Extracting full content from URLs, converting HTML to markdown, deep page analysis",
    avoid_when="Quick title/snippet lookup, don't need full content"
)
def crawl_jina(url: str) -> str:
    """
    Crawl a URL and convert its content to clean markdown using Jina Reader API.
    
    Extracts full page content and converts to structured markdown.
    Excellent for analyzing documents, blog posts, documentation pages.
    
    Parameters:
    - url (str): Full URL to crawl
      Example: "https://example.com/article"
    
    Returns:
    - Full page content in clean markdown format
    - Removes navigation, ads, clutter
    - Preserves structure and formatting
    
    Example use cases:
    - Extract full blog post or article
    - Convert documentation page to markdown
    - Get clean content from news articles
    - Analyze white papers or research pages
    
    Cost: ~$0.001 per request (cheap)
    Latency: 2-5 seconds typical
    Reliability: Good - handles most websites
    """
    api_key = settings.JINA_API_KEY
    jina_url = f"https://r.jina.ai/{url}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.get(jina_url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error calling Jina Reader API: {str(e)}"


# ============================================================================
# ANALYSIS TOOLS
# ============================================================================


@tools_registry.register(
    use_cases=["assumption validation", "claim verification", "critical review"],
    output_quality="medium",
    latency="fast",
    cost="free",
    reliability="beta",
    best_for="Validating critical assumptions, checking claim validity, cross-referencing",
    avoid_when="Definitive fact-checking (use search tools), need external sources"
)
def validate_assumptions(claim: str, context: str = "") -> str:
    """
    Validate critical assumptions in research findings.
    
    Reviews claims for internal consistency and logical validity.
    Currently MOCK - should integrate with fact-checking service.
    
    Parameters:
    - claim (str): The assumption or claim to validate
    - context (str, optional): Additional context about the claim
    
    Returns:
    - Validation result with confidence level
    - Suggests search queries if validation needed
    
    Example:
    - Claim: "Rust has 20x lower memory usage than Python"
    - Output: "Needs context: depends on framework and workload. Recommend searching..."
    
    Status: MOCK - Implementation pending with fact-checking API
    """
    return f"[Mock] Validating claim: '{claim}' with context: '{context}'"


@tools_registry.register(
    use_cases=["synthesis", "finding summarization", "key insight extraction"],
    output_quality="medium",
    latency="fast",
    cost="free",
    reliability="beta",
    best_for="Condensing findings into key points, identifying patterns across sources",
    avoid_when="Need final formatted report (use write tools)"
)
def summarize_findings(findings: str) -> str:
    """
    Synthesize and summarize research findings into key insights.
    
    Extracts main points, identifies patterns, highlights contradictions.
    Currently MOCK - should integrate with summarization agent.
    
    Parameters:
    - findings (str): Raw findings text to summarize
    
    Returns:
    - Condensed summary with key points and patterns
    
    Status: MOCK - Implementation pending
    """
    return f"[Mock] Summarizing findings..."


@tools_registry.register(
    use_cases=["report generation", "formatted output", "structured content"],
    output_quality="medium",
    latency="medium",
    cost="free",
    reliability="beta",
    best_for="Generating formatted report sections, structuring findings",
    avoid_when="Complex multi-section reports (use writer agent)"
)
def generate_report_section(section_type: str, findings: str) -> str:
    """
    Generate a formatted report section from findings.
    
    Creates structured sections like Executive Summary, Key Findings, Analysis, etc.
    Currently MOCK - should integrate with writer agent.
    
    Parameters:
    - section_type (str): Type of section ("summary", "findings", "analysis", "conclusion")
    - findings (str): Content for the section
    
    Returns:
    - Formatted markdown section
    
    Status: MOCK - Implementation pending
    """
    return f"[Mock] Generated {section_type} section."


# ============================================================================
# RESEARCH TOOLS
# ============================================================================


@tools_registry.register(
    use_cases=["academic research", "peer-reviewed sources", "scholarly content"],
    output_quality="high",
    latency="slow",
    cost="cheap",
    reliability="beta",
    best_for="Finding peer-reviewed papers, academic citations, scholarly sources",
    avoid_when="Breaking news, commercial information, quick facts"
)
def search_academic_literature(query: str, num_results: int = 10) -> str:
    """
    Search academic literature and peer-reviewed papers.
    
    Finds scholarly sources, research papers, and academic content.
    Currently MOCK - should integrate with academic search API (PubMed, arXiv, Google Scholar).
    
    Parameters:
    - query (str): Research topic or paper search
    - num_results (int): Number of papers to find (default 10)
    
    Returns:
    - List of academic papers with citation info
    - Links to paper abstracts
    
    Status: MOCK - Implementation pending
    """
    return f"[Mock] Found {num_results} papers for query: '{query}'"


@tools_registry.register(
    use_cases=["scope clarification", "question analysis", "research planning"],
    output_quality="medium",
    latency="fast",
    cost="free",
    reliability="beta",
    best_for="Breaking down complex questions, clarifying scope, identifying research dimensions",
    avoid_when="Simple direct questions"
)
def clarify_research_scope(research_question: str) -> str:
    """
    Clarify and break down complex research questions into manageable sub-questions.
    
    Identifies scope boundaries, key dimensions, and research areas.
    Currently MOCK - should integrate with clarifier agent logic.
    
    Parameters:
    - research_question (str): The question to clarify
    
    Returns:
    - Clarified scope with:
      * Sub-questions
      * Key dimensions to investigate
      * Scope boundaries (include/exclude)
      * Undefined terms defined
    
    Example:
    Input: "Compare Python vs Rust for web backends"
    Output:
    - Sub-Q1: Performance metrics (throughput, latency, memory)?
    - Sub-Q2: Developer experience (learning curve, ecosystem)?
    - Scope: Web backends only (not systems programming)
    - Key terms: "high-performance" = 1000+ req/s
    
    Status: MOCK - Implementation pending with clarifier prompt integration
    """
    return f"[Mock] Clarified scope for: {research_question}"


# ============================================================================
# KNOWLEDGE BASE TOOLS
# ============================================================================


@tools_registry.register(
    use_cases=["listing available knowledge", "checking database content"],
    output_quality="high",
    latency="fast",
    cost="free",
    reliability="production",
    best_for="Finding out what knowledge bases (collections) are available to query"
)
def list_knowledge_bases() -> str:
    """List all available Knowledge Base collections."""
    try:
        db_path = os.path.join(os.getcwd(), settings.CHROMA_DB_DIR)
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        if not collections:
            return "No knowledge bases found."
        
        return "Available Knowledge Bases:\n" + "\n".join([f"- {c.name}" for c in collections])
    except Exception as e:
        return f"Error listing knowledge bases: {e}"


@tools_registry.register(
    use_cases=["retrieving internal documents", "checking past research", "accessing knowledge base"],
    output_quality="high",
    latency="fast",
    cost="free",
    reliability="production",
    best_for="Accessing stored documents, company knowledge, or previously ingested text",
    avoid_when="Searching for live/external web data (use Tavily/Serper)"
)
def query_knowledge_base(query: str, collection_name: str = None, n_results: int = 3) -> str:
    """
    Query the local knowledge base (vector database) for relevant documents.
    
    Retrieves semantic matches from documents in the specific collection.
    
    Parameters:
    - query (str): The semantic search query.
    - collection_name (str, optional): The specific collection to search. 
      If not provided, tries 'flexi_knowledge_base' or returns error if ambiguous.
      Use 'list_knowledge_bases' to see options.
    - n_results (int): Number of document chunks to retrieve (default 3).
    
    Returns:
    - Relevant document excerpts with source metadata.
    """
    try:
        db_path = os.path.join(os.getcwd(), settings.CHROMA_DB_DIR)
        client = chromadb.PersistentClient(path=db_path)
        
        # Determine collection
        target_name = collection_name or settings.CHROMA_COLLECTION_NAME
        
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        try:
            collection = client.get_collection(name=target_name, embedding_function=ef)
        except Exception:
            return f"Collection '{target_name}' not found. Available: {list_knowledge_bases()}"
            
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        if not documents:
            return f"No relevant documents found in '{target_name}'."
            
        formatted_output = f"Found the following relevant documents in '{target_name}':\n"
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            source = meta.get('source', 'Unknown')
            formatted_output += f"\n[Result {i+1}] (Source: {source})\n{doc}\n"
            
        return formatted_output
        
    except Exception as e:
        return f"Error querying knowledge base: {e}"
        
@tools_registry.register(
    use_cases=["javascript research", "language nuances", "js patterns", "deep js concepts"],
    output_quality="high",
    latency="fast",
    cost="free",
    reliability="production",
    best_for="Understanding complex JavaScript concepts (closures, prototypes, async) from 'You Don't Know JS'",
    avoid_when="Searching for general web dev news or frameworks not covered in core JS"
)
def query_javascript_kb(query: str, n_results: int = 3) -> str:
    """
    Query the JavaScript knowledge base ('You Don't Know JS' book series).
    
    Accesses deep technical explanations of JavaScript core mechanisms.
    Perfect for questions about scope, closures, this, prototypes, types, and async.
    
    Parameters:
    - query (str): Semantic query about JavaScript.
    - n_results (int): Number of results (default 3).
    """
    return query_knowledge_base(query, collection_name="javascript-core", n_results=n_results)


@tools_registry.register(
    use_cases=["code review", "engineering standards", "google style guide", "best practices"],
    output_quality="high",
    latency="fast",
    cost="free",
    reliability="production",
    best_for="Checking Google's engineering practices, code review guidelines, and style standards",
    avoid_when="Looking for specific library documentation (unless likely in standard guides)"
)
def query_engineering_practices_kb(query: str, n_results: int = 3) -> str:
    """
    Query the Google Engineering Practices knowledge base.
    
    Accesses Google's official documentation on code reviews, style guides, and engineering culture.
    Use this to resolve debates about code quality, review etiquette, or standard processes.
    
    Parameters:
    - query (str): Semantic query about engineering practices.
    - n_results (int): Number of results (default 3).
    """
    return query_knowledge_base(query, collection_name="google-engineering-standards", n_results=n_results)


