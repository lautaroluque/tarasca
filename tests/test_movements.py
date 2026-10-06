"""Tests for movement type classification and sign normalization."""

from datetime import datetime

from src.core.ingestion import parse_spanish_date
from src.core.movements import classify_movement


def test_galicia_purchase_is_expense():
    movement_type, amount = classify_movement(
        "galicia_mastercard", "CARREFOUR ROSARIO SUR", 110794.00
    )
    assert movement_type == "gasto"
    assert amount == -110794.00


def test_galicia_refund_is_income():
    # Negative amount inside the statement detail = refund/credit
    movement_type, amount = classify_movement(
        "galicia_mastercard", "PEDIDOSYA*ROTISERIA EL", -34100.00
    )
    assert movement_type == "ingreso"
    assert amount == 34100.00


def test_galicia_card_payment_is_transfer():
    # "SU PAGO" is negative in the statement: money in (reduces the debt)
    movement_type, amount = classify_movement(
        "galicia_mastercard", "SU PAGO", -1233608.29
    )
    assert movement_type == "transferencia"
    assert amount == 1233608.29


def test_fiwind_rewards_are_income():
    for description in ("Ganancia diaria", "Rendimiento bonificado"):
        movement_type, amount = classify_movement("fiwind", description, 221.41)
        assert movement_type == "ingreso"
        assert amount == 221.41


def test_fiwind_retiro_a_person_is_expense():
    movement_type, amount = classify_movement(
        "fiwind", "Retiro a Walter Leandro Zenatti", 350000.0
    )
    assert movement_type == "gasto"
    assert amount == -350000.0


def test_fiwind_retiro_to_own_account_is_transfer():
    # Must not be read as "retiro a" (withdrawal to a person): moving money
    # between my own accounts is not spending, and the amount/sign stay put.
    movement_type, amount = classify_movement(
        "fiwind", "Retiro a una cuenta propia", -77516.50
    )
    assert movement_type == "transferencia"
    assert amount == -77516.50


def test_fiwind_deposit_to_own_account_is_transfer():
    movement_type, amount = classify_movement(
        "fiwind", "Depósito de cuenta propia", 150000.0
    )
    assert movement_type == "transferencia"
    assert amount == 150000.0


def test_own_account_rule_applies_to_default_template():
    # The rule lives in the shared (non-Galicia) branch, so any template gets it
    movement_type, amount = classify_movement(
        "otro_banco", "Retiro a una cuenta propia", -1000.0
    )
    assert movement_type == "transferencia"
    assert amount == -1000.0


def test_fiwind_conversion_is_transfer():
    movement_type, amount = classify_movement("fiwind", "Conversión", 350000.0)
    assert movement_type == "transferencia"
    assert amount == 350000.0


def test_hint_overrides_rules():
    # Opposite side of a conversion: money out
    movement_type, amount = classify_movement(
        "fiwind", "Conversión", 217.53, hint=("transferencia", "out")
    )
    assert movement_type == "transferencia"
    assert amount == -217.53


def test_unknown_movement_defaults_to_expense():
    movement_type, amount = classify_movement("fiwind", "Algo desconocido", 100.0)
    assert movement_type == "gasto"
    assert amount == -100.0


def test_parse_spanish_date():
    """Spanish month abbreviations must not depend on locale."""
    assert parse_spanish_date("19-Ago-26") == datetime(2026, 8, 19)
    assert parse_spanish_date("01-Sep-26") == datetime(2026, 9, 1)
    assert parse_spanish_date("31-Dic-25") == datetime(2025, 12, 31)
    assert parse_spanish_date("15-Ene-24") == datetime(2024, 1, 15)


def test_parse_spanish_date_invalid():
    assert parse_spanish_date("Resumen") is None
    assert parse_spanish_date("30-50000173-5") is None
    assert parse_spanish_date("01/10/2026") is None
    assert parse_spanish_date("19-XXX-26") is None
