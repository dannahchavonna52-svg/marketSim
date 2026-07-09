"""AI fund backtesting package for MarketSim.

This package is intentionally lightweight in the first phase. It does not
place real trades and does not provide investment advice.
"""

from .engine import run_backtest
from .models import (
    BacktestConfig,
    BacktestResult,
    DailyPortfolioPoint,
    FundNavPoint,
    TradeRecord,
)

__all__ = [
    "run_backtest",
    "BacktestConfig",
    "BacktestResult",
    "DailyPortfolioPoint",
    "FundNavPoint",
    "TradeRecord",
]
