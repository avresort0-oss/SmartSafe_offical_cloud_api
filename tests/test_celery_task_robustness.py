"""Celery retry/backoff/dead-letter-queue robustness tests.

Runs real task bodies in-process via Celery's eager mode (task_always_eager),
with task_eager_propagates=False so that self.retry()'s internal recursive
apply() loop actually replays the task up to max_retries instead of raising
the first Retry straight out of .delay() -- see Task.apply()/Task.retry() in
celery/app/{task,trace}.py. Network calls (WhatsAppIntegration) are mocked;
everything else (DB writes, retry counting, the task_failure signal that
feeds workers/dlq.py) runs for real against the test SQLite database that
tests/conftest.py already provisions.
"""
import uuid

import pytest
import requests
from unittest.mock import patch

from core.database import SessionLocal
from core.models.user import User
from core.models.workspace import Workspace
from core.models.contact import Contact
from core.models.message import Message
from core.models.failed_task import FailedTask
from services.message_service import MessageService
from services.meta_cloud_service import MessageResultDTO
from workers.celery_app import app as celery_app
from workers.retry_utils import compute_backoff
import workers.message_tasks as message_tasks

OPS_BASE_URL = "http://127.0.0.1:8000/v1/ops/tasks"


@pytest.fixture(autouse=True)
def eager_celery():
    original_eager = celery_app.conf.task_always_eager
    original_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    yield
    celery_app.conf.task_always_eager = original_eager
    celery_app.conf.task_eager_propagates = original_propagates


def _unique_workspace_and_contact():
    """Creates an isolated User/Workspace/Contact trio so this module's rows
    can never collide with unique-constrained columns other test files use."""
    suffix = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        user = User(username=f"celery_test_{suffix}", email=f"celery_test_{suffix}@example.com", password_hash="x")
        db.add(user)
        db.flush()
        workspace = Workspace(name=f"Celery Test WS {suffix}", owner_id=user.id)
        db.add(workspace)
        db.flush()
        contact = Contact(workspace_id=workspace.id, phone_e164=f"+1555{suffix[:7]}", display_name="Celery Test Contact")
        db.add(contact)
        db.commit()
        return user.id, workspace.id, contact.id
    finally:
        db.close()


def _make_message(workspace_id, sender_id, contact_id=None, content="hello", status="PENDING"):
    # MessageService's lazy E2EE-key provisioning opens+commits its own
    # session; doing that *before* opening ours avoids a SQLite "database is
    # locked" conflict between the two writers.
    encrypted = MessageService()._encrypt(content)
    db = SessionLocal()
    try:
        msg = Message(
            content=encrypted,
            sender_id=sender_id,
            workspace_id=workspace_id,
            contact_id=contact_id,
            status=status,
        )
        db.add(msg)
        db.commit()
        return msg.id
    finally:
        db.close()


def _get_message(message_id):
    db = SessionLocal()
    try:
        return db.query(Message).filter_by(id=message_id).first()
    finally:
        db.close()


def _failed_task_for(task_id):
    db = SessionLocal()
    try:
        return db.query(FailedTask).filter_by(task_id=task_id).first()
    finally:
        db.close()


# --- compute_backoff ---------------------------------------------------

def test_compute_backoff_grows_exponentially_and_respects_cap():
    assert 20 <= compute_backoff(0) <= 25
    assert 40 <= compute_backoff(1) <= 45
    assert 80 <= compute_backoff(2) <= 85
    assert 160 <= compute_backoff(3) <= 165
    # base * 2**retries blows past cap=600 well before retries=10/20; every
    # value past that point should clamp to the cap (+ up to 5s jitter).
    assert 600 <= compute_backoff(10) <= 605
    assert 600 <= compute_backoff(20) <= 605


# --- dispatch_whatsapp_message ------------------------------------------

