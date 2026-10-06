"""Tests for the email poller with a mocked IMAP mailbox."""

import email
from datetime import date
from email import policy
from pathlib import Path
from unittest import mock

from src.core import email_ingest
from src.core.email_ingest import poll_and_normalize

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "emails"


def load_fixture(name: str) -> email.Message:
    raw = (FIXTURES_DIR / name).read_bytes()
    return email.message_from_bytes(raw, policy=policy.default)


def test_poll_and_normalize_returns_transactions():
    msg1 = load_fixture("consumo_1.eml")
    msg2 = load_fixture("consumo_2.eml")

    with (
        mock.patch.object(email_ingest, "get_ingest_state", return_value=None),
        mock.patch.object(email_ingest, "set_ingest_state") as mock_set_state,
        mock.patch.object(
            email_ingest, "fetch_new_emails", return_value=[(msg1, 101), (msg2, 102)]
        ),
    ):
        transactions, last_uid = poll_and_normalize("host", "user", "pass")

    assert last_uid == 102
    assert len(transactions) == 2
    assert transactions[0]["description"] == "TEST*MERCHANT"
    assert transactions[1]["description"] == "OTHER*STORE"
    mock_set_state.assert_called_once_with("imap_last_uid", "102")


def test_poll_and_normalize_respects_last_uid():
    msg1 = load_fixture("consumo_1.eml")

    with (
        mock.patch.object(email_ingest, "get_ingest_state", return_value="100"),
        mock.patch.object(email_ingest, "set_ingest_state"),
        mock.patch.object(
            email_ingest, "fetch_new_emails", return_value=[(msg1, 101)]
        ) as mock_fetch,
    ):
        poll_and_normalize("host", "user", "pass")

    # fetch_new_emails should be called with last_uid=100
    mock_fetch.assert_called_once_with("host", "user", "pass", 100)


def test_poll_and_normalize_skips_non_matching():
    msg = load_fixture("consumo_1.eml")
    msg.replace_header("From", "noreply@other.com")

    with (
        mock.patch.object(email_ingest, "get_ingest_state", return_value=None),
        mock.patch.object(email_ingest, "set_ingest_state"),
        mock.patch.object(email_ingest, "fetch_new_emails", return_value=[(msg, 101)]),
    ):
        transactions, last_uid = poll_and_normalize("host", "user", "pass")

    assert transactions == []
    assert last_uid == 101  # UID still advances


def test_fetch_new_emails_caps_batch(monkeypatch):
    """A first run must not FETCH the entire mailbox in one go."""

    class FakeMail:
        def __init__(self):
            self.fetched = []

        def login(self, user, password):
            pass

        def select(self, mailbox):
            return ("OK", [b""])

        def uid(self, command, *args):
            if command == "SEARCH":
                big = b" ".join(str(u).encode() for u in range(1, 1001))
                return ("OK", [big])
            self.fetched.append(args[0])
            return ("OK", [(None, b"raw")])

        def logout(self):
            pass

    fake = FakeMail()
    monkeypatch.setattr(email_ingest.imaplib, "IMAP4_SSL", lambda *a, **k: fake)

    results = email_ingest.fetch_new_emails("host", "user", "pass", last_uid=0)

    assert len(results) == email_ingest.MAX_MESSAGES_PER_RUN
    assert len(fake.fetched) == email_ingest.MAX_MESSAGES_PER_RUN
    # Oldest first, so the stored UID cursor advances monotonically
    assert fake.fetched[0] == "1"
    assert results[0][1] == 1


def test_fetch_new_emails_limits_to_ingest_start(monkeypatch):
    """Messages older than INGEST_START_DATE must never be fetched."""

    class FakeMail:
        def __init__(self):
            self.search_args = None

        def login(self, user, password):
            pass

        def select(self, mailbox):
            return ("OK", [b""])

        def uid(self, command, *args):
            if command == "SEARCH":
                self.search_args = args
                return ("OK", [b"101"])
            return ("OK", [(None, b"raw")])

        def logout(self):
            pass

    fake = FakeMail()
    monkeypatch.setattr(email_ingest.imaplib, "IMAP4_SSL", lambda *a, **k: fake)

    email_ingest.fetch_new_emails("host", "user", "pass", last_uid=0)

    assert fake.search_args == (
        "UID 1:*",
        "SINCE 01-Aug-2026",
    )


def test_imap_date_format():
    """IMAP requires DD-Mon-YYYY with an English month name."""
    assert email_ingest._imap_date(date(2026, 8, 1)) == "01-Aug-2026"
    assert email_ingest._imap_date(date(2026, 12, 31)) == "31-Dec-2026"
