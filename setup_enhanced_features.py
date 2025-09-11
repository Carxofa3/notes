#!/usr/bin/env python3
"""
Setup script for enhanced notes app features
This script will:
1. Run the database migration
2. Create the uploads directory
3. Initialize default settings
"""

import os
import sqlite3
from pathlib import Path

def run_migration():
    """Run the database migration for enhanced features"""
    
    # Database path
    db_path = 'notes.db'  # Adjust this path if your database is elsewhere
    
    # Migration SQL file
    migration_file = 'database/migration_enhanced_features.sql'
    
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
        
        print("✓ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

def create_directories():
    """Create necessary directories for the enhanced features"""
    
    directories = [
        'webui/static/uploads',
        'webui/static/js'
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✓ Created directory: {directory}")
        except Exception as e:
            print(f"✗ Failed to create directory {directory}: {e}")
            return False
    
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    
    required_packages = ['flask', 'sqlalchemy', 'PIL']
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

def main():
    print("🚀 Setting up Enhanced Notes App Features...")
    print("=" * 50)
    
    # Check dependencies
    print("\n1. Checking dependencies...")
    if not check_dependencies():
        print("\nSetup failed due to missing dependencies.")
        return
    
    # Create directories
    print("\n2. Creating directories...")
    if not create_directories():
        print("\nSetup failed during directory creation.")
        return
    
    # Run migration
    print("\n3. Running database migration...")
    if not run_migration():
        print("\nSetup failed during database migration.")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Enhanced Notes App setup completed successfully!")
    print("\nNew features added:")
    print("• Rich text editor with TinyMCE")
    print("• Advanced color palette system")
    print("• Image upload and attachment")
    print("• Auto-detection of titles and headings")
    print("• Live document schema generation")
    print("• Comprehensive settings panel")
    print("• Auto-save functionality")
    print("• Note deletion from editor")
    print("\nYou can now start the application and enjoy the enhanced features!")

if __name__ == "__main__":
    main()
