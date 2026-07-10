"""AI-enabled FastAPI entrypoint for MarketSim.

This wrapper keeps the original main.py stable while enabling the AI fund
backtest router for local trial runs.
"""

from pathlib import Path

from fastapi.responses import FileResponse

from main import app
from ai_backtester.routes import router as ai_backtest_router


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
NO_CACHE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}


@app.get("/app-final.js")
def frontend_final_app():
    return FileResponse(FRONTEND_DIR / "app-final.js", headers=NO_CACHE_HEADERS)


@app.get("/ai-backtest.js")
def frontend_ai_backtest_app():
    return FileResponse(FRONTEND_DIR / "ai-backtest.js", headers=NO_CACHE_HEADERS)


app.include_router(ai_backtest_router)
