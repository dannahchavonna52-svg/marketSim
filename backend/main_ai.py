"""AI-enabled FastAPI entrypoint for MarketSim.

This wrapper keeps the original main.py stable while enabling the AI fund
backtest router and an optional privacy-safe video demo mode.
"""

from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse

from main import app
from ai_backtester.routes import router as ai_backtest_router


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
NO_CACHE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}


@app.middleware("http")
async def inject_video_demo_assets(request: Request, call_next):
    """Inject demo-only assets for URLs such as /?demo=1&fund=014855.

    Normal application requests are untouched. Demo mode keeps account details
    masked and provides a portrait-friendly layout for screen recording.
    """

    if request.url.path == "/" and request.query_params.get("demo") == "1":
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            html = index_file.read_text(encoding="utf-8")
            html = html.replace(
                "</head>",
                '    <link rel="stylesheet" href="/demo-mode.css?v=20260710-demo1" />\n  </head>',
            )
            html = html.replace(
                "</body>",
                '    <script src="/demo-mode.js?v=20260710-demo1"></script>\n  </body>',
            )
            return HTMLResponse(html, headers=NO_CACHE_HEADERS)
    return await call_next(request)


@app.get("/app-final.js")
def frontend_final_app():
    return FileResponse(FRONTEND_DIR / "app-final.js", headers=NO_CACHE_HEADERS)


@app.get("/ai-backtest.js")
def frontend_ai_backtest_app():
    return FileResponse(FRONTEND_DIR / "ai-backtest.js", headers=NO_CACHE_HEADERS)


@app.get("/demo-mode.js")
def frontend_demo_mode_app():
    return FileResponse(FRONTEND_DIR / "demo-mode.js", headers=NO_CACHE_HEADERS)


@app.get("/demo-mode.css")
def frontend_demo_mode_style():
    return FileResponse(FRONTEND_DIR / "demo-mode.css", headers=NO_CACHE_HEADERS)


app.include_router(ai_backtest_router)
