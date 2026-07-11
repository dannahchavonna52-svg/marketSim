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
from .service import run_ai_backtest_for_fund

__all__ = [
    "run_backtest",
    "run_ai_backtest_for_fund",
    "BacktestConfig",
    "BacktestResult",
    "DailyPortfolioPoint",
    "FundNavPoint",
    "TradeRecord",
]
