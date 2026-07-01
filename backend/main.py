from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import crud
import auth
import daily_ops
import advisor_sim
import rich_fund_data as fund_data
import market_data
import rich_news_data as news_data
import rich_scoring as scoring
import rich_signal_data
import trading
from database import get_db, init_db
from models import User
from schemas import AuthRequest, BuyRequest, DailyOperationSettingsRequest, SellRequest, SimAccountRequest, WatchlistCreate


app = FastAPI(
    title="MarketSim Web API",
    description="股票市场关注 + 基金模拟交易本地系统，仅用于学习和模拟。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def ok(data=None, message="ok"):
    return {"success": True, "message": message, "data": data}


def fail(message: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": None},
    )


NO_CACHE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}


@app.on_event("startup")
def startup():
    init_db()
    daily_ops.start_scheduler()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return fail(f"服务器处理失败：{exc}", status_code=500)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return fail(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(item) for item in first_error.get("loc", []) if item != "body")
    message = first_error.get("msg", "参数错误")
    if "username" in field and ("at least 3" in message or "too_short" in str(first_error)):
        message = "用户名至少需要 3 个字符"
        field = ""
    elif "password" in field and ("at least 6" in message or "too_short" in str(first_error)):
        message = "密码至少需要 6 位"
        field = ""
    elif "Field required" in message:
        message = "请把必填项填写完整"
        field = ""
    return fail(f"参数错误：{field} {message}".strip(), status_code=422)


@app.get("/", response_class=HTMLResponse)
def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"), headers=NO_CACHE_HEADERS)
    return "<h1>MarketSim Web</h1><p>frontend/index.html not found.</p>"


@app.get("/style.css")
def frontend_style():
    return FileResponse(FRONTEND_DIR / "style.css", headers=NO_CACHE_HEADERS)


@app.get("/app.js")
def frontend_app():
    return FileResponse(FRONTEND_DIR / "app.js", headers=NO_CACHE_HEADERS)


@app.get("/app-auth.js")
def frontend_auth_app():
    return FileResponse(FRONTEND_DIR / "app-auth.js", headers=NO_CACHE_HEADERS)


@app.get("/app-pages.js")
def frontend_pages_app():
    return FileResponse(FRONTEND_DIR / "app-pages.js", headers=NO_CACHE_HEADERS)


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.webmanifest", media_type="application/manifest+json", headers=NO_CACHE_HEADERS)


@app.get("/service-worker.js")
def service_worker():
    return FileResponse(FRONTEND_DIR / "service-worker.js", media_type="application/javascript", headers=NO_CACHE_HEADERS)


