"""Tests for email template matching and field extraction."""

import email
from email import policy
from pathlib import Path

from src.core.email_ingest import normalize_email
from src.core.email_templates import match_email_template

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "emails"


def load_fixture(name: str) -> email.Message:
    raw = (FIXTURES_DIR / name).read_bytes()
    return email.message_from_bytes(raw, policy=policy.default)


def test_match_galicia_consumo_template():
    msg = load_fixture("consumo_1.eml")
    template = match_email_template(msg["From"], msg["Subject"])
    assert template is not None
    assert template.name == "galicia_mastercard_consumo"
    assert template.account == "Galicia Mastercard"


def test_no_match_for_other_sender():
    template = match_email_template("other@example.com", "Aviso de consumo con tarjeta")
    assert template is None


def test_normalize_consumo_pesos():
    msg = load_fixture("consumo_1.eml")
    tx = normalize_email(msg)

    assert tx is not None
    assert tx["description"] == "TEST*MERCHANT"
    assert tx["amount"] == -1234.56  # gasto = negative
    assert tx["currency"] == "ARS"
    assert tx["movement_type"] == "gasto"
    assert tx["account"] == "Galicia Mastercard"
    assert tx["source"] == "email"
    assert tx["metadata"]["message_id"] == "<test-0001@example.com>"
    assert tx["metadata"]["tipo"] == "COMPRA"
    assert tx["metadata"]["tarjeta_ult4"] == "0000"


def test_normalize_consumo_dolares():
    msg = load_fixture("consumo_dolares.eml")
    tx = normalize_email(msg)

    assert tx is not None
    assert tx["description"] == "FOREIGN*SHOP"
    assert tx["amount"] == -50.00
    assert tx["currency"] == "USD"


def test_normalize_skips_non_matching_email():
    msg = load_fixture("consumo_1.eml")
    # Tamper with the sender so it doesn't match any template
    msg.replace_header("From", "noreply@other.com")
    assert normalize_email(msg) is None


def test_normalize_skips_missing_fields():
    msg = load_fixture("consumo_1.eml")
    # Remove the HTML part so extraction finds nothing
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            part.set_content("<html><body><p>No fields here</p></body></html>")
    assert normalize_email(msg) is None
