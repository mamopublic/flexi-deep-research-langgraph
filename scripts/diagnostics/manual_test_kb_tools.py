from flexi.core.tools import query_javascript_kb, query_engineering_practices_kb, list_knowledge_bases
import os

print("\n--- Listing Knowledge Bases ---")
print(list_knowledge_bases())

print("\n\n--- Testing JavaScript KB (Closures) ---")
print(query_javascript_kb("What is a closure?"))

print("\n\n--- Testing Engineering KB (Code Review) ---")
print(query_engineering_practices_kb("What are the code review guidelines?"))
