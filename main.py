from app import create_app
from app.models import Base
from app.database import db

app = create_app()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    with app.app_context():
        db.create_all()
        print('Initialized the database.')

if __name__ == '__main__':
    app.run()
