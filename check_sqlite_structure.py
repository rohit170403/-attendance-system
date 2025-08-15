#!/usr/bin/env python3
"""
Check SQLite Database Structure
"""

import sqlite3
import os

def check_sqlite_structure():
    """Check the structure of SQLite database"""
    sqlite_path = "instance/attendance.db"
    
    if not os.path.exists(sqlite_path):
        print("❌ SQLite database not found")
        return
    
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    print("📊 SQLite Database Structure")
    print("=" * 50)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Table: {table_name}")
        print("-" * 30)
        
        # Get table structure
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        rows = cursor.fetchall()
        
        if rows:
            print(f"\n  Sample data ({len(rows)} rows):")
            for i, row in enumerate(rows, 1):
                print(f"    Row {i}: {row}")
        else:
            print("  No data found")
    
    conn.close()

if __name__ == "__main__":
    check_sqlite_structure()