def test_dispatch_whatsapp_message_retries_then_succeeds():
    sender_id, workspace_id, contact_id = _unique_workspace_and_contact()
    message_id = _make_message(workspace_id, sender_id, contact_id)

    call_count = {"n": 0}

    def fail_twice_then_succeed(self, to_phone_number, text):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise Exception(f"transient-failure-{call_count['n']}")
        return MessageResultDTO(success=True, message_id="wamid.TEST123")

    with patch("integrations.whatsapp_integration.WhatsAppIntegration.send_message", fail_twice_then_succeed):
        result = message_tasks.dispatch_whatsapp_message.delay(message_id=message_id)

    assert result.state == "SUCCESS"
    assert call_count["n"] == 3, "should succeed on the 3rd attempt, not loop forever or stop early"

    msg = _get_message(message_id)
    assert msg.status == "SENT", "message must reach SENT once a retry succeeds"
    assert msg.external_message_id == "wamid.TEST123"
    assert _failed_task_for(result.id) is None, "a message that eventually succeeds must never be dead-lettered"


def test_dispatch_whatsapp_message_exhausts_retries_and_dead_letters():
    sender_id, workspace_id, contact_id = _unique_workspace_and_contact()
    message_id = _make_message(workspace_id, sender_id, contact_id)

    call_count = {"n": 0}

    def always_fail(self, to_phone_number, text):
        call_count["n"] += 1
        raise Exception(f"permanent-failure-{call_count['n']}")

    with patch("integrations.whatsapp_integration.WhatsAppIntegration.send_message", always_fail):
        result = message_tasks.dispatch_whatsapp_message.delay(message_id=message_id)

    assert result.state == "FAILURE"
    # max_retries=3 -> 1 initial attempt + 3 retries = 4 calls total.
    assert call_count["n"] == 4

    msg = _get_message(message_id)
    assert msg.status == "FAILED", "status must flip to FAILED once retries are exhausted"
    assert "permanent-failure-4" in msg.provider_error_code

    dead_letter = _failed_task_for(result.id)
    assert dead_letter is not None, "exhausting retries must produce exactly one DLQ row"
    assert dead_letter.task_name == "workers.message_tasks.dispatch_whatsapp_message"
    assert dead_letter.retries == 3
    assert "permanent-failure-4" in dead_letter.exception_message


def test_dispatch_whatsapp_message_never_shows_failed_mid_retry():
    """Regression guard for the status-timing bug: the message must stay in
    its pre-dispatch state (QUEUED) through every failed *attempt*, and only
    ever become FAILED once retries are actually exhausted -- never flicker
    to FAILED on attempt 1 and then silently revert."""
    sender_id, workspace_id, contact_id = _unique_workspace_and_contact()
    message_id = _make_message(workspace_id, sender_id, contact_id)

    observed_statuses = []

    def fail_and_record(self, to_phone_number, text):
        observed_statuses.append(_get_message(message_id).status)
        raise Exception("still failing")

    with patch("integrations.whatsapp_integration.WhatsAppIntegration.send_message", fail_and_record):
        message_tasks.dispatch_whatsapp_message.delay(message_id=message_id)

    # Every attempt (including retries) must see QUEUED, never FAILED.
    assert observed_statuses == ["QUEUED"] * 4


def test_dispatch_whatsapp_message_missing_phone_is_terminal_without_retry():
    sender_id, workspace_id, _ = _unique_workspace_and_contact()
    # No contact_id and no target_phone passed at call time -> resolved_phone
    # stays empty, which is a deterministic configuration error, not transient.
    message_id = _make_message(workspace_id, sender_id, contact_id=None)

    with patch("integrations.whatsapp_integration.WhatsAppIntegration.send_message") as mock_send:
        result = message_tasks.dispatch_whatsapp_message.delay(message_id=message_id)

    mock_send.assert_not_called()
    assert result.state == "SUCCESS", "the task itself completes normally -- it's the message that's FAILED, not the task"

    msg = _get_message(message_id)
    assert msg.status == "FAILED"
    assert msg.provider_error_code == "MISSING_PHONE"
    assert _failed_task_for(result.id) is None, "deterministic non-retryable failures must not be dead-lettered"


