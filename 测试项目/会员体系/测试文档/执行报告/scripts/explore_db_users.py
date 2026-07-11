import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helpers"))
from db_helper import query

print("--- Tables ---")
tables = query("SHOW TABLES LIKE '%user%'")
for t in tables:
    print(t)
    
tables2 = query("SHOW TABLES LIKE '%member%'")
for t in tables2:
    print(t)
    
tables3 = query("SHOW TABLES LIKE '%customer%'")
for t in tables3:
    print(t)
