import sqlite3
import os

path = os.path.join(os.getcwd(), 'lapdoctor_cache.db')
print('DB exists:', os.path.exists(path))
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','index','view')")
print(cur.fetchall())
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='scan_history'")
print(cur.fetchall())
conn.close()
