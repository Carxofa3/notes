# Notes App

A web-based note-taking application for organizing lessons, units, and notes, with AI-powered features.

## Project Structure

```
notes/
├── app/                    # Main application package
│   ├── api/                # Flask-RESTX API namespaces
│   ├── models/             # SQLAlchemy database models
│   ├── services/           # Business logic layer
│   ├── static/             # Static files (CSS, JS, images)
│   └── templates/          # HTML templates
├── config/                 # Configuration files
├── migrations/             # Database migration files
├── tests/                  # Test files
├── main.py                 # Application entry point
└── requirements.txt        # Python dependencies
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
    - Edit `config/.env` to add your API keys and other settings (e.g., `OPENAI_API_KEY`).

4.  **Initialize the database:**
    This will create the database file and run all migrations.
    ```bash
    # Set the FLASK_APP environment variable
    # On Windows (cmd): set FLASK_APP=main.py
    # On Windows (PowerShell): $env:FLASK_APP = "main.py"
    # On macOS/Linux: export FLASK_APP=main.py

    flask db upgrade
    ```

5.  **Run the application:**
    ```bash
    python main.py
    ```

## Architecture Overview

The application follows a layered architecture:

- **Models**: Define data structure and database relationships using SQLAlchemy.
- **Services**: Contain business logic and data processing.
- **API**: Handles HTTP requests and responses using Flask-RESTX, with separate namespaces for each resource.
- **Frontend**: A single-page application built with vanilla JavaScript that interacts with the backend API.
