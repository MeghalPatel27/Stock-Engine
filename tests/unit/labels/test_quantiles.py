"""Quantile cut-size policy tests."""

from stock_engine.labels.quantiles import cut_size, top_bottom_sizes


def test_floor_ceil_nearest() -> None:
    assert cut_size(10, 0.20, "floor") == 2
    assert cut_size(10, 0.20, "ceil") == 2
    assert cut_size(11, 0.20, "floor") == 2
    assert cut_size(11, 0.20, "ceil") == 3
    assert cut_size(11, 0.20, "nearest") == 2  # 2.2 -> 2
    assert cut_size(5, 0.20, "floor") == 1


def test_shrink_when_sum_exceeds_n() -> None:
    k_top, k_bot = top_bottom_sizes(5, 0.6, 0.6, "ceil")
    assert k_top + k_bot <= 5
