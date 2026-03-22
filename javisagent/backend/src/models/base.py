import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")
DEFAULT_SQLITE_PATH = BACKEND_ROOT / 'javisagent.db'


def _resolve_database_url(raw_url: str | None) -> str:
    if not raw_url:
        return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    # Normalize relative SQLite paths against the backend root so the app
    # always connects to the same database regardless of the launch cwd.
    if raw_url.startswith('sqlite:///') and not raw_url.startswith('sqlite:////'):
        db_path = raw_url.replace('sqlite:///', '', 1)
        if not os.path.isabs(db_path):
            resolved = (BACKEND_ROOT / db_path).resolve()
            return f"sqlite:///{resolved.as_posix()}"

    return raw_url


DATABASE_URL = _resolve_database_url(os.getenv('DATABASE_URL'))

engine = create_engine(
    DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
