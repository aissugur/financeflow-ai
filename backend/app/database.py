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


def ensure_schema() -> None:
    """Tiny, idempotent migration for an MVP that uses create_all (no Alembic).

    create_all() creates missing TABLES but never adds a new COLUMN to a table
    that already exists. So when a model gains a column (e.g. chunks.embedding for
    hybrid retrieval), an older on-disk SQLite file would 'no such column' on the
    next query. This adds any such columns in place. Safe to call repeatedly and
    before the tables exist (it simply skips what isn't there yet), and never
    raises — a migration hiccup must not brick startup.
    """
    from sqlalchemy import inspect, text

    # (table, column, sqlite_type) added after the initial schema.
    additions = [("chunks", "embedding", "BLOB")]
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names())
    except Exception:
        return
    for table, column, col_type in additions:
        if table not in tables:
            continue  # fresh DB: create_all() will make it with the column
        try:
            cols = {c["name"] for c in insp.get_columns(table)}
            if column not in cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        except Exception:
            pass  # leave the DB as-is rather than crash on import


# Run on import so every entrypoint (app, eval CLIs, scripts) gets a current
# schema before its first query, including processes that never call create_all().
ensure_schema()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
