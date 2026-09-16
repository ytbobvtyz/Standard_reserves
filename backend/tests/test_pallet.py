from decimal import Decimal

from app.services.pallet import ceil_to_pallet


def test_ceil_to_pallet_rounds_up() -> None:
    assert ceil_to_pallet(Decimal("10"), 48) == Decimal("48.00")
    assert ceil_to_pallet(Decimal("48"), 48) == Decimal("48.00")
    assert ceil_to_pallet(Decimal("49"), 48) == Decimal("96.00")


def test_ceil_to_pallet_defaults_missing_norm_to_one() -> None:
    assert ceil_to_pallet(Decimal("10"), None) == Decimal("10.00")
    assert ceil_to_pallet(Decimal("10.1"), None) == Decimal("11.00")
