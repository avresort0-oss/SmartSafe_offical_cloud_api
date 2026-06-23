import os
import shutil
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
 
logger = logging.getLogger(__name__)

# Use a local SQLite database for this desktop application.
# The cloud sync service will handle moving data to a remote PostgreSQL DB.
from sqlalchemy.pool import QueuePool
from sqlalchemy import event

# 1. Environment-Aware Configuration
# This supports seamless migration from local development (SQLite)
# to production-grade enterprise deployments (PostgreSQL).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartsafe_local.db")

# 2. Optimized Engine Configuration
is_sqlite = DATABASE_URL.startswith("sqlite")
DB_FILE_PATH = DATABASE_URL.replace("sqlite:///", "") if is_sqlite else None

if is_sqlite:
    # Each Session gets its own pooled connection (check_same_thread=False allows
    # any thread to use a pooled connection); WAL mode below lets SQLite itself
    # serialize concurrent writers safely across those separate connections.
    # NOTE: do not use StaticPool here — forcing every Session onto one shared
    # physical connection causes concurrent commits from different threads to
    # corrupt each other's in-flight transactions (e.g. "Could not refresh
    # instance" errors from the background workers).
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=QueuePool,
    )
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
else:
    # Production PostgreSQL pooling configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_timeout=45,
        pool_recycle=1800,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


def _sqlite_column_exists(connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_sqlite_column(connection, table_name: str, column_name: str, column_ddl: str):
    if not _sqlite_column_exists(connection, table_name, column_name):
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))


def _ensure_sqlite_schema_compatibility():
    """
    Best-effort backward compatibility for existing SQLite DBs that predate
    the CRM schema. This avoids runtime failures before alembic is applied.
    """
    if not is_sqlite:
        return

    with engine.begin() as connection:
        _ensure_sqlite_column(connection, "messages", "conversation_id", "conversation_id TEXT")
        _ensure_sqlite_column(connection, "messages", "contact_id", "contact_id TEXT")
        _ensure_sqlite_column(connection, "messages", "direction", "direction TEXT DEFAULT 'OUTBOUND'")
        _ensure_sqlite_column(connection, "messages", "channel", "channel TEXT DEFAULT 'LOCAL'")
        _ensure_sqlite_column(connection, "messages", "external_message_id", "external_message_id TEXT")

        _ensure_sqlite_column(connection, "cloud_messages", "conversation_id", "conversation_id TEXT")
        _ensure_sqlite_column(connection, "cloud_messages", "contact_id", "contact_id TEXT")
        _ensure_sqlite_column(connection, "cloud_messages", "direction", "direction TEXT DEFAULT 'OUTBOUND'")
        _ensure_sqlite_column(connection, "cloud_messages", "channel", "channel TEXT DEFAULT 'LOCAL'")
        _ensure_sqlite_column(connection, "cloud_messages", "external_message_id", "external_message_id TEXT")

        connection.execute(text("UPDATE messages SET direction='OUTBOUND' WHERE direction IS NULL"))
        connection.execute(text("UPDATE messages SET channel='LOCAL' WHERE channel IS NULL"))
        connection.execute(text("UPDATE cloud_messages SET direction='OUTBOUND' WHERE direction IS NULL"))
        connection.execute(text("UPDATE cloud_messages SET channel='LOCAL' WHERE channel IS NULL"))

def backup_database():
    """Creates a safety backup of the SQLite database file."""
    if is_sqlite and DB_FILE_PATH and os.path.exists(DB_FILE_PATH):
        backup_path = f"{DB_FILE_PATH}.bak"
        try:
            # Using copy2 might fail if the file is locked by another process
            # We use a simpler copy and catch errors gracefully
            shutil.copy(DB_FILE_PATH, backup_path)
            logger.info(f"Database backup created successfully at {backup_path}")
        except Exception as e:
            logger.warning(f"Database backup skipped (likely busy): {e}")

def init_db():
    """Initializes the database, creating all tables."""
    if is_sqlite:
        backup_database()
    
    # Import all models to register them with Base.metadata
    from core.models.user import User
    from core.models.workspace import Workspace
    from core.models.message import Message
    from core.models.cloud_message import CloudMessage
    from core.models.app_setting import AppSetting
    from core.models.meta_account import MetaAccount
    from core.models.template import Template
    from core.models.integration import DesktopInstance
    from core.models.contact import Contact
    from core.models.conversation import Conversation
    from core.models.label import Label
    from core.models.contract import Contract
    from core.models.api_key import ApiKey
    from core.models.audit_log import AuditLog

    from core.models.audit_log import AuditLog

    try:
        # Increase the timeout for the duration of schema creation
        with engine.connect() as conn:
            if is_sqlite:
                conn.execute(text("PRAGMA busy_timeout = 5000"))
            Base.metadata.create_all(bind=engine)
            _ensure_sqlite_schema_compatibility()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Re-raise to be caught by the AppController's initialization thread
        raise

def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
