"""AI-enabled FastAPI entrypoint for MarketSim.

This wrapper keeps the original main.py stable while enabling the AI fund
backtest router for local trial runs.
"""

from main import app
from ai_backtester.routes import router as ai_backtest_router


app.include_router(ai_backtest_router)
