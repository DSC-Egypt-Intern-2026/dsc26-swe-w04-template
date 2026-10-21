from nour_transfers.rules import can_transfer, days_of_cover, priority


def test_reserve_is_kept_exactly():
    assert can_transfer(from_stock=40, quantity=30, reserve=10) is True


def test_no_sales_means_no_urgency():
    assert days_of_cover(stock=12, avg_daily_sales=0) is None
    assert priority(is_chronic=True, cover_days=None) == "normal"
