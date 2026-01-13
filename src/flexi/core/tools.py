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
from typing import Callable, Dict, List, Any, Optional
from duckduckgo_search import DDGS
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


# Note: No decorator here, keeping it available but hidden from public registry
def search_tavily(query: str, search_depth: str = "advanced", num_results: int = 5) -> str:
    """
    Search the web using Tavily API for high-quality, research-oriented results.
    
    Provides comprehensive search with content summaries and source quality filtering.
    Excellent for technical research and finding credible sources.
    
    Parameters:
    - query (str): Search query. Use specific technical terms for best results.
      Example: "FastAPI performance benchmarks 2024"
    - search_depth (str): "basic" (fast, standard) or "advanced" (comprehensive, slower, costs 2 credits)
      Default: "advanced" - recommended for research tasks
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
    
    # Map 'smart' to 'advanced' for backward compatibility with older prompts/models
    if search_depth == "smart":
        search_depth = "advanced"
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": min(max(num_results, 1), 20) # Ensure 1-20 range
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            error_msg = f"Tavily API Error {response.status_code}: {response.text}"
            return f"Error calling Tavily API: {error_msg}"
            
        data = response.json()
        results = data.get("results", [])
        formatted = []
        for res in results:
            formatted.append(f"Title: {res.get('title')}\nURL: {res.get('url')}\nContent: {res.get('content')}\n")
        return "\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Error calling Tavily API: {str(e)}"


# Note: No decorator here, keeping it available but hidden from public registry
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


def search_ddg(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo (Free, no API key required).
    
    Reliable but basic search. Best used as a persistent fallback.
    Uses the duckduckgo-search library for high-quality results.
    """
    try:
        results = []
        with DDGS() as ddgs:
            ddg_gen = ddgs.text(query, max_results=num_results)
            for r in ddg_gen:
                results.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
        
        return "\n".join(results) if results else "No DuckDuckGo results found."
    except Exception as e:
        return f"Error calling DuckDuckGo: {str(e)}"


@tools_registry.register(
    use_cases=["general web search", "research", "quick lookups"],
    output_quality="high",
    latency="medium",
    cost="cheap",
    reliability="production",
    best_for="Generic web search without caring about the underlying provider",
    avoid_when="You explicitly want to compare Tavily vs Serper vs DuckDuckGo"
)
def web_search(
    query: str,
    num_results: int = 5,
    mode: str = "fallback"  # "quality" or "fallback"
) -> str:
    """
    General web search tool that hides the underlying provider choice.

    Parameters:
    - query (str): Search query
    - num_results (int): Desired number of results (1-20)
    - mode (str):
        - "quality": prefer Tavily-style results (research-oriented)
        - "fast": prefer Serper-style results (Google SERP)
        - "fallback": use cheaper/free providers

    This is meant for research on agent architectures, not provider selection.
    """
    # Normalize num_results
    num_results = max(1, min(num_results, 20))

    # Simple routing logic: keep it boring on purpose
    # so it doesn't become the thing you're studying.
    if mode == "fallback":
        # Try Serper first, fall back to Tavily, then DDG
        out = search_serper(query=query, num_results=num_results)
        if out.lower().startswith("error"):
            out = search_tavily(query=query, search_depth="basic", num_results=num_results)
        if out.lower().startswith("error"):
            out = search_ddg(query=query, num_results=num_results)
        return out

    elif mode == "fast":
        # Prefer Serper
        out = search_serper(query=query, num_results=num_results)
        if out.lower().startswith("error"):
            out = search_ddg(query=query, num_results=num_results)
        return out

    else:
        # mode == "quality" (default)
        out = search_tavily(query=query, search_depth="advanced", num_results=num_results)
        if out.lower().startswith("error"):
            out = search_serper(query=query, num_results=num_results)
        if out.lower().startswith("error"):
            out = search_ddg(query=query, num_results=num_results)
        return out


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

# ============================================================================
# RESEARCH TOOLS
# ============================================================================





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


# Note: No decorator here. This is a helper for specific KB tools.
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


