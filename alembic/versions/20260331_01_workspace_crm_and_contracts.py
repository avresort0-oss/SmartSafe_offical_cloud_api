"""workspace crm and contracts foundation

Revision ID: 20260331_01
Revises:
Create Date: 2026-03-31
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260331_01"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def _normalize_phone(raw: str) -> str:
    if not raw:
        return ""
    value = raw.strip()
    prefix = "+" if value.startswith("+") else ""
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""
    return f"{prefix}{digits}" if prefix else f"+{digits}"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "contacts"):
        op.create_table(
            "contacts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("phone_e164", sa.String(length=32), nullable=False),
            sa.Column("display_name", sa.String(length=120), nullable=False, server_default="Unknown"),
            sa.Column("email", sa.String(length=120), nullable=True),
            sa.Column("lifecycle_stage", sa.String(length=32), nullable=False, server_default="LEAD"),
            sa.Column("owner_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True, server_default=""),
            sa.Column("is_whatsapp_customer", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("workspace_id", "phone_e164", name="uq_contacts_workspace_phone"),
        )
        op.create_index("ix_contacts_workspace_id", "contacts", ["workspace_id"])
        op.create_index("ix_contacts_phone_e164", "contacts", ["phone_e164"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=False),
            sa.Column("meta_account_id", sa.String(length=36), sa.ForeignKey("meta_accounts.id"), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
            sa.Column("priority", sa.String(length=32), nullable=False, server_default="NORMAL"),
            sa.Column("assigned_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("last_message_at", sa.DateTime(), nullable=True),
            sa.Column("last_message_preview", sa.String(length=255), nullable=True, server_default=""),
            sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("workspace_id", "contact_id", "meta_account_id", name="uq_conversation_workspace_contact_meta"),
        )
        op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
        op.create_index("ix_conversations_status", "conversations", ["status"])
        op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
        op.create_index("ix_conversations_assigned_user_id", "conversations", ["assigned_user_id"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "labels"):
        op.create_table(
            "labels",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("color_hex", sa.String(length=16), nullable=False, server_default="#00a884"),
            sa.Column("applies_to", sa.String(length=32), nullable=False, server_default="BOTH"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("workspace_id", "name", name="uq_labels_workspace_name"),
        )
        op.create_index("ix_labels_workspace_id", "labels", ["workspace_id"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "conversation_labels"):
        op.create_table(
            "conversation_labels",
            sa.Column("conversation_id", sa.String(length=36), sa.ForeignKey("conversations.id"), primary_key=True),
            sa.Column("label_id", sa.String(length=36), sa.ForeignKey("labels.id"), primary_key=True),
        )

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "contact_labels"):
        op.create_table(
            "contact_labels",
            sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), primary_key=True),
            sa.Column("label_id", sa.String(length=36), sa.ForeignKey("labels.id"), primary_key=True),
        )

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "contracts"):
        op.create_table(
            "contracts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("contract_number", sa.String(length=80), nullable=True),
            sa.Column("contract_type", sa.String(length=80), nullable=True, server_default="SERVICE"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
            sa.Column("value_amount", sa.Float(), nullable=True),
            sa.Column("currency", sa.String(length=12), nullable=False, server_default="USD"),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("renewal_date", sa.Date(), nullable=True),
            sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("document_path", sa.String(length=512), nullable=True),
            sa.Column("owner_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_contracts_workspace_id", "contracts", ["workspace_id"])
        op.create_index("ix_contracts_contact_id", "contracts", ["contact_id"])
        op.create_index("ix_contracts_status", "contracts", ["status"])

    inspector = sa.inspect(bind)
    with op.batch_alter_table("messages") as batch_op:
        if not _column_exists(inspector, "messages", "conversation_id"):
            batch_op.add_column(sa.Column("conversation_id", sa.String(length=36), nullable=True))
        if not _column_exists(inspector, "messages", "contact_id"):
            batch_op.add_column(sa.Column("contact_id", sa.String(length=36), nullable=True))
        if not _column_exists(inspector, "messages", "direction"):
            batch_op.add_column(sa.Column("direction", sa.String(length=32), nullable=False, server_default="OUTBOUND"))
        if not _column_exists(inspector, "messages", "channel"):
            batch_op.add_column(sa.Column("channel", sa.String(length=32), nullable=False, server_default="LOCAL"))
        if not _column_exists(inspector, "messages", "external_message_id"):
            batch_op.add_column(sa.Column("external_message_id", sa.String(length=128), nullable=True))

    inspector = sa.inspect(bind)
    with op.batch_alter_table("cloud_messages") as batch_op:
        if not _column_exists(inspector, "cloud_messages", "conversation_id"):
            batch_op.add_column(sa.Column("conversation_id", sa.String(length=36), nullable=True))
        if not _column_exists(inspector, "cloud_messages", "contact_id"):
            batch_op.add_column(sa.Column("contact_id", sa.String(length=36), nullable=True))
        if not _column_exists(inspector, "cloud_messages", "direction"):
            batch_op.add_column(sa.Column("direction", sa.String(length=32), nullable=False, server_default="OUTBOUND"))
        if not _column_exists(inspector, "cloud_messages", "channel"):
            batch_op.add_column(sa.Column("channel", sa.String(length=32), nullable=False, server_default="LOCAL"))
        if not _column_exists(inspector, "cloud_messages", "external_message_id"):
            batch_op.add_column(sa.Column("external_message_id", sa.String(length=128), nullable=True))

    run_backfill(bind)


def run_backfill(bind) -> None:
    now = datetime.now(timezone.utc)
    bind.execute(
        sa.text(
            """
            UPDATE messages
            SET direction = COALESCE(direction, 'OUTBOUND'),
                channel = COALESCE(channel, 'LOCAL')
            """
        )
    )

    external_users = bind.execute(
        sa.text(
            """
            SELECT id, username, email
            FROM users
            WHERE username LIKE '+%'
               OR username GLOB '[0-9]*'
               OR email LIKE '%@wa.external'
            """
        )
    ).mappings().all()

    for user in external_users:
        phone = _normalize_phone(user["username"] or "")
        if not phone:
            continue
        display_name = (user["username"] or phone)[:120]

        workspace_rows = bind.execute(
            sa.text("SELECT DISTINCT workspace_id FROM messages WHERE sender_id = :sender_id"),
            {"sender_id": user["id"]},
        ).mappings().all()

        for ws in workspace_rows:
            workspace_id = ws["workspace_id"]
            existing_contact = bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM contacts
                    WHERE workspace_id = :workspace_id AND phone_e164 = :phone_e164
                    """
                ),
                {"workspace_id": workspace_id, "phone_e164": phone},
            ).mappings().first()
            if existing_contact:
                contact_id = existing_contact["id"]
            else:
                contact_id = str(uuid.uuid4())
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO contacts (
                            id, workspace_id, phone_e164, display_name, email, lifecycle_stage, owner_user_id,
                            notes, is_whatsapp_customer, is_active, created_at, updated_at
                        ) VALUES (
                            :id, :workspace_id, :phone_e164, :display_name, :email, 'LEAD', NULL,
                            '', 1, 1, :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "id": contact_id,
                        "workspace_id": workspace_id,
                        "phone_e164": phone,
                        "display_name": display_name,
                        "email": user["email"],
                        "created_at": now,
                        "updated_at": now,
                    },
                )

            existing_conv = bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM conversations
                    WHERE workspace_id = :workspace_id
                      AND contact_id = :contact_id
                      AND meta_account_id IS NULL
                    """
                ),
                {"workspace_id": workspace_id, "contact_id": contact_id},
            ).mappings().first()
            if existing_conv:
                conversation_id = existing_conv["id"]
            else:
                conversation_id = str(uuid.uuid4())
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO conversations (
                            id, workspace_id, contact_id, meta_account_id, status, priority, assigned_user_id,
                            last_message_at, last_message_preview, unread_count, created_at, updated_at
                        ) VALUES (
                            :id, :workspace_id, :contact_id, NULL, 'OPEN', 'NORMAL', NULL,
                            NULL, '', 0, :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "id": conversation_id,
                        "workspace_id": workspace_id,
                        "contact_id": contact_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                )

            bind.execute(
                sa.text(
                    """
                    UPDATE messages
                    SET contact_id = :contact_id,
                        conversation_id = :conversation_id,
                        direction = 'INBOUND',
                        channel = 'WHATSAPP'
                    WHERE sender_id = :sender_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {
                    "contact_id": contact_id,
                    "conversation_id": conversation_id,
                    "sender_id": user["id"],
                    "workspace_id": workspace_id,
                },
            )

            bind.execute(
                sa.text(
                    """
                    UPDATE conversations
                    SET last_message_at = (
                        SELECT MAX(created_at)
                        FROM messages
                        WHERE conversation_id = :conversation_id
                    ),
                        last_message_preview = COALESCE((
                            SELECT substr(content, 1, 255)
                            FROM messages
                            WHERE conversation_id = :conversation_id
                            ORDER BY created_at DESC
                            LIMIT 1
                        ), ''),
                        unread_count = (
                            SELECT COUNT(1)
                            FROM messages
                            WHERE conversation_id = :conversation_id
                              AND direction = 'INBOUND'
                              AND is_deleted = 0
                        ),
                        updated_at = :updated_at
                    WHERE id = :conversation_id
                    """
                ),
                {"conversation_id": conversation_id, "updated_at": now},
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "contact_labels"):
        op.drop_table("contact_labels")
    if _table_exists(inspector, "conversation_labels"):
        op.drop_table("conversation_labels")
    if _table_exists(inspector, "contracts"):
        op.drop_table("contracts")
    if _table_exists(inspector, "labels"):
        op.drop_table("labels")
    if _table_exists(inspector, "conversations"):
        op.drop_table("conversations")
    if _table_exists(inspector, "contacts"):
        op.drop_table("contacts")

