from typing import Literal


PriceAlertType = Literal["price_drop", "back_in_stock", "target_price"]


def build_price_alerts(
    *,
    label: str,
    url: str,
    previous_price: float | None,
    new_price: float | None,
    previous_stock: bool | None,
    new_stock: bool | None,
    min_price: float | None,
    alert_threshold: float | None,
) -> set[PriceAlertType]:
    alerts: set[PriceAlertType] = set()

    if previous_price is not None and new_price is not None and new_price < previous_price:
        alerts.add("price_drop")

    if previous_stock is False and new_stock is True:
        alerts.add("back_in_stock")

    crossed_target = (
        alert_threshold is not None
        and new_price is not None
        and new_price <= alert_threshold
        and (previous_price is None or previous_price > alert_threshold)
    )
    if crossed_target:
        alerts.add("target_price")

    return alerts
