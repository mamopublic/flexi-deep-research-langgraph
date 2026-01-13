import chromadb
import os
from flexi.config.settings import settings

db_path = os.path.join(os.getcwd(), settings.CHROMA_DB_DIR)
client = chromadb.PersistentClient(path=db_path)
collections = client.list_collections()

print("Available Collections:")
for c in collections:
    print(f"- {c.name}")
