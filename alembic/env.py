import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, ".env"))
except ImportError:
    pass

from core.database import Base
# Import all models so Base knows about them for autogenerate
from core.models.user import User
from core.models.workspace import Workspace, WorkspaceMember
from core.models.message import Message
from core.models.cloud_message import CloudMessage
from core.models.app_setting import AppSetting # noqa
from core.models.meta_account import MetaAccount
from core.models.contact import Contact
from core.models.conversation import Conversation
from core.models.label import Label, conversation_labels, contact_labels
from core.models.contract import Contract
from core.models.auto_reply_rule import AutoReplyRule
from core.models.api_key import ApiKey
from core.models.audit_log import AuditLog
from core.models.template import Template
from core.models.failed_task import FailedTask

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    url = os.getenv("DATABASE_URL")
    if not url or url == '""' or url == "''":
        return config.get_main_option("sqlalchemy.url", "sqlite:///./smartsafe_local.db")
    return url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    """
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
