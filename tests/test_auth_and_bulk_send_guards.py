import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bcrypt


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.meta_account_service import MetaAccountService, MessageResultDTO
from services.user_service import UserService


class _ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self._target = target

    def start(self):
        if self._target:
            self._target()


class _DummySessionCtx:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeMetaAccountRepository:
    def __init__(self, session):
        self._account = SimpleNamespace(
            id="acc-1",
            phone_number_id="phone-id-1",
            access_token="token-1",
            is_active=True,
        )

    def get_by_id(self, account_id: str):
        if account_id == "acc-1":
            return self._account
        return None


class _CloudStub:
    def __init__(self):
        self.sent_to = []

    def send_text_message(self, phone_number_id, access_token, to_phone, body):
        self.sent_to.append(to_phone)
        return MessageResultDTO(success=True, message_id=f"wamid-{to_phone}")


class AuthAndBulkSendGuardTests(unittest.TestCase):
    def test_invalid_password_hash_does_not_crash_auth(self):
        service = UserService(Mock())

        self.assertFalse(service._check_password("secret", "external_wa"))

    def test_bulk_send_accepts_numbers_with_or_without_plus_prefix(self):
        cloud = _CloudStub()
        service = MetaAccountService(session=Mock(), cloud_service=cloud)

        progress_events = []
        completion_events = []

        with patch("services.meta_account_service.SessionLocal", lambda: _DummySessionCtx()):
            with patch("services.meta_account_service.MetaAccountRepository", _FakeMetaAccountRepository):
                with patch("services.meta_account_service.threading.Thread", _ImmediateThread):
                    with patch("services.meta_account_service.time.sleep", lambda *_: None):
                        with patch("services.meta_account_service.random.uniform", lambda _a, _b: 0):
                            service.bulk_send(
                                account_id="acc-1",
                                to_phones=[
                                    "15550001234",
                                    "+15550001234",
                                    "(44)-7700-900123",
                                    "bad-input",
                                ],
                                message_type="text",
                                text_body="hello",
                                progress_callback=lambda current, total, phone: progress_events.append((current, total, phone)),
                                completion_callback=lambda ok, fail: completion_events.append((ok, fail)),
                            )

        self.assertEqual(cloud.sent_to, ["+15550001234", "+447700900123"])
        self.assertEqual(progress_events, [(1, 2, "+15550001234"), (2, 2, "+447700900123")])
        self.assertEqual(completion_events, [(2, 0)])

    def test_valid_bcrypt_hash_still_authenticates(self):
        service = UserService(Mock())
        hashed = bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode("utf-8")

        self.assertTrue(service._check_password("secret", hashed))


if __name__ == "__main__":
    unittest.main()
