"""Reset the database: drop all tables and recreate the empty schema.

    python -m app.reset_db

Useful for a clean demo or when the local DB gets into a bad state.
"""
from .database import Base, engine
from .logging_config import setup_logging
from . import models  # noqa: F401  (ensure models are registered on Base)


def main() -> None:
    setup_logging()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset: all tables dropped and recreated (empty).")


if __name__ == "__main__":
    main()
