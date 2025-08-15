#!/usr/bin/env python3
"""
Database Query Script for Attendance System
"""

import os
import sys
from tabulate import tabulate

# Set environment variables directly
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'postgresql://sanket:LU9ZK9Fyiu0jwUxcfOBzZkNwNLImA9ag@dpg-d2fe9cer433s73b86oug-a.singapore-postgres.render.com/attendance_ostk'

def run_query(query, description=""):
    """Run a custom SQL query"""
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        app = create_app()
        
        with app.app_context():
            if description:
                print(f"\n🔍 {description}")
                print("-" * 50)
            
            with db.engine.connect() as connection:
                result = connection.execute(text(query))
                
                if result.returns_rows:
                    # Get column names
                    columns = result.keys()
                    
                    # Get all rows
                    rows = result.fetchall()
                    
                    if rows:
                        print(tabulate(rows, headers=columns, tablefmt='grid'))
                        print(f"Total rows: {len(rows)}")
                    else:
                        print("No results found.")
                else:
                    print("Query executed successfully (no results to display).")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run common database queries"""
    print("🔍 Database Query Tool for Attendance System")
    print("=" * 60)
    
    # List all tables
    run_query("""
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """, "Database Tables")
    
    # Show table structures
    run_query("""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'user'
        ORDER BY ordinal_position;
    """, "User Table Structure")
    
    # Count records in each table
    run_query("""
        SELECT 
            'user' as table_name, COUNT(*) as record_count FROM "user"
        UNION ALL
        SELECT 
            'subject' as table_name, COUNT(*) as record_count FROM subject
        UNION ALL
        SELECT 
            'enrollment' as table_name, COUNT(*) as record_count FROM enrollment
        UNION ALL
        SELECT 
            'qr_code' as table_name, COUNT(*) as record_count FROM qr_code
        UNION ALL
        SELECT 
            'attendance' as table_name, COUNT(*) as record_count FROM attendance;
    """, "Record Counts by Table")
    
    print("\n✅ Database queries completed!")

if __name__ == "__main__":
    main()
