import sqlite3
import os

# Get the absolute path to the database file
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'notes.db'))

def create_database():
    """Creates the database if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    conn.close()

def initialize_schema():
    """Initializes the database schema by executing the schema.sql file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()

def create_sample_data():
    """Populates the database with sample data from sample_data.sql."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sample_data_path = os.path.join(os.path.dirname(__file__), 'sample_data.sql')
    if os.path.exists(sample_data_path):
        with open(sample_data_path, 'r') as f:
            cursor.executescript(f.read())

    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Initializing database...")
    create_database()
    initialize_schema()
    # create_sample_data() # Uncomment to load sample data
    print("Database initialized successfully.")