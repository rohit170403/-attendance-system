#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script for Attendance System
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_postgresql_connection():
    """Check if PostgreSQL connection is properly configured"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("Please create a .env file with your PostgreSQL configuration")
        print("See env_template.txt for reference")
        return False
    
    if database_url.startswith('sqlite://'):
        print("⚠️  Currently using SQLite database")
        print("To use PostgreSQL, update your DATABASE_URL in .env file")
        return False
    
    if database_url.startswith('postgresql://'):
        print("✅ PostgreSQL configuration detected")
        return True
    
    print("❌ Invalid DATABASE_URL format")
    return False

def setup_database():
    """Setup the database tables"""
    try:
        from app import create_app, db
        from app.models.models import User, Subject, Attendance, QRCode
        
        app = create_app()
        
        with app.app_context():
            print("Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if tables exist
            tables = db.engine.table_names()
            print(f"📋 Available tables: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False
    
    return True

def run_migrations():
    """Run database migrations"""
    try:
        print("Running database migrations...")
        os.system("flask db upgrade")
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False

def main():
    print("🚀 PostgreSQL Database Setup for Attendance System")
    print("=" * 50)
    
    # Check connection
    if not check_postgresql_connection():
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        sys.exit(1)
    
    print("\n🎉 PostgreSQL setup completed successfully!")
    print("You can now run your application with: python run.py")

if __name__ == "__main__":
    main()
