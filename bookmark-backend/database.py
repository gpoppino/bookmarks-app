"""SQLAlchemy engine and session dependency."""

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL


def engine_options(database_url: str) -> dict:
    """Return engine options that are specific to the selected SQL dialect."""
    if make_url(database_url).get_backend_name() == "sqlite":
        return {"connect_args": {"check_same_thread": False}}
    return {}


SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    **engine_options(SQLALCHEMY_DATABASE_URL),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
