from decimal import ROUND_CEILING, Decimal

DEFAULT_PALLET_QTY = 1
QUANTITY_QUANT = Decimal("0.01")


def pallet_step(pallet_qty: int | None) -> Decimal:
    if pallet_qty is None or pallet_qty < 1:
        return Decimal(DEFAULT_PALLET_QTY)
    return Decimal(pallet_qty)


def ceil_to_pallet(quantity: Decimal, pallet_qty: int | None) -> Decimal:
    step = pallet_step(pallet_qty)
    if quantity <= 0:
        return quantity
    multiples = (quantity / step).to_integral_value(rounding=ROUND_CEILING)
    if multiples < 1:
        multiples = Decimal(1)
    return (multiples * step).quantize(QUANTITY_QUANT)
