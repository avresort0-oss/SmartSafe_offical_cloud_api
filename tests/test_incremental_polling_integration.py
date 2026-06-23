import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure model metadata is registered before create_all.
from core.database import Base
from core.models.app_setting import AppSetting
from core.models.contact import Contact
from core.models.conversation import Conversation
from core.models.message import Message
from core.models.user import User
from core.models.workspace import Workspace
import services.message_service as message_service_module
from services.message_service import MessageService


class IncrementalPollingIntegrationTests(unittest.TestCase):
    """
    Integration-test scaffold for incremental chat polling.

    Covers end-to-end behavior from MessageService -> MessageRepository -> SQLite
    using a dedicated in-memory database and patched SessionLocal.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)
        cls.sessionlocal_patcher = patch.object(message_service_module, "SessionLocal", cls.TestSessionLocal)
        cls.sessionlocal_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.sessionlocal_patcher.stop()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self._truncate_tables()
        self.user_id, self.workspace_id = self._seed_user_workspace()
        self.service = MessageService(whatsapp_integration=None)

    def _truncate_tables(self):
        with self.TestSessionLocal() as session:
            session.query(Message).delete()
            session.query(Conversation).delete()
            session.query(Contact).delete()
            session.query(Workspace).delete()
            session.query(User).delete()
            session.query(AppSetting).delete()
            session.commit()

    def _seed_user_workspace(self):
        with self.TestSessionLocal() as session:
            user = User(
                id="u-test-1",
                username="itest-user",
                email="itest-user@example.com",
                password_hash="not-used",
            )
            workspace = Workspace(
                id="w-test-1",
                name="Integration Workspace",
                owner_id=user.id,
            )
            session.add(user)
            session.add(workspace)
            session.commit()
            return user.id, workspace.id

    def _insert_message(
        self,
        message_id: str,
        content: str,
        created_at: datetime,
        updated_at: datetime,
        conversation_id: str = None,
        contact_id: str = None,
        *,
        is_synced: bool = False,
        is_starred: bool = False,
    ):
        with self.TestSessionLocal() as session:
            msg = Message(
                id=message_id,
                content=content,
                sender_id=self.user_id,
                workspace_id=self.workspace_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                is_synced=is_synced,
                is_starred=is_starred,
            )
            msg.created_at = created_at
            msg.updated_at = updated_at
            session.add(msg)
            session.commit()

    def _seed_contact_conversation(self, contact_id: str, conversation_id: str, phone: str):
        with self.TestSessionLocal() as session:
            contact = Contact(
                id=contact_id,
                workspace_id=self.workspace_id,
                phone_e164=phone,
                display_name=f"Contact-{contact_id}",
            )
            conversation = Conversation(
                id=conversation_id,
                workspace_id=self.workspace_id,
                contact_id=contact_id,
                status="OPEN",
                priority="NORMAL",
                unread_count=0,
            )
            session.add(contact)
            session.add(conversation)
            session.commit()

    def test_incremental_poll_returns_only_new_messages_after_cursor(self):
        t0 = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
        self._insert_message("m-1", "first", t0, t0)
        self._insert_message("m-2", "second", t0 + timedelta(minutes=1), t0 + timedelta(minutes=1))

        initial = self.service.get_recent_messages(self.workspace_id)
        self.assertEqual([m.id for m in initial], ["m-1", "m-2"])
        cursor = initial[-1].updated_at

        self._insert_message("m-3", "third", t0 + timedelta(minutes=2), t0 + timedelta(minutes=2))
        delta = self.service.get_recent_messages(self.workspace_id, since_timestamp=cursor)

        self.assertEqual([m.id for m in delta], ["m-3"])

    def test_incremental_poll_includes_existing_message_when_updated(self):
        t0 = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
        self._insert_message("m-10", "status-target", t0, t0, is_starred=False)

        initial = self.service.get_recent_messages(self.workspace_id)
        self.assertEqual(len(initial), 1)
        cursor = initial[-1].updated_at

        with self.TestSessionLocal() as session:
            msg = session.query(Message).filter(Message.id == "m-10").one()
            msg.is_starred = True
            msg.updated_at = t0 + timedelta(minutes=5)
            session.commit()

        delta = self.service.get_recent_messages(self.workspace_id, since_timestamp=cursor)

        self.assertEqual(len(delta), 1)
        self.assertEqual(delta[0].id, "m-10")
        self.assertTrue(delta[0].is_starred)

    def test_invalid_cursor_falls_back_to_full_recent_load(self):
        t0 = datetime(2026, 3, 1, 7, 0, tzinfo=timezone.utc)
        self._insert_message("m-20", "a", t0, t0)
        self._insert_message("m-21", "b", t0 + timedelta(minutes=1), t0 + timedelta(minutes=1))

        rows = self.service.get_recent_messages(self.workspace_id, since_timestamp="not-a-valid-iso")

        self.assertEqual([m.id for m in rows], ["m-20", "m-21"])

    def test_incremental_poll_scaffold_filters_by_selected_conversation(self):
        self._seed_contact_conversation("c-1", "conv-1", "+15550001111")
        self._seed_contact_conversation("c-2", "conv-2", "+15550002222")
        t0 = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
        self._insert_message("m-c1-a", "c1-first", t0, t0, conversation_id="conv-1", contact_id="c-1")
        self._insert_message(
            "m-c2-a",
            "c2-first",
            t0 + timedelta(minutes=1),
            t0 + timedelta(minutes=1),
            conversation_id="conv-2",
            contact_id="c-2",
        )

        rows = self.service.get_recent_messages(self.workspace_id, conversation_id="conv-1")
        self.assertEqual([m.id for m in rows], ["m-c1-a"])

        cursor = rows[-1].updated_at
        self._insert_message(
            "m-c1-b",
            "c1-second",
            t0 + timedelta(minutes=2),
            t0 + timedelta(minutes=2),
            conversation_id="conv-1",
            contact_id="c-1",
        )
        self._insert_message(
            "m-c2-b",
            "c2-second",
            t0 + timedelta(minutes=3),
            t0 + timedelta(minutes=3),
            conversation_id="conv-2",
            contact_id="c-2",
        )

        delta = self.service.get_recent_messages(
            self.workspace_id,
            since_timestamp=cursor,
            conversation_id="conv-1",
        )
        self.assertEqual([m.id for m in delta], ["m-c1-b"])


if __name__ == "__main__":
    unittest.main()
