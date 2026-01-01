import inspect
import requests
import os
from typing import Callable, Dict, List
from dataclasses import dataclass
from flexi.config.settings import settings

@dataclass
class ToolMetadata:
    """Metadata about a tool for introspection by the architect."""
    name: str
    description: str
    docstring: str
    parameters: Dict[str, str]

class ToolsRegistry:
    """Centralized registry of tools with metadata for architect awareness."""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
    
    def register(self, func: Callable) -> Callable:
        """Decorator to register a tool and extract its metadata."""
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
            parameters=parameters
        )
        return func
    
    def get_tool(self, name: str) -> Callable:
        return self.tools.get(name)
    
    def list_all_metadata(self) -> List[ToolMetadata]:
        return list(self.metadata.values())
    
    def get_metadata_text(self) -> str:
        text = "AVAILABLE TOOLS:\n\n"
        for meta in self.list_all_metadata():
            text += f"Tool: {meta.name}\n"
            text += f"Description: {meta.description}\n"
            text += f"Docstring:\n{meta.docstring}\n"
            text += f"Parameters: {meta.parameters}\n\n"
        return text

# Global registry instance
tools_registry = ToolsRegistry()

# ============================================================================
# SEARCH TOOLS
# ============================================================================

@tools_registry.register
def search_tavily(query: str, search_depth: str = "smart", num_results: int = 5) -> str:
    """
    Search the web using Tavily API for high-quality, research-oriented results.
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

@tools_registry.register
def search_serper(query: str, num_results: int = 5) -> str:
    """
    Search Google using Serper API. Good for general web search and news.
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

@tools_registry.register
def crawl_jina(url: str) -> str:
    """
    Crawl a URL and convert its content to clean markdown using Jina Reader.
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
# MOCK TOOLS
# ============================================================================

@tools_registry.register
def search_academic_literature(query: str, num_results: int = 10) -> str:
    """Search academic literature and papers related to a query (Mock)."""
    return f"[Mock] Found {num_results} papers for query: '{query}'"

@tools_registry.register
def clarify_research_scope(research_question: str) -> str:
    """Clarify and break down the research question (Mock)."""
    return f"[Mock] Clarified scope for: {research_question}"

@tools_registry.register
def summarize_findings(findings: str) -> str:
    """Synthesize and summarize research findings (Mock)."""
    return "[Mock] Summary of findings..."

@tools_registry.register
def generate_report_section(section_type: str, findings: str) -> str:
    """Generate a formatted report section (Mock)."""
    return f"[Mock] Generated {section_type} section."

@tools_registry.register
def validate_assumptions(claim: str, context: str = "") -> str:
    """Validate critical assumptions (Mock)."""
    return f"[Mock] Validation of claim: '{claim}'"
