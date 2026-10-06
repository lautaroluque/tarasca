"""Movement type classification: ingreso, gasto, transferencia.

Sign convention: positive = money in, negative = money out,
always relative to the account the movement belongs to.
"""

from typing import Literal

MovementType = Literal["ingreso", "gasto", "transferencia"]

MOVEMENT_TYPES: tuple[str, ...] = ("ingreso", "gasto", "transferencia")


def classify_movement(
    template_name: str,
    description: str,
    raw_amount: float,
    hint: tuple[str, str] | None = None,
) -> tuple[str, float]:
    """Classify a movement and normalize its sign.

    Args:
        template_name: Normalized template key (e.g. "galicia_mastercard").
        description: Transaction description as parsed.
        raw_amount: Amount as found in the source document.
        hint: Optional (movement_type, direction) override, used for
            derived rows such as the opposite side of a currency conversion.

    Returns:
        (movement_type, signed_amount) where positive = money in.
    """
    if hint is not None:
        movement_type, direction = hint
    else:
        movement_type, direction = _apply_rules(template_name, description, raw_amount)

    if movement_type == "gasto":
        signed = -abs(raw_amount)
    elif movement_type == "ingreso":
        signed = abs(raw_amount)
    else:  # transferencia
        signed = abs(raw_amount) if direction == "in" else -abs(raw_amount)

    return movement_type, signed


def _apply_rules(
    template_name: str, description: str, raw_amount: float
) -> tuple[str, str]:
    """Per-template keyword rules. Returns (movement_type, direction)."""
    desc = description.lower()

    if template_name == "galicia_mastercard":
        # Payment toward the card: money in (reduces what is owed)
        if "su pago" in desc:
            return "transferencia", "in"
        # Negative amount inside the detail section = refund/credit
        if raw_amount < 0:
            return "ingreso", "in"
        # Positive = purchase
        return "gasto", "out"

    # Fiwind (and default): wallet/balance account movements
    if "conversi" in desc:  # covers "conversión"/"conversion"
        return "transferencia", "in"
    if "ganancia" in desc or "rendimiento" in desc:
        return "ingreso", "in"
    # Moving money to/from another of my own accounts: not income, not an
    # expense. Checked before "retiro a", which would otherwise match
    # "Retiro a una cuenta propia" and count it as a payment.
    if "cuenta propia" in desc:
        return "transferencia", "in" if raw_amount >= 0 else "out"
    if "retiro a" in desc:  # withdrawal to a person = payment
        return "gasto", "out"
    if "retiro" in desc:
        return "transferencia", "out"
    if "depósito" in desc or "deposito" in desc:
        return "transferencia", "in"
    return "gasto", "out"
