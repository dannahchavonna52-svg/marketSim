from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


SignalAction = Literal["buy", "sell", "hold"]


@dataclass(frozen=True)
class FundNavPoint:
    """One historical fund NAV point.

    For OTC funds, unit_nav is the main tradable value. For ETFs, unit_nav can
    be replaced by close price in the adapter layer.
    """

    trade_date: date
    unit_nav: float
    accumulated_nav: float | None = None
    daily_return: float | None = None

    @classmethod
    def from_dict(cls, item: dict) -> "FundNavPoint":
        raw_date = item.get("trade_date") or item.get("date") or item.get("nav_date")
        if isinstance(raw_date, datetime):
            trade_date = raw_date.date()
        elif isinstance(raw_date, date):
            trade_date = raw_date
        else:
            trade_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()

        raw_nav = item.get("unit_nav") or item.get("nav") or item.get("close")
        if raw_nav is None:
            raise ValueError("FundNavPoint requires unit_nav/nav/close")

        return cls(
            trade_date=trade_date,
            unit_nav=float(raw_nav),
            accumulated_nav=(
                float(item["accumulated_nav"])
                if item.get("accumulated_nav") is not None
                else None
            ),
            daily_return=(
                float(item["daily_return"])
                if item.get("daily_return") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class AgentSignal:
    action: SignalAction
    confidence: int
    reasoning: str


@dataclass
class BacktestConfig:
    fund_code: str
    initial_cash: float = 100000.0
    trade_amount: float = 10000.0
    max_position_ratio: float = 0.8
    buy_fee_rate: float = 0.0
    sell_fee_rate: float = 0.0
    min_hold_days: int = 0


@dataclass
class TradeRecord:
    trade_date: date
    fund_code: str
    action: SignalAction
    nav: float
    amount: float
    units: float
    fee: float
    cash_after: float
    units_after: float
    reasoning: str


@dataclass
class DailyPortfolioPoint:
    trade_date: date
    nav: float
    cash: float
    units: float
    market_value: float
    total_value: float
    drawdown_pct: float
    signal: SignalAction
    reasoning: str


@dataclass
class BacktestResult:
    fund_code: str
    initial_cash: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[DailyPortfolioPoint] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "fund_code": self.fund_code,
            "summary": {
                "initial_cash": self.initial_cash,
                "final_value": self.final_value,
                "total_return_pct": self.total_return_pct,
                "max_drawdown_pct": self.max_drawdown_pct,
            },
            "trades": [
                {
                    "trade_date": t.trade_date.isoformat(),
                    "fund_code": t.fund_code,
                    "action": t.action,
                    "nav": t.nav,
                    "amount": t.amount,
                    "units": t.units,
                    "fee": t.fee,
                    "cash_after": t.cash_after,
                    "units_after": t.units_after,
                    "reasoning": t.reasoning,
                }
                for t in self.trades
            ],
            "equity_curve": [
                {
                    "trade_date": p.trade_date.isoformat(),
                    "nav": p.nav,
                    "cash": p.cash,
                    "units": p.units,
                    "market_value": p.market_value,
                    "total_value": p.total_value,
                    "drawdown_pct": p.drawdown_pct,
                    "signal": p.signal,
                    "reasoning": p.reasoning,
                }
                for p in self.equity_curve
            ],
        }
