# Knowledge Base Setup

This project uses **Chroma** as a local vector database to store and retrieve documents for the research agents. This allows agents to access a persistent knowledge base of text and markdown files.

The system supports **multiple collections** (independent knowledge bases), allowing agents to query specific domains of knowledge. Our current collections are based on:
- **`javascript-core`**: Ingested from [You-Dont-Know-JS (2nd Edition)](https://github.com/getify/You-Dont-Know-JS/tree/2nd-ed)
- **`google-engineering-standards`**: Ingested from [Google Engineering Practices](https://github.com/google/eng-practices/)

## Prerequisites

Ensure you have installed the project dependencies:

```bash
pip install -e .
```

## Management Script

The `scripts/setup_knowledge_base.py` script is used to manage your local knowledge bases.

### 1. Ingest Documents (Recursive)

To populate a knowledge base with documents from a directory:

```bash
# General usage
python scripts/setup_knowledge_base.py --ingest /path/to/documents --name collection_name

# Example: Ingesting JavaScript books
python scripts/setup_knowledge_base.py --ingest kb_sources/You-Dont-Know-JS --name javascript-core
```

- **Recursive**: The script automatically crawls all subdirectories.
- **Strict Filtering**: Only `.txt` and `.md` files are ingested.
- **Dynamic Naming**: If `--name` is omitted, the script uses the directory's basename as the collection name.

### 2. List Available Collections

To see all currently initialized knowledge bases:

```bash
python scripts/setup_knowledge_base.py --list
```

### 3. Query a Specific Collection

To test retrieval or verify ingestion for a specific knowledge base:

```bash
# Must specify the name if you have multiple
python scripts/setup_knowledge_base.py --query "what are closures?" --name javascript-core
```

### 4. Reset or Delete

To clear data:

```bash
# Delete a specific collection
python scripts/setup_knowledge_base.py --reset --name javascript-core

# Delete EVERYTHING (Clear entire database)
python scripts/setup_knowledge_base.py --reset
```

## Configuration

Settings in `src/flexi/config/settings.py`:
- `CHROMA_DB_DIR`: Directory where data is stored (default: `.chroma_db`).
- `CHROMA_COLLECTION_NAME`: Default collection used if no name is specified in tools.

## Agent Integration

Agents have access to specialized tools to query these databases:
- `query_javascript_kb`: Specifically searches the `javascript-core` collection.
- `query_engineering_practices_kb`: Specifically searches the `google-engineering-standards` collection.
- `list_knowledge_bases`: Allows an agent to see what knowledge is available.

