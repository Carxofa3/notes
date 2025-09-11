from app import create_app
from app.utils.database import engine
from app.models import Base

app = create_app()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    Base.metadata.create_all(bind=engine)
    print('Initialized the database.')

if __name__ == '__main__':
    app.run()
