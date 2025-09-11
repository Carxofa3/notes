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

1. Create virtual environment: `python -m venv venv`
2. Activate virtual environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure settings
5. Initialize database: `python database/init_db.py`
6. Run application: `python main.py`

## Architecture Overview

The application follows a layered architecture:

- **Models**: Define data structure and database relationships
- **Services**: Contain business logic and data processing
- **Controllers**: Handle HTTP requests and responses
- **Utils**: Provide common functionality across the application

