"""Cost model arithmetic against NSE/statutory schedule numbers."""

from stock_engine.backtest.costs import (
    DeliveryCostModel,
    round_trip_variable_fraction,
    trade_cost_inr,
)


def test_stt_and_stamp_on_1lakh_notional() -> None:
    """
    NSE delivery example on ₹1,00,000 notional:
    STT buy 0.1% = ₹100; stamp 0.015% = ₹15 (buy only).
    """
    model = DeliveryCostModel(
        stt_rate=0.001,
        stamp_duty_rate=0.00015,
        exchange_txn_rate=0.0,
        sebi_rate=0.0,
        gst_rate=0.0,
        brokerage_rate=0.0,
        apply_dp_charges=False,
        slippage_bps=0.0,
    )
    buy = trade_cost_inr(side="buy", notional_inr=100_000.0, model=model)
    sell = trade_cost_inr(side="sell", notional_inr=100_000.0, model=model)
    assert abs(buy - 115.0) < 1e-9  # 100 STT + 15 stamp
    assert abs(sell - 100.0) < 1e-9  # 100 STT


def test_default_round_trip_near_22bps_plus_slippage() -> None:
    model = DeliveryCostModel()  # includes 5 bps slip each side
    rt = round_trip_variable_fraction(model)
    statutory = rt - 2 * (model.slippage_bps / 10_000)
    # Statutory+exchange ≈ 0.22%; +10 bps slippage ≈ 0.32%
    assert 0.0020 < statutory < 0.0025
    assert 0.0030 < rt < 0.0040


def test_dp_added_on_sell_only() -> None:
    model = DeliveryCostModel(
        stt_rate=0.0,
        stamp_duty_rate=0.0,
        exchange_txn_rate=0.0,
        sebi_rate=0.0,
        gst_rate=0.0,
        brokerage_rate=0.0,
        dp_charge_inr=15.34,
        apply_dp_charges=True,
        slippage_bps=0.0,
    )
    assert trade_cost_inr(side="buy", notional_inr=50_000.0, model=model) == 0.0
    assert abs(trade_cost_inr(side="sell", notional_inr=50_000.0, model=model) - 15.34) < 1e-9
