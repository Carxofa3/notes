#!/usr/bin/env python3
"""
Setup script for AI features
This script will:
1. Run the AI features database migration
2. Check AI dependencies
3. Initialize default AI settings
"""

import os
import sqlite3
from pathlib import Path

def run_ai_migration():
    """Run the database migration for AI features"""
    
    # Database path
    db_path = 'notes.db'  # Adjust this path if your database is elsewhere
    
    # Migration SQL file
    migration_file = 'database/migration_ai_features.sql'
    
    if not os.path.exists(migration_file):
        print(f"Migration file {migration_file} not found!")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read and execute migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement.startswith('--') or not statement:
                continue
            try:
                cursor.execute(statement)
                print(f"✓ Executed: {statement[:50]}...")
            except sqlite3.Error as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠ Column already exists (skipping): {statement[:50]}...")
                elif "already exists" in str(e).lower():
                    print(f"⚠ Table already exists (skipping): {statement[:50]}...")
                else:
                    print(f"✗ Error executing: {statement[:50]}...")
                    print(f"  Error: {e}")
        
        conn.commit()
        conn.close()
        
        print("✓ AI features database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

def check_ai_dependencies():
    """Check if AI-related dependencies are installed"""
    
    required_packages = ['requests', 'numpy', 'PIL']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            else:
                __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is not installed")
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    return True

def verify_ai_setup():
    """Verify that AI features are properly set up"""
    
    try:
        # Test database connection and check tables
        conn = sqlite3.connect('notes.db')
        cursor = conn.cursor()
        
        # Check if new tables exist
        tables_to_check = ['embeddings', 'search_cache']
        for table in tables_to_check:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' is missing")
                return False
        
        # Check if new columns exist in settings table
        cursor.execute("PRAGMA table_info(settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        ai_columns = ['ai_base_url', 'ai_api_key', 'ai_model', 'ai_embedding_model', 'ai_enabled']
        for col in ai_columns:
            if col in columns:
                print(f"✓ Column '{col}' exists in settings table")
            else:
                print(f"✗ Column '{col}' is missing from settings table")
                return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

def main():
    print("🤖 Setting up AI Features for Enhanced Notes App...")
    print("=" * 50)
    
    # Check dependencies
    print("\n1. Checking AI dependencies...")
    if not check_ai_dependencies():
        print("\nSetup failed due to missing dependencies.")
        return
    
    # Run migration
    print("\n2. Running AI features database migration...")
    if not run_ai_migration():
        print("\nSetup failed during database migration.")
        return
    
    # Verify setup
    print("\n3. Verifying AI setup...")
    if not verify_ai_setup():
        print("\nSetup verification failed.")
        return
    
    print("\n" + "=" * 50)
    print("🎉 AI Features setup completed successfully!")
    print("\nNew AI features available:")
    print("• Semantic search with embeddings")
    print("• AI-powered text formatting")
    print("• Drag-and-drop lesson/unit reordering")
    print("• Lesson and unit name editing")
    print("• Real-time search with similarity matching")
    print("• Automatic embedding generation")
    print("• OpenAI-compatible API integration")
    
    print("\nNext steps:")
    print("1. Start your application")
    print("2. Go to Settings > AI Features")
    print("3. Enter your OpenAI API key and base URL")
    print("4. Test the connection")
    print("5. Enable AI features")
    print("6. Generate embeddings for existing notes")
    
    print("\nEnjoy your AI-powered notes app! 🚀")

if __name__ == "__main__":
    main()
