"""SQLAlchemy engine, session factory, and declarative base.

Sync engine on psycopg 3. Neon pools connections at the proxy, so pool_pre_ping
guards against the serverless endpoint dropping an idle connection.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
    # pgbouncer in transaction mode cannot keep server-side prepared statements.
    connect_args={"prepare_threshold": None} if settings.is_pooled_connection else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency. One session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
