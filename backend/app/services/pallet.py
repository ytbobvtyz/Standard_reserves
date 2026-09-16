from decimal import ROUND_CEILING, Decimal

DEFAULT_PALLET_QTY = 1
KG_IN_TON = Decimal("1000")
QUANTITY_QUANT_PCS = Decimal("0.01")
QUANTITY_QUANT_TONS = Decimal("0.000001")


def pallet_step_pcs(pallet_qty: int | None) -> Decimal:
    if pallet_qty is None or pallet_qty < 1:
        return Decimal(DEFAULT_PALLET_QTY)
    return Decimal(pallet_qty)


def ceil_to_pallet(
    quantity: Decimal,
    pallet_qty: int | None,
    *,
    unit: str = "шт",
    weight_kg: Decimal | None = None,
) -> Decimal:
    if quantity <= 0:
        return quantity
    step_pcs = pallet_step_pcs(pallet_qty)
    qty_pcs = _to_pieces(quantity, unit, weight_kg)
    multiples = (qty_pcs / step_pcs).to_integral_value(rounding=ROUND_CEILING)
    if multiples < 1:
        multiples = Decimal(1)
    rounded_pcs = multiples * step_pcs
    return _from_pieces(rounded_pcs, unit, weight_kg)


def _to_pieces(quantity: Decimal, unit: str, weight_kg: Decimal | None) -> Decimal:
    if unit != "т":
        return quantity
    weight = Decimal(weight_kg or 0)
    if weight <= 0:
        return quantity
    return quantity * KG_IN_TON / weight


def _from_pieces(pieces: Decimal, unit: str, weight_kg: Decimal | None) -> Decimal:
    if unit != "т":
        return pieces.quantize(QUANTITY_QUANT_PCS)
    weight = Decimal(weight_kg or 0)
    if weight <= 0:
        return pieces.quantize(QUANTITY_QUANT_PCS)
    return (pieces * weight / KG_IN_TON).quantize(QUANTITY_QUANT_TONS)
