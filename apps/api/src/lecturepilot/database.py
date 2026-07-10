from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatabaseSettings:
    url: str | None
    required: bool

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        environment = os.getenv("LECTUREPILOT_ENV", "").strip().lower()
        url = os.getenv("DATABASE_URL", "").strip() or None
        required = environment == "production"
        if required and not url:
            raise DatabaseConfigurationError("DATABASE_URL is required in production.")
        if required and url and not _is_postgresql_url(url):
            raise DatabaseConfigurationError("Production DATABASE_URL must use PostgreSQL.")
        return cls(url=_psycopg_url(url) if url else None, required=required)


class Database:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self.settings = settings or DatabaseSettings.from_env()
        self.engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        if self.settings.url:
            self.engine = create_engine(self.settings.url, pool_pre_ping=True)
            self._session_factory = sessionmaker(self.engine, expire_on_commit=False)
        if self.settings.required:
            self.verify_schema()

    @property
    def configured(self) -> bool:
        return self.engine is not None

    @contextmanager
    def session(self) -> Iterator[Session]:
        if self._session_factory is None:
            raise DatabaseConfigurationError("Database-backed operation requires DATABASE_URL.")
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def verify_schema(self) -> None:
        if self.engine is None:
            if self.settings.required:
                raise DatabaseConfigurationError("Database is not configured.")
            return
        tables = set(inspect(self.engine).get_table_names())
        required = {
            "users",
            "local_credentials",
            "sessions",
            "courses",
            "alembic_version",
        }
        missing = sorted(required - tables)
        if missing:
            raise DatabaseConfigurationError(
                f"Database migrations are required; missing tables: {', '.join(missing)}."
            )
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            current = MigrationContext.configure(connection).get_current_revision()
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        expected = ScriptDirectory.from_config(config).get_current_head()
        if current != expected:
            raise DatabaseConfigurationError(
                f"Database migration revision is stale: current={current}, expected={expected}."
            )


def _psycopg_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _is_postgresql_url(url: str) -> bool:
    return url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://"))
