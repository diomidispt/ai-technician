"""Database engine, session factory, and one-time schema init."""

from collections.abc import Iterator

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base, User

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Enable pgvector and create tables. Idempotent — safe to call on every start / ingest."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)


def seed_users() -> None:
    """Create a default admin + technician if there are no users yet. Idempotent."""
    from app.auth.security import hash_password  # local import avoids a circular import

    session = SessionLocal()
    try:
        if session.scalar(select(User).limit(1)) is not None:
            return
        session.add_all(
            [
                User(
                    email=settings.seed_admin_email.strip().lower(),
                    password_hash=hash_password(settings.seed_admin_password),
                    role="admin",
                ),
                User(
                    email=settings.seed_tech_email.strip().lower(),
                    password_hash=hash_password(settings.seed_tech_password),
                    role="technician",
                ),
            ]
        )
        session.commit()
        print(
            f"[seed] created users: {settings.seed_admin_email} (admin), "
            f"{settings.seed_tech_email} (technician)"
        )
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
