from decimal import Decimal

from app.services.pallet import ceil_to_pallet


def test_ceil_to_pallet_rounds_up() -> None:
    assert ceil_to_pallet(Decimal("10"), 48) == Decimal("48.00")
    assert ceil_to_pallet(Decimal("48"), 48) == Decimal("48.00")
    assert ceil_to_pallet(Decimal("49"), 48) == Decimal("96.00")


def test_ceil_to_pallet_defaults_missing_norm_to_one() -> None:
    assert ceil_to_pallet(Decimal("10"), None) == Decimal("10.00")
    assert ceil_to_pallet(Decimal("10.1"), None) == Decimal("11.00")


def test_ceil_to_pallet_converts_tons_via_weight() -> None:
    rounded = ceil_to_pallet(
        Decimal("1"),
        756,
        unit="т",
        weight_kg=Decimal("0.82"),
    )
    assert rounded == Decimal("1.23984")


def test_ceil_to_pallet_keeps_exact_ton_multiple() -> None:
    rounded = ceil_to_pallet(
        Decimal("1.23984"),
        756,
        unit="т",
        weight_kg=Decimal("0.82"),
    )
    assert rounded == Decimal("1.23984")


def test_ceil_to_pallet_keeps_six_ton_decimals() -> None:
    rounded = ceil_to_pallet(
        Decimal("0.0001"),
        1,
        unit="т",
        weight_kg=Decimal("0.82"),
    )
    assert rounded == Decimal("0.000820")
