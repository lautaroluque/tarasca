"""Tests for categorization module."""

from src.core.categorization import (
    add_custom_keyword,
    categorize_transaction,
    get_default_categories,
    remove_custom_keyword,
)


def test_get_default_categories():
    """Test that default categories are returned."""
    categories = get_default_categories()
    assert len(categories) == 10
    category_names = [c["name"] for c in categories]
    assert "Vivienda" in category_names
    assert "Alimentación" in category_names
    assert "Transporte" in category_names
    assert "Otros" in category_names


def test_categorize_transaction_food():
    """Test categorization of food transactions."""
    categories = get_default_categories()

    assert categorize_transaction("PEDIDOSYA*ROTISERIA EL", categories) == "Alimentación"
    assert categorize_transaction("MC DONALDS P SIGLO", categories) == "Alimentación"
    assert categorize_transaction("SUPERM COTO MC 165", categories) == "Alimentación"


def test_categorize_transaction_transport():
    """Test categorization of transport transactions."""
    categories = get_default_categories()

    assert categorize_transaction("UBER*TRIP", categories) == "Transporte"
    assert categorize_transaction("CABIFYAR", categories) == "Transporte"
    assert categorize_transaction("COMBUSTIBLE", categories) == "Transporte"


def test_categorize_transaction_entertainment():
    """Test categorization of entertainment transactions."""
    categories = get_default_categories()

    assert categorize_transaction("NETFLIX.COM", categories) == "Entretenimiento"
    assert categorize_transaction("SPOTIFY", categories) == "Entretenimiento"
    assert categorize_transaction("SHOWCASE CINEMAS ROSAR", categories) == "Entretenimiento"


def test_categorize_transaction_no_match():
    """Test that unmatched transactions return None."""
    categories = get_default_categories()

    assert categorize_transaction("UNKNOWN MERCHANT XYZ", categories) is None


def test_add_custom_keyword():
    """Test adding a custom keyword."""
    categories = get_default_categories()

    # Add a new keyword
    add_custom_keyword("Otros", "custom_keyword_test")

    # Verify it works
    assert categorize_transaction("custom_keyword_test", categories) == "Otros"

    # Clean up
    remove_custom_keyword("Otros", "custom_keyword_test")


def test_remove_custom_keyword():
    """Test removing a custom keyword."""
    categories = get_default_categories()

    # Add and then remove
    add_custom_keyword("Otros", "temp_keyword")
    remove_custom_keyword("Otros", "temp_keyword")

    # Verify it no longer works
    assert categorize_transaction("temp_keyword", categories) is None
