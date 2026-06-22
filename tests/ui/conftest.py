"""
Shared fixtures for headless ChatFrame/component smoke tests.

These run under Xvfb (no real display): `xvfb-run -a python -m pytest tests/ui/ -v`.
They exercise real CustomTkinter widget construction and the Tk event loop, so they
catch crashes and structural/state regressions. They cannot assert anything about
pixel-level appearance (color, exact layout) — that ceiling is intentional, not an
oversight; see the project plan for why.
"""
import pytest
import customtkinter as ctk

from services.message_service import MessageResponseDTO
from services.user_service import UserResponseDTO
from services.workspace_service import WorkspaceDTO

@pytest.fixture
def root():
    r = ctk.CTk()
    yield r
    try:
        r.destroy()
    except Exception:
        pass


def pump(root_widget, condition, timeout=5.0, interval_ms=20):
    """Drive a real Tk mainloop until `condition()` is true or timeout elapses.

    Must use mainloop()/quit(), not manual update() polling: tkinter only allows a
    background thread to register a new `after()` callback while the main thread is
    genuinely inside Tcl's event loop. Manual update() calls don't count as "in the
    main loop" and a worker thread's self.after(0, ...) raises
    "RuntimeError: main thread is not in main loop" if called while the test is only
    polling via update().
    """
    state = {"done": False}

    def check():
        if condition():
            state["done"] = True
            root_widget.quit()
        else:
            root_widget.after(interval_ms, check)

    check()
    timeout_id = root_widget.after(int(timeout * 1000), root_widget.quit)
    root_widget.mainloop()
    try:
        root_widget.after_cancel(timeout_id)
    except Exception:
        pass
    return state["done"] or condition()


def make_msg_dto(
    id,
    sender_id,
    content,
    sender_name="Tester",
    workspace_id="ws-1",
    conversation_id="conv-1",
    contact_id="contact-1",
    direction="OUTBOUND",
    channel="WHATSAPP",
    external_message_id=None,
    timestamp="12:00 PM",
    created_at="2026-06-21T10:00:00+00:00",
    updated_at="2026-06-21T10:00:00+00:00",
    is_synced=False,
    parent_id=None,
    attachment_path=None,
    is_starred=False,
    status="PENDING",
):
    return MessageResponseDTO(
        id=id,
        content=content,
        sender_id=sender_id,
        sender_name=sender_name,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        direction=direction,
        channel=channel,
        external_message_id=external_message_id,
        timestamp=timestamp,
        created_at=created_at,
        updated_at=updated_at,
        is_synced=is_synced,
        parent_id=parent_id,
        attachment_path=attachment_path,
        is_starred=is_starred,
        status=status,
    )


@pytest.fixture
def fake_user():
    return UserResponseDTO(id="user-1", username="tester", email="tester@example.com", is_active=True)


@pytest.fixture
def fake_workspace():
    return WorkspaceDTO(id="ws-1", name="Acme Corp", owner_id="user-1", role="OWNER")


class FakeCallbacks:
    """Stateful canned callbacks matching ChatFrame's 9 constructor callback signatures.

    `history` is returned on the first load_messages_cb call (since=None) and `[]` on
    every subsequent call (polling), unless overridden per-test via `next_poll_result`.
    """

    def __init__(self):
        self.history = [
            make_msg_dto(id="m1", sender_id="user-1", content="hi"),
            make_msg_dto(id="m2", sender_id="other-1", content="yo", sender_name="Bob"),
        ]
        self.next_poll_result = []
        self.load_calls = []
        self.sent_messages = []
        self.deleted_ids = []
        self.starred = {}
        self.detached_labels = []
        self.attached_labels = []
        self.created_contracts = []
        self._send_counter = 0

    def load_messages_cb(self, conversation_id, since):
        self.load_calls.append((conversation_id, since))
        if since is None:
            return list(self.history)
        result = self.next_poll_result
        self.next_poll_result = []
        return result

    def send_message_cb(self, conversation_id, text, user_id, reply_parent_id, route_wa, attachment, callback=None):
        self._send_counter += 1
        dto = make_msg_dto(
            id=f"sent-{self._send_counter}",
            sender_id=user_id,
            content=text,
            parent_id=reply_parent_id,
            attachment_path=attachment,
        )
        self.sent_messages.append(dto)
        if callback:
            callback(dto)
        return dto

    def delete_message_cb(self, msg_id):
        self.deleted_ids.append(msg_id)
        return True

    def toggle_star_cb(self, msg_id):
        new_state = not self.starred.get(msg_id, False)
        self.starred[msg_id] = new_state
        return new_state

    def load_quick_replies_cb(self):
        return [{"title": "Greeting", "text": "Hello there!"}]

    def load_labels_cb(self):
        return [{"id": "L1", "name": "VIP"}]

    def attach_label_cb(self, label_id, conversation_id):
        self.attached_labels.append((label_id, conversation_id))
        return True

    def detach_label_cb(self, label_id, conversation_id):
        self.detached_labels.append((label_id, conversation_id))
        return True

    def create_contract_cb(self, payload):
        self.created_contracts.append(payload)
        return True

    def as_kwargs(self):
        return dict(
            load_messages_cb=self.load_messages_cb,
            send_message_cb=self.send_message_cb,
            delete_message_cb=self.delete_message_cb,
            toggle_star_cb=self.toggle_star_cb,
            load_quick_replies_cb=self.load_quick_replies_cb,
            load_labels_cb=self.load_labels_cb,
            attach_label_cb=self.attach_label_cb,
            detach_label_cb=self.detach_label_cb,
            create_contract_cb=self.create_contract_cb,
        )


@pytest.fixture
def fake_callbacks():
    return FakeCallbacks()
