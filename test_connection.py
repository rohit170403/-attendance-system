#!/usr/bin/env python3
"""
Test PostgreSQL Connection Script
"""

import os
import sys

# Set environment variables directly
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'postgresql://sanket:LU9ZK9Fyiu0jwUxcfOBzZkNwNLImA9ag@dpg-d2fe9cer433s73b86oug-a.singapore-postgres.render.com/attendance_ostk'

def test_connection():
    """Test the PostgreSQL connection"""
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        print("🚀 Testing PostgreSQL Connection...")
        print("=" * 50)
        
        app = create_app()
        
        with app.app_context():
            print("✅ Flask app created successfully")
            
            # Test database connection
            print("🔌 Testing database connection...")
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                print("✅ Database connection successful!")
            
            # Create tables
            print("📋 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # List tables
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Available tables: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_connection():
        print("\n🎉 Connection test successful!")
        print("Your application is ready to use with PostgreSQL!")
    else:
        print("\n❌ Connection test failed!")
        sys.exit(1)
