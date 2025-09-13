#!/usr/bin/env python3
"""
Unified setup script for the Notes application.
This script prepares the application for its first run by:
1. Checking for required dependencies.
2. Creating necessary directories.
3. Initializing the database with the complete, unified schema.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

DB_PATH = 'notes.db'
MIGRATION_FILE = 'database/V1_unified_migration.sql'
UPLOAD_DIR = 'webui/static/uploads'

def check_dependencies():
    """Checks if all required packages from requirements.txt are installed."""
    print("1. Checking for required dependencies...")
    try:
        with open('requirements.txt', 'r') as f:
            required = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]

        # A simple pip check to see what's installed
        installed_packages_raw = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
        installed_packages = {pkg.split('==')[0].lower() for pkg in installed_packages_raw.splitlines()}

        missing = [req for req in required if req.lower() not in installed_packages]

        if not missing:
            print("✓ All dependencies are installed.")
            return True
        else:
            print("✗ Missing dependencies found:")
            for pkg in missing:
                print(f"  - {pkg}")
            print("\nPlease install the required packages by running:")
            print(f"  {sys.executable} -m pip install -r requirements.txt")
            return False

    except FileNotFoundError:
        print("✗ requirements.txt not found. Cannot check dependencies.")
        return False
    except Exception as e:
        print(f"An error occurred while checking dependencies: {e}")
        return False

def create_directories():
    """Creates necessary directories for the application."""
    print("\n2. Creating necessary directories...")
    try:
        Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        print(f"✓ Directory '{UPLOAD_DIR}' created or already exists.")
        return True
    except Exception as e:
        print(f"✗ Failed to create directory {UPLOAD_DIR}: {e}")
        return False

def initialize_database():
    """Initializes the database using the unified migration script."""
    print("\n3. Initializing database...")

    if not os.path.exists(MIGRATION_FILE):
        print(f"✗ Migration file not found at '{MIGRATION_FILE}'.")
        return False

    try:
        # Connect to the database (this will create the file if it doesn't exist)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Read the unified migration SQL script
        with open(MIGRATION_FILE, 'r') as f:
            sql_script = f.read()

        # Execute the script
        cursor.executescript(sql_script)

        conn.commit()
        conn.close()

        print(f"✓ Database '{DB_PATH}' initialized successfully.")
        return True

    except sqlite3.Error as e:
        print(f"✗ An error occurred during database initialization: {e}")
        return False
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
        return False

def main():
    """Main function to run the setup process."""
    print("🚀 Starting setup for the Notes application...")
    print("==============================================")

    if not check_dependencies():
        print("\nSetup aborted due to missing dependencies.")
        return

    if not create_directories():
        print("\nSetup aborted due to directory creation failure.")
        return

    if not initialize_database():
        print("\nSetup aborted due to database initialization failure.")
        return

    print("\n==============================================")
    print("🎉 Application setup completed successfully!")
    print("\nYou can now run the application using: python main.py")
    print("==============================================")

if __name__ == "__main__":
    main()
