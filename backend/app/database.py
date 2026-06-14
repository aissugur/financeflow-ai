"""SQLAlchemy engine, session, and Base used across the app."""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

# check_same_thread=False is required for SQLite used by FastAPI's thread pool.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores ON DELETE CASCADE unless foreign keys are enabled per
    connection. Without this, the FK constraints on chunks/qa_history would be
    dead weight and rely solely on ORM-level cascades."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
