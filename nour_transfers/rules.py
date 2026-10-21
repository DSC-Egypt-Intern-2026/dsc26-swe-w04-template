"""Business rules for stock transfers between Nour branches. Pure functions."""
from typing import Literal

Priority = Literal["urgent", "high", "normal"]


def days_of_cover(stock: int, avg_daily_sales: float) -> float | None:
    """How many days the stock lasts at the current sales rate. None means 'no sales, lasts indefinitely'."""
    if stock < 0 or avg_daily_sales < 0:
        raise ValueError("stock and sales must be non-negative")
    if avg_daily_sales == 0:
        return None
    return stock / avg_daily_sales


def priority(is_chronic: bool, cover_days: float | None) -> Priority:
    if cover_days is None:
        return "normal"
    if is_chronic and cover_days < 3:
        return "urgent"
    if cover_days < 7:
        return "high"
    return "normal"


def can_transfer(from_stock: int, quantity: int, reserve: int) -> bool:
    """The sending branch must keep at least `reserve` units after the transfer."""
    return quantity >= 1 and from_stock - quantity >= reserve