# --- download_incoming_media --------------------------------------------

def test_download_incoming_media_exhausts_retries_and_dead_letters():
    sender_id, workspace_id, contact_id = _unique_workspace_and_contact()
    message_id = _make_message(workspace_id, sender_id, contact_id)
    db = SessionLocal()
    try:
        msg = db.query(Message).filter_by(id=message_id).first()
        msg.media_id = "wamid.MEDIA123"
        db.commit()
    finally:
        db.close()

    with patch(
        "integrations.whatsapp_integration.WhatsAppIntegration._get_active_credentials",
        side_effect=Exception("media-download-boom"),
    ):
        result = message_tasks.download_incoming_media.delay(message_id=message_id)

    assert result.state == "FAILURE"
    dead_letter = _failed_task_for(result.id)
    assert dead_letter is not None
    assert dead_letter.task_name == "workers.message_tasks.download_incoming_media"
    assert dead_letter.retries == 3


# --- periodic tasks: must propagate failures instead of swallowing them ---

def test_check_sla_breaches_reraises_and_dead_letters_on_error():
    with patch("workers.message_tasks.SessionLocal") as mock_session_local:
        mock_db = mock_session_local.return_value
        mock_db.query.side_effect = RuntimeError("simulated db outage")

        result = message_tasks.check_sla_breaches.delay()

        assert mock_db.rollback.called
        assert mock_db.close.called

    assert result.state == "FAILURE"
    dead_letter = _failed_task_for(result.id)
    assert dead_letter is not None
    assert dead_letter.task_name == "workers.message_tasks.check_sla_breaches"
    assert "simulated db outage" in dead_letter.exception_message


def test_process_scheduled_campaigns_reraises_and_dead_letters_on_error():
    with patch("workers.message_tasks.SessionLocal") as mock_session_local:
        mock_db = mock_session_local.return_value
        mock_db.query.side_effect = RuntimeError("simulated campaign query failure")

        result = message_tasks.process_scheduled_campaigns.delay()

        assert mock_db.rollback.called
        assert mock_db.close.called

    assert result.state == "FAILURE"
    dead_letter = _failed_task_for(result.id)
    assert dead_letter is not None
    assert dead_letter.task_name == "workers.message_tasks.process_scheduled_campaigns"


# --- GET /v1/ops/tasks/failed --------------------------------------------

def test_failed_tasks_endpoint_fails_closed_when_key_unset(monkeypatch):
    monkeypatch.delenv("INTERNAL_OPS_KEY", raising=False)
    resp = requests.get(f"{OPS_BASE_URL}/failed", headers={"X-Internal-Key": "anything"})
    assert resp.status_code == 401


def test_failed_tasks_endpoint_rejects_missing_or_wrong_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_OPS_KEY", "test-ops-secret")

    resp = requests.get(f"{OPS_BASE_URL}/failed")
    assert resp.status_code == 401

    resp = requests.get(f"{OPS_BASE_URL}/failed", headers={"X-Internal-Key": "wrong-secret"})
    assert resp.status_code == 401


def test_failed_tasks_endpoint_lists_dead_letters_with_correct_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_OPS_KEY", "test-ops-secret")

    marker_task_name = "workers.message_tasks.check_sla_breaches"
    with patch("workers.message_tasks.SessionLocal") as mock_session_local:
        mock_db = mock_session_local.return_value
        mock_db.query.side_effect = RuntimeError("endpoint-visibility-check")
        result = message_tasks.check_sla_breaches.delay()

    resp = requests.get(
        f"{OPS_BASE_URL}/failed",
        headers={"X-Internal-Key": "test-ops-secret"},
        params={"task_name": marker_task_name, "limit": 200},
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert any(row["task_id"] == result.id for row in rows)
    assert all(row["task_name"] == marker_task_name for row in rows)
