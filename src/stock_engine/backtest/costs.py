"""India equity delivery cost model (statutory + exchange schedules)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeliveryCostModel:
    """
    Per-side / round-trip costs for NSE equity delivery.

    Rates are fractions of notional unless noted (dp_charge_inr is INR flat).
    See docs/backtest/COST_SOURCES.md.
    """

    stt_rate: float = 0.001  # 0.10% each side
    stamp_duty_rate: float = 0.00015  # 0.015% buy only
    exchange_txn_rate: float = 0.0000297  # 0.00297% each side
    sebi_rate: float = 0.000001  # ₹10/crore each side
    gst_rate: float = 0.18
    brokerage_rate: float = 0.0
    dp_charge_inr: float = 15.34
    apply_dp_charges: bool = True
    slippage_bps: float = 5.0

    @classmethod
    def from_config(cls, cfg: dict[str, Any] | None) -> DeliveryCostModel:
        c = cfg or {}
        return cls(
            stt_rate=float(c.get("stt_rate", 0.001)),
            stamp_duty_rate=float(c.get("stamp_duty_rate", 0.00015)),
            exchange_txn_rate=float(c.get("exchange_txn_rate", 0.0000297)),
            sebi_rate=float(c.get("sebi_rate", 0.000001)),
            gst_rate=float(c.get("gst_rate", 0.18)),
            brokerage_rate=float(c.get("brokerage_rate", 0.0)),
            dp_charge_inr=float(c.get("dp_charge_inr", 15.34)),
            apply_dp_charges=bool(c.get("apply_dp_charges", True)),
            slippage_bps=float(c.get("slippage_bps", 5.0)),
        )


def _gstable(brokerage: float, exchange: float, sebi: float) -> float:
    return brokerage + exchange + sebi


def buy_cost_fraction(model: DeliveryCostModel) -> float:
    """Variable cost as fraction of buy notional (excludes flat DP)."""
    brokerage = model.brokerage_rate
    exchange = model.exchange_txn_rate
    sebi = model.sebi_rate
    gst = model.gst_rate * _gstable(brokerage, exchange, sebi)
    slip = model.slippage_bps / 10_000.0
    return model.stt_rate + model.stamp_duty_rate + exchange + sebi + brokerage + gst + slip


def sell_cost_fraction(model: DeliveryCostModel) -> float:
    """Variable cost as fraction of sell notional (excludes flat DP)."""
    brokerage = model.brokerage_rate
    exchange = model.exchange_txn_rate
    sebi = model.sebi_rate
    gst = model.gst_rate * _gstable(brokerage, exchange, sebi)
    slip = model.slippage_bps / 10_000.0
    return model.stt_rate + exchange + sebi + brokerage + gst + slip


def round_trip_variable_fraction(model: DeliveryCostModel) -> float:
    return buy_cost_fraction(model) + sell_cost_fraction(model)


def trade_cost_inr(
    *,
    side: str,
    notional_inr: float,
    model: DeliveryCostModel,
) -> float:
    """Absolute INR cost for one buy or sell of `notional_inr`."""
    if notional_inr < 0:
        raise ValueError("notional_inr must be >= 0")
    if side == "buy":
        return notional_inr * buy_cost_fraction(model)
    if side == "sell":
        cost = notional_inr * sell_cost_fraction(model)
        if model.apply_dp_charges:
            cost += model.dp_charge_inr
        return cost
    raise ValueError("side must be 'buy' or 'sell'")
