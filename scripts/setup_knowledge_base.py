"""
Script to initialize and populate the Chroma Knowledge Base.
Run this script to setup the vector database with initial documents.
"""

import os
import argparse
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from flexi.config.settings import settings

def get_chroma_client():
    """Get persistent Chroma client."""
    db_path = os.path.join(os.getcwd(), settings.CHROMA_DB_DIR)
    return chromadb.PersistentClient(path=db_path)

def get_collection(client, name):
    """Get or create a specific knowledge base collection."""
    # Use default all-MiniLM-L6-v2 embedding function
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_or_create_collection(
        name=name,
        embedding_function=sentence_transformer_ef
    )

def list_collections():
    """List all available collections."""
    client = get_chroma_client()
    collections = client.list_collections()
    if not collections:
        print("No collections found.")
        return
    print("\nAvailable Knowledge Bases (Collections):")
    for col in collections:
        print(f"- {col.name} (Count: {col.count()})")

def reset_db(name=None):
    """Reset the database. If name provided, delete only that collection."""
    client = get_chroma_client()
    try:
        if name:
            client.delete_collection(name)
            print(f"Collection '{name}' deleted.")
        else:
            client.reset() # This might not be supported in all versions, safer to delete all collections
            for col in client.list_collections():
                client.delete_collection(col.name)
            print("All collections deleted.")
    except Exception as e:
        print(f"Error resetting DB: {e}")

def ingest_documents(directory: str, collection_name: str = None):
    """Ingest documents into a specific collection."""
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return

    # Determine collection name
    if not collection_name:
        # Create one on the fly based on directory name
        # e.g., kb_sources/You-Dont-Know-JS -> You-Dont-Know-JS
        collection_name = os.path.basename(os.path.normpath(directory))
        print(f"No name provided. Using directory name: '{collection_name}'")
    
    # Sanitize name (Chroma strict naming: alphanumeric, underscores, hyphens)
    safe_name = "".join([c if c.isalnum() or c in "-_" else "_" for c in collection_name])
    if safe_name != collection_name:
        print(f"Sanitized collection name to: '{safe_name}'")
        collection_name = safe_name

    client = get_chroma_client()
    collection = get_collection(client, collection_name)
    
    files_to_process = []
    print(f"Scanning {directory} for .txt and .md files...")
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.txt', '.md')):
                files_to_process.append(os.path.join(root, file))
                
    if not files_to_process:
        print(f"No text/markdown files found in {directory} or its subdirectories")
        return

    print(f"Found {len(files_to_process)} files to ingest into '{collection_name}'...")
    
    ids = []
    documents = []
    metadatas = []
    
    BATCH_SIZE = 100
    
    for filepath in files_to_process:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            chunks = [c for c in content.split('\n\n') if len(c.strip()) > 50]
            rel_path = os.path.relpath(filepath, directory)
            
            for i, chunk in enumerate(chunks):
                safe_id = f"{collection_name}_{rel_path}_{i}".replace('/', '_').replace('\\', '_').replace(' ', '_')
                ids.append(safe_id)
                documents.append(chunk)
                metadatas.append({"source": rel_path, "original_dir": directory, "chunk_index": i})
                
        except Exception as e:
            print(f"Skipping file {filepath}: {e}")
            continue
            
    if documents:
        total = len(documents)
        print(f"Processing {total} chunks...")
        for i in range(0, total, BATCH_SIZE):
            end = min(i + BATCH_SIZE, total)
            print(f"  Upserting batch {i} to {end}...")
            collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )
        print(f"Ingestion matching '{directory}' into '{collection_name}' complete.")
    else:
        print("No valid content found to ingest.")

def query_db(query_text: str, collection_name: str = None, n_results: int = 3):
    """Query a specific collection or the default if configured."""
    client = get_chroma_client()
    
    target_collections = []
    if collection_name:
        target_collections.append(collection_name)
    else:
        # If no name, try default from settings, or list all?
        # For CLI, let's list available if not specified
        cols = client.list_collections()
        if not cols:
            print("No collections exist.")
            return
        print("Collections available:", [c.name for c in cols])
        # Default to the first one for now, or require name
        target_collections.append(cols[0].name)
        print(f"Querying collection: {target_collections[0]}")

    for col_name in target_collections:
        try:
            collection = get_collection(client, col_name)
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            print(f"\n--- Results from '{col_name}' for '{query_text}' ---")
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                print(f"\n[Result {i+1}] (Source: {meta.get('source', 'Unknown')})")
                print(f"{doc[:200]}...")
        except Exception as e:
            print(f"Error querying {col_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage Chroma Knowledge Base")
    parser.add_argument("--reset", action="store_true", help="Reset DB (delete collection). Use --name to delete specific one.")
    parser.add_argument("--ingest", type=str, help="Directory path to ingest")
    parser.add_argument("--name", type=str, help="Name of the collection (database) to use")
    parser.add_argument("--query", type=str, help="Query string")
    parser.add_argument("--list", action="store_true", help="List all collections")
    
    args = parser.parse_args()
    
    if args.list:
        list_collections()
        return

    if args.reset:
        reset_db(args.name)
        return

    if args.ingest:
        ingest_documents(args.ingest, args.name)
        return
        
    if args.query:
        query_db(args.query, args.name)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
