"""AI-enabled FastAPI entrypoint for MarketSim.

This wrapper keeps the original main.py stable while enabling the AI fund
backtest router and an optional privacy-safe video demo mode.
"""

from pathlib import Path

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from main import app, validation_exception_handler
from ai_backtester.routes import router as ai_backtest_router


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
NO_CACHE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}


@app.exception_handler(RequestValidationError)
async def ai_validation_exception_handler(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/ai-backtest"):
        return await validation_exception_handler(request, exc)

    error = exc.errors()[0] if exc.errors() else {}
    field = next((str(item) for item in reversed(error.get("loc", ())) if item != "body"), "")
    messages = {
        "fund_code": "基金代码必须是 6 位数字",
        "start_date": "开始日期格式必须为 YYYY-MM-DD",
        "end_date": "结束日期格式必须为 YYYY-MM-DD",
        "initial_cash": "初始资金必须大于 0",
        "trade_amount": "单次交易金额必须大于 0",
        "max_position_ratio": "最大仓位必须大于 0 且不超过 1",
        "buy_fee_rate": "买入费率必须大于等于 0 且小于 1",
        "sell_fee_rate": "卖出费率必须大于等于 0 且小于 1",
    }
    message = messages.get(field, "请检查回测参数格式")
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": f"参数错误：{message}", "data": None},
    )


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
