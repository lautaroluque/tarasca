"""Email notification templates for card-use alerts.

Mirrors the BankTemplate pattern from templates.py: each template matches
sender/subject patterns and knows how to extract fields from the HTML body.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable

from bs4 import BeautifulSoup


@dataclass
class EmailTemplate:
    """Email notification template configuration."""

    name: str
    sender_pattern: str  # regex matched against the From header
    subject_pattern: str  # regex matched against the Subject header
    account: str  # account name used in transactions (e.g. "Galicia Mastercard")
    extractor: Callable[[str], dict[str, Any]]  # HTML body → raw fields


def extract_galicia_consumo_fields(html: str) -> dict[str, Any]:
    """Extract fields from a Galicia Mastercard 'Aviso de consumo' email.

    The HTML body is a <ul> of <li>Label: <b>value</b></li> items.
    """
    soup = BeautifulSoup(html, "html.parser")
    fields: dict[str, Any] = {}
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        if ":" not in text:
            continue
        label, _, value = text.partition(":")
        label = label.strip().lstrip("\xa0").strip()
        value = value.strip()
        fields[label] = value
    return fields


TEMPLATE_GALICIA_CONSUMO = EmailTemplate(
    name="galicia_mastercard_consumo",
    sender_pattern=r"alertas@misconsultas\.com\.ar",
    subject_pattern=r"Aviso de consumo con tarjeta",
    account="Galicia Mastercard",
    extractor=extract_galicia_consumo_fields,
)

EMAIL_TEMPLATES = [TEMPLATE_GALICIA_CONSUMO]


def match_email_template(sender: str, subject: str) -> EmailTemplate | None:
    """Return the first template matching the sender and subject."""
    for template in EMAIL_TEMPLATES:
        if re.search(template.sender_pattern, sender) and re.search(
            template.subject_pattern, subject
        ):
            return template
    return None
