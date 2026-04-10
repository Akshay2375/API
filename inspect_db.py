import sqlite3

c = sqlite3.connect('CETrankDB.db')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
for table in tables:
    print(f"Table: {table[0]}")
    columns = c.execute(f"PRAGMA table_info('{table[0]}');").fetchall()
    for col in columns:
        print(f"  {col[1]}")
