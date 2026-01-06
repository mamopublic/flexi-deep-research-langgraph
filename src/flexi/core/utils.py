import re

def slugify_question(question: str, max_words: int = 5) -> str:
    """
    Convert a question into a folder-friendly slug.
    Example: "Compare Python vs Rust for web backends" -> "compare_python_vs_rust_for"
    """
    # Remove non-alphanumeric characters except spaces
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', question).lower()
    
    # Split into words and take the first N
    words = clean.split()
    slug_words = words[:max_words]
    
    return "_".join(slug_words)
