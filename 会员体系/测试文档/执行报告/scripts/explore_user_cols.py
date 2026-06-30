import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helpers"))
from db_helper import query

print("--- b2b_user Columns ---")
cols = query("SHOW COLUMNS FROM b2b_user")
for c in cols:
    print(c['Field'], c['Type'])
    
print("--- b2b_user_role Columns ---")
cols = query("SHOW COLUMNS FROM b2b_user_role")
for c in cols:
    print(c['Field'], c['Type'])
