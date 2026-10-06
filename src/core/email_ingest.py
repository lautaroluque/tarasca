"""Email ingestion: fetch card-use notifications via IMAP and normalize them.

The poller (scripts/poll_email.py) runs headless in GitHub Actions and uses
this module to fetch new emails, normalize them to transaction dicts, and
track the last processed IMAP UID in the ingest_state table.
"""

import email
import imaplib
from datetime import date, datetime
from email import policy
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.core.categorization import categorize_transaction, get_default_categories
from src.core.database import get_supabase_client
from src.core.email_templates import match_email_template
from src.core.ingestion import parse_amount_argentine
from src.core.movements import classify_movement

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# Socket timeout for IMAP connect/read/write. Without this, a stalled TCP
# connection blocks forever and the job hangs until the 6-hour CI limit.
IMAP_TIMEOUT_SECONDS = 60

# Nothing before this date is ingested: card notifications older than
# August 2026 are already covered by imported statements. Sent to IMAP as
# a SINCE search criterion, which matches on INTERNALDATE.
INGEST_START_DATE = date(2026, 8, 1)

# Maps the email's "Moneda" field to our currency codes
MONEDA_TO_CURRENCY = {
    "PESOS": "ARS",
    "DÓLARES": "USD",
    "DOLARES": "USD",
}


# Cap how many messages one run will FETCH. Each FETCH is a full RFC822
# body, one round trip at a time, and the UID cursor is only stored after
# the whole batch, so an unbounded run can outlive the job and make no
# progress. Progress advances across runs: the caller stores the highest
# UID seen, so the next scheduled run resumes where this one stopped.
MAX_MESSAGES_PER_RUN = 500


# English month abbreviations: IMAP requires them regardless of locale,
# and strftime("%b") would emit the localized name on many machines.
_IMAP_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _imap_date(d: date) -> str:
    """Format a date the way IMAP wants it: 01-Aug-2026."""
    return f"{d.day:02d}-{_IMAP_MONTHS[d.month - 1]}-{d.year}"


def fetch_new_emails(
    host: str, user: str, password: str, last_uid: int = 0
) -> list[tuple[Message, int]]:
    """Fetch emails with UID > last_uid via IMAP. Returns (message, uid) pairs.

    Restricted to messages on or after INGEST_START_DATE, and fetches the
    oldest matching messages first, up to MAX_MESSAGES_PER_RUN.
    """
    mail = imaplib.IMAP4_SSL(host, timeout=IMAP_TIMEOUT_SECONDS)
    try:
        mail.login(user, password)
        mail.select("INBOX")
        # IMAP UID search: "UID <from>:*" matches all UIDs >= from.
        # IMAP joins criteria with an implicit AND, so SINCE narrows the
        # same search rather than needing a second round trip.
        _, data = mail.uid(
            "SEARCH",
            f"UID {last_uid + 1}:*",
            f"SINCE {_imap_date(INGEST_START_DATE)}",
        )
        raw_uids = data[0] if data else b""
        if isinstance(raw_uids, (bytes, bytearray)):
            uids = raw_uids.split()
        else:
            uids = []
        if len(uids) > MAX_MESSAGES_PER_RUN:
            print(
                f"Mailbox has {len(uids)} new messages; "
                f"fetching the oldest {MAX_MESSAGES_PER_RUN} this run.",
                flush=True,
            )
            uids = uids[:MAX_MESSAGES_PER_RUN]
        results: list[tuple[Message, int]] = []
        for uid in uids:
            uid_str = uid.decode() if isinstance(uid, (bytes, bytearray)) else str(uid)
            _, msg_data = mail.uid("FETCH", uid_str, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw, policy=policy.default)
            results.append((msg, int(uid)))
        return results
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def get_ingest_state(key: str) -> str | None:
    """Read a value from the ingest_state table."""
    client = get_supabase_client()
    resp = client.table("ingest_state").select("value").eq("key", key).execute()
    if resp.data and len(resp.data) > 0:
        row: Any = resp.data[0]
        return str(row.get("value"))
    return None


def set_ingest_state(key: str, value: str) -> None:
    """Write a value to the ingest_state table (upsert)."""
    client = get_supabase_client()
    client.table("ingest_state").upsert(
        {"key": key, "value": value}
    ).execute()


def get_html_body(msg: Message) -> str | None:
    """Extract the text/html part from a message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if isinstance(payload, (bytes, bytearray)):
                    return payload.decode("utf-8", errors="replace")
    elif msg.get_content_type() == "text/html":
        payload = msg.get_payload(decode=True)
        if isinstance(payload, (bytes, bytearray)):
            return payload.decode("utf-8", errors="replace")
    return None


def normalize_email(msg: Message) -> dict[str, Any] | None:
    """Convert a matched notification email into a transaction dict.

    Returns None if the email doesn't match a template or required fields
    are missing.
    """
    sender = msg.get("From", "")
    subject = msg.get("Subject", "")
    template = match_email_template(sender, subject)
    if template is None:
        return None

    html = get_html_body(msg)
    if html is None:
        return None

    fields = template.extractor(html)

    comercio = fields.get("Comercio")
    importe_str = fields.get("Importe")
    moneda = fields.get("Moneda", "")
    if not comercio or not importe_str:
        return None

    try:
        raw_amount = parse_amount_argentine(importe_str)
    except ValueError:
        return None

    currency = MONEDA_TO_CURRENCY.get(moneda.upper(), "ARS")

    # Use the Date header (more precise) converted to naive Argentina time
    date_str = msg.get("Date")
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            date = dt.astimezone(ARGENTINA_TZ).replace(tzinfo=None)
        except (ValueError, TypeError):
            date = datetime.now(ARGENTINA_TZ).replace(tzinfo=None)
    else:
        date = datetime.now(ARGENTINA_TZ).replace(tzinfo=None)

    # A COMPRA is always a gasto (money out)
    movement_type, signed_amount = classify_movement(
        "galicia_mastercard", comercio, raw_amount, hint=("gasto", "out")
    )

    categories = get_default_categories()
    category_name = categorize_transaction(comercio, categories) or "Otros"

    message_id = msg.get("Message-ID", "")

    return {
        "date": date,
        "description": comercio,
        "amount": signed_amount,
        "currency": currency,
        "movement_type": movement_type,
        "account": template.account,
        "category_name": category_name,
        "metadata": {
            "source": "email",
            "message_id": message_id,
            "tipo": fields.get("Tipo de Movimiento", ""),
            "cuotas": fields.get("Cantidad cuotas", ""),
            "estado": fields.get("Estado", ""),
            "tarjeta_ult4": fields.get("Últimos 4 dígitos de la tarjeta", ""),
            "ubicacion": fields.get("Ubicación", ""),
        },
        "source": "email",
    }


def poll_and_normalize(
    host: str, user: str, password: str
) -> tuple[list[dict[str, Any]], int]:
    """Fetch new emails and normalize them. Returns (transactions, last_uid).

    Updates the ingest_state with the highest processed UID.
    """
    last_uid_str = get_ingest_state("imap_last_uid")
    last_uid = int(last_uid_str) if last_uid_str else 0

    emails = fetch_new_emails(host, user, password, last_uid)
    transactions: list[dict[str, Any]] = []
    max_uid = last_uid

    for msg, uid in emails:
        tx = normalize_email(msg)
        if tx is not None:
            transactions.append(tx)
        if uid > max_uid:
            max_uid = uid

    if max_uid > last_uid:
        set_ingest_state("imap_last_uid", str(max_uid))

    return transactions, max_uid