@app.post("/api/auth/register")
def register(payload: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = auth.create_user(db, payload.username, payload.password)
        account = crud.get_or_create_account(db, user)
        session = auth.create_session(db, user)
        return ok(
            {
                "token": session.token,
                "user": auth.serialize_user(user),
                "account": crud.serialize_account(account, []),
            },
            "注册成功",
        )
    except ValueError as exc:
        db.rollback()
        return fail(str(exc))


@app.post("/api/auth/login")
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = auth.authenticate_user(db, payload.username, payload.password)
        account = crud.get_or_create_account(db, user)
        session = auth.create_session(db, user)
        positions = crud.list_positions(db, user)
        return ok(
            {
                "token": session.token,
                "user": auth.serialize_user(user),
                "account": crud.serialize_account(account, positions),
            },
            "登录成功",
        )
    except ValueError as exc:
        return fail(str(exc), status_code=401)


@app.get("/api/auth/me")
def me(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    account = crud.get_or_create_account(db, current_user)
    positions = crud.list_positions(db, current_user)
    return ok(
        {
            "user": auth.serialize_user(current_user),
            "account": crud.serialize_account(account, positions),
        }
    )


@app.post("/api/auth/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        auth.revoke_session(db, authorization.split(" ", 1)[1].strip())
    return ok(True, "已退出登录")


@app.get("/api/account")
def get_account(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    account = crud.get_or_create_account(db, current_user)
    positions = crud.list_positions(db, current_user)
    return ok(crud.serialize_account(account, positions))


@app.get("/api/watchlist")
def get_watchlist(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    items = crud.list_watchlist(db, current_user)
    return ok(
        [
            {
                "id": item.id,
                "symbol": item.symbol,
                "name": item.name,
                "asset_type": item.asset_type,
                "note": item.note,
                "created_at": item.created_at,
            }
            for item in items
        ]
    )


@app.post("/api/watchlist")
def add_watchlist(payload: WatchlistCreate, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    try:
        item = crud.add_watchlist_item(
            db,
            current_user,
            symbol=payload.symbol,
            name=payload.name,
            asset_type=payload.asset_type,
            note=payload.note or "",
        )
        return ok(
            {
                "id": item.id,
                "symbol": item.symbol,
                "name": item.name,
                "asset_type": item.asset_type,
                "note": item.note,
                "created_at": item.created_at,
            },
            "添加成功",
        )
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        return fail(str(exc))


@app.delete("/api/watchlist/{item_id}")
def delete_watchlist(item_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not crud.delete_watchlist_item(db, current_user, item_id):
        return fail("未找到该自选标的", status_code=404)
    return ok(True, "删除成功")


@app.get("/api/quotes")
def get_quotes(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    items = crud.list_watchlist(db, current_user)
    return ok(market_data.get_quotes(items))


@app.get("/api/positions")
def get_positions(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    positions = crud.list_positions(db, current_user)
    return ok([crud.serialize_position(item) for item in positions])


@app.post("/api/trade/buy")
def buy_trade(payload: BuyRequest, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    try:
        result = trading.buy(
            db,
            current_user,
            symbol=payload.symbol,
            name=payload.name,
            asset_type=payload.asset_type,
            price=payload.price,
            quantity=payload.quantity,
            fee=payload.fee,
        )
        positions = crud.list_positions(db, current_user)
        return ok(
            {
                "account": crud.serialize_account(result["account"], positions),
                "position": crud.serialize_position(result["position"]),
                "trade": crud.serialize_trade(result["trade"]),
            },
            "买入成功",
        )
    except ValueError as exc:
        db.rollback()
        return fail(str(exc))


@app.post("/api/trade/sell")
def sell_trade(payload: SellRequest, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    try:
        result = trading.sell(
            db,
            current_user,
            symbol=payload.symbol,
            asset_type=payload.asset_type,
            price=payload.price,
            quantity=payload.quantity,
            fee=payload.fee,
        )
        positions = crud.list_positions(db, current_user)
        return ok(
            {
                "account": crud.serialize_account(result["account"], positions),
                "position": crud.serialize_position(result["position"]) if result["position"] else None,
                "trade": crud.serialize_trade(result["trade"]),
            },
            "卖出成功",
        )
    except ValueError as exc:
        db.rollback()
        return fail(str(exc))


@app.get("/api/trades")
def get_trades(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    trades = crud.list_trades(db, current_user)
    return ok([crud.serialize_trade(item) for item in trades])


@app.post("/api/refresh")
def refresh_positions(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    positions = crud.list_positions(db, current_user)
    updated = 0
    errors = []
    for position in positions:
        result = market_data.get_quote(position.symbol, position.asset_type)
        if result["success"] and result["data"].get("price"):
            crud.update_position_price(position, result["data"]["price"])
            updated += 1
        else:
            errors.append(result["error"])
    db.commit()
    account = crud.get_or_create_account(db, current_user)
    return ok(
        {
            "updated": updated,
            "errors": errors,
            "account": crud.serialize_account(account, crud.list_positions(db, current_user)),
            "positions": [crud.serialize_position(item) for item in crud.list_positions(db, current_user)],
        },
        "刷新完成" if not errors else "部分行情刷新失败",
    )


@app.get("/api/market/indices")
def market_indices():
    return ok(market_data.get_major_indices())


@app.get("/api/funds/search")
def search_funds(q: str = "", refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    return ok(fund_data.search_funds(q, refresh=refresh))


@app.get("/api/funds/recommendations")
def fund_recommendations(refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    data = fund_data.recommendation_pool(refresh=refresh)
    items = data["funds"][:20]
    enriched_by_symbol = {}

    def enrich(item):
        copied = dict(item)
        try:
            trend = fund_data.get_fund_trend(copied["symbol"], refresh=refresh)
            copied.update(
                {
                    "history": trend.get("history", [])[-45:],
                    "latest_nav": trend.get("latest_nav", copied.get("latest_nav")),
                    "daily_change": trend.get("daily_change", copied.get("daily_change")),
                }
            )
        except Exception:
            pass
        return copied

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(enrich, item) for item in items]
        for future in as_completed(futures):
            item = future.result()
            enriched_by_symbol[item.get("symbol")] = item
    enriched = [enriched_by_symbol.get(item.get("symbol"), item) for item in items]
    return ok(
        {
            "recommendations": scoring.recommendation_buckets(enriched or data["funds"]),
            "source_errors": data.get("errors", []),
            "updated_at": data.get("updated_at"),
        }
    )


@app.get("/api/funds/my-analysis")
def my_fund_analysis(refresh: bool = False, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    positions = crud.list_positions(db, current_user)
    watchlist = crud.list_watchlist(db, current_user)
    market = news_data.get_market_news(limit=50, refresh=refresh)
    rows = []
    seen = set()

    fund_symbols = []
    for position in positions:
        if position.asset_type == "fund":
            fund_symbols.append((position.symbol, "position", position))
    for item in watchlist:
        if item.asset_type == "fund" and item.symbol not in [symbol for symbol, _, _ in fund_symbols]:
            fund_symbols.append((item.symbol, "watch", item))

    for symbol, relation, source in fund_symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        detail = fund_data.get_fund_detail(symbol, refresh=refresh)
        fund = detail["fund"]
        matched = news_data.match_news_for_funds(market["news"], [fund])
        position_payload = None
        if relation == "position":
            position_payload = crud.serialize_position(source)
            if fund.get("latest_nav"):
                quantity = float(source.quantity or 0)
                avg_cost = float(source.avg_cost or 0)
                latest = float(fund.get("latest_nav") or source.current_price or avg_cost or 0)
                market_value = round(quantity * latest, 2)
                profit = round((latest - avg_cost) * quantity, 2)
                position_payload.update(
                    {
                        "current_price": latest,
                        "market_value": market_value,
                        "profit": profit,
                        "profit_rate": round((latest / avg_cost - 1) * 100, 2) if avg_cost else 0,
                    }
                )
        advice = scoring.recommendation_index(fund, matched, position=position_payload)

        rows.append(
            {
                "relation": relation,
                "fund": fund,
                "position": position_payload,
                "advice": advice,
                "related_news_count": len(matched),
                "latest_news": matched[:3],
                "updated_at": fund.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "errors": detail.get("errors", []),
            }
        )

    return ok(
        {
            "items": rows,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "disclaimer": scoring.DISCLAIMER,
        }
    )


@app.get("/api/funds/{symbol}")
def fund_detail(symbol: str, refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    detail = fund_data.get_fund_detail(symbol, refresh=refresh)
    score = scoring.score_fund(detail["fund"])
    advice = scoring.recommendation_index(detail["fund"])
    return ok({"detail": detail, "score": score, "advice": advice})


@app.get("/api/funds/{symbol}/score")
def fund_score(symbol: str, refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    detail = fund_data.get_fund_detail(symbol, refresh=refresh)
    return ok({"score": scoring.score_fund(detail["fund"]), "advice": scoring.recommendation_index(detail["fund"])})


@app.get("/api/funds/{symbol}/advice")
def fund_advice(symbol: str, refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    detail = fund_data.get_fund_detail(symbol, refresh=refresh)
    market = news_data.get_market_news(limit=50, refresh=refresh)
    matched = news_data.match_news_for_funds(market["news"], [detail["fund"]])
    advice = scoring.recommendation_index(detail["fund"], matched)
    return ok(
        {
            "fund": detail["fund"],
            "score": scoring.score_fund(detail["fund"]),
            "advice": advice,
            "related_news": matched,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


@app.get("/api/news/market")
def market_news(limit: int = 50, refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    return ok(news_data.get_market_news(limit=limit, refresh=refresh))


@app.get("/api/data/status")
def data_status(current_user: User = Depends(auth.get_current_user)):
    return ok(
        {
            "funds": fund_data.data_status(),
            "news": {
                "source": "新浪财经/东方财富公开资讯",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "notice": "基金净值以公开基金平台披露为准，通常不是股票那种秒级成交数据。",
        }
    )


@app.get("/api/news/my-funds")
def my_fund_news(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    positions = crud.list_positions(db, current_user)
    watchlist = crud.list_watchlist(db, current_user)
    symbols = []
    for item in positions + watchlist:
        if item.asset_type == "fund" and item.symbol not in symbols:
            symbols.append(item.symbol)
    funds = [fund_data.get_fund_detail(symbol)["fund"] for symbol in symbols]
    market = news_data.get_market_news(limit=50)
    matched = news_data.match_news_for_funds(market["news"], funds)
    advice = [
        {
            "fund": fund,
            "advice": scoring.recommendation_index(
                fund,
                [item for item in matched if item.get("fund", {}).get("symbol") == fund.get("symbol")],
            ),
        }
        for fund in funds
    ]
    return ok(
        {
            "matched": matched,
            "advice": advice,
            "watched_funds": funds,
            "updated_at": market.get("updated_at"),
            "disclaimer": scoring.DISCLAIMER,
        }
    )


@app.get("/api/daily-ops/settings")
def daily_operation_settings(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    setting = daily_ops.get_or_create_setting(db, current_user)
    return ok(daily_ops.setting_to_dict(setting))


@app.post("/api/daily-ops/settings")
def save_daily_operation_settings(
    payload: DailyOperationSettingsRequest,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    setting = daily_ops.update_setting(db, current_user, payload.enabled, payload.run_time, payload.email or "")
    return ok(daily_ops.setting_to_dict(setting), "每日模拟操作设置已保存")


@app.post("/api/daily-ops/run")
def run_daily_operation_now(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    setting = daily_ops.get_or_create_setting(db, current_user)
    log = daily_ops.run_for_user(db, current_user, setting.email or "")
    setting.last_run_date = datetime.now().strftime("%Y-%m-%d")
    db.commit()
    return ok(daily_ops.log_to_dict(log), "已生成本次模拟操作记录")


@app.get("/api/daily-ops/logs")
def daily_operation_logs(limit: int = 20, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return ok({"logs": daily_ops.list_logs(db, current_user, limit=max(1, min(limit, 50)))})


@app.get("/api/signals/smart-money")
def smart_money_signals(refresh: bool = False, current_user: User = Depends(auth.get_current_user)):
    return ok(rich_signal_data.get_smart_money_signals(limit=12, refresh=refresh))


@app.get("/api/advisor-sim")
def advisor_sim_dashboard(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return ok(advisor_sim.get_dashboard(db, current_user))


@app.post("/api/advisor-sim/run")
def run_advisor_sim(refresh: bool = False, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return ok(advisor_sim.run_strategy_once(db, current_user, refresh=refresh), "系统模拟操作已完成")


@app.post("/api/sim/account")
def set_sim_account(payload: SimAccountRequest, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    positions = crud.list_positions(db, current_user)
    trades = crud.list_trades(db, current_user)
    if positions or trades:
        return fail("已有持仓或交易记录时不能直接重置初始资金，请新注册账号或先手动清仓。")
    account = crud.get_or_create_account(db, current_user)
    account.initial_cash = payload.initial_cash
    account.cash = payload.initial_cash
    db.commit()
    db.refresh(account)
    return ok(crud.serialize_account(account, []), "模拟账户设置成功")


@app.get("/api/sim/performance")
def performance(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    account = crud.get_or_create_account(db, current_user)
    positions = crud.list_positions(db, current_user)
    trades = list(reversed(crud.list_trades(db, current_user)))
    curve = [{"label": "初始", "asset": account.initial_cash, "return_rate": 0.0}]
    cash = account.initial_cash
    holding_cost = 0.0
    for trade in trades:
        if trade.side == "buy":
            cash -= trade.amount + trade.fee
            holding_cost += trade.amount + trade.fee
        else:
            cash += trade.amount - trade.fee
            holding_cost = max(0.0, holding_cost - trade.amount + trade.profit)
        asset = cash + holding_cost
        curve.append(
            {
                "label": str(trade.created_at).replace("T", " ")[:16],
                "asset": round(asset, 2),
                "return_rate": round((asset - account.initial_cash) / account.initial_cash * 100, 2) if account.initial_cash else 0,
            }
        )
    summary = crud.serialize_account(account, positions)
    curve.append(
        {
            "label": "当前",
            "asset": round(summary.get("total_asset", account.initial_cash), 2),
            "return_rate": round(summary.get("total_profit_rate", 0), 2),
        }
    )
    return ok({"summary": summary, "curve": curve, "disclaimer": scoring.DISCLAIMER})
