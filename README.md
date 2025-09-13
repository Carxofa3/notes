# Notes App

A web-based note-taking application for organizing lessons, units, and notes.

## Project Structure

```
notes/
├── app/                    # Main application package
│   ├── controllers/        # Route handlers and API endpoints
│   ├── models/            # Database models and schemas
│   ├── services/          # Business logic layer
│   └── utils/             # Utility functions and helpers
├── config/                # Configuration files
├── database/              # Database initialization and schema
├── migrations/            # Database migration files
├── tests/                 # Test files
├── webui/                # Frontend templates and static files
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JavaScript, images
├── logs/                 # Application log files
├── main.py               # Application entry point
└── requirements.txt      # Python dependencies
```

## Setup Instructions

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\\Scripts\\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure your environment:**
    - Copy `config/.env.example` to `config/.env`.
    - Edit `config/.env` to add your API keys and other settings.

4.  **Run the setup script:**
    This will initialize the database with the complete schema and create necessary directories.
    ```bash
    python setup.py
    ```

5.  **Run the application:**
    ```bash
    python main.py
    ```

## Architecture Overview

The application follows a layered architecture:

- **Models**: Define data structure and database relationships
- **Services**: Contain business logic and data processing
- **Controllers**: Handle HTTP requests and responses
- **Utils**: Provide common functionality across the application

