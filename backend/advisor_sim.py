from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import crud
import rich_fund_data
import rich_news_data
import rich_scoring
import rich_signal_data
from models import AdvisorSimAccount, AdvisorSimPosition, AdvisorSimSnapshot, AdvisorSimTrade, User


INITIAL_CASH = 100000.0
MAX_POSITION_WEIGHT = 0.18
BUY_AMOUNT = 10000.0
MIN_TRADE_AMOUNT = 1000.0


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def get_or_create_account(db, user: User) -> AdvisorSimAccount:
    account = db.query(AdvisorSimAccount).filter(AdvisorSimAccount.user_id == user.id).first()
    if account:
        return account
    account = AdvisorSimAccount(user_id=user.id, cash=INITIAL_CASH, initial_cash=INITIAL_CASH)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _position_payload(position: AdvisorSimPosition) -> dict[str, Any]:
    return {
        "id": position.id,
        "symbol": position.symbol,
        "name": position.name,
        "quantity": round(position.quantity, 4),
        "avg_cost": round(position.avg_cost, 4),
        "current_nav": round(position.current_nav, 4),
        "market_value": round(position.market_value, 2),
        "profit": round(position.profit, 2),
        "profit_rate": round(position.profit_rate, 2),
        "last_action": position.last_action or "",
        "updated_at": position.updated_at,
    }


def _trade_payload(trade: AdvisorSimTrade) -> dict[str, Any]:
    try:
        evidence = json.loads(trade.evidence_json or "[]")
    except Exception:
        evidence = []
    try:
        signals = json.loads(trade.signal_json or "[]")
    except Exception:
        signals = []
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "name": trade.name,
        "side": trade.side,
        "price": round(trade.price, 4),
        "quantity": round(trade.quantity, 4),
        "amount": round(trade.amount, 2),
        "profit": round(trade.profit, 2),
        "reason": trade.reason or "",
        "evidence": evidence,
        "signals": signals,
        "created_at": trade.created_at,
    }


def _refresh_position(position: AdvisorSimPosition, fund: dict[str, Any]) -> None:
    nav = _num(fund.get("estimated_nav")) or _num(fund.get("latest_nav")) or position.current_nav
    position.current_nav = nav
    position.market_value = position.quantity * nav
    position.profit = (nav - position.avg_cost) * position.quantity
    position.profit_rate = ((nav / position.avg_cost - 1) * 100) if position.avg_cost else 0.0


def _snapshot(db, user: User, summary: str = "") -> AdvisorSimSnapshot:
    account = get_or_create_account(db, user)
    positions = db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id).all()
    market_value = sum(position.market_value for position in positions)
    total = account.cash + market_value
    profit = total - account.initial_cash
    profit_rate = (profit / account.initial_cash * 100) if account.initial_cash else 0.0
    snap = AdvisorSimSnapshot(
        user_id=user.id,
        total_asset=total,
        cash=account.cash,
        market_value=market_value,
        profit=profit,
        profit_rate=profit_rate,
        summary=summary,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _summary(db, user: User) -> dict[str, Any]:
    account = get_or_create_account(db, user)
    positions = db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id).order_by(AdvisorSimPosition.market_value.desc()).all()
    market_value = sum(position.market_value for position in positions)
    total = account.cash + market_value
    profit = total - account.initial_cash
    profit_rate = (profit / account.initial_cash * 100) if account.initial_cash else 0.0
    return {
        "cash": round(account.cash, 2),
        "initial_cash": round(account.initial_cash, 2),
        "market_value": round(market_value, 2),
        "total_asset": round(total, 2),
        "profit": round(profit, 2),
        "profit_rate": round(profit_rate, 2),
        "position_count": len(positions),
        "updated_at": _now(),
    }


def _candidate_symbols(db, user: User) -> list[str]:
    symbols: list[str] = []
    for item in crud.list_watchlist(db, user):
        if item.asset_type == "fund" and item.symbol not in symbols:
            symbols.append(item.symbol)
    for item in db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id).all():
        if item.symbol not in symbols:
            symbols.append(item.symbol)
    try:
        pool = rich_fund_data.recommendation_pool()
        for fund in pool.get("funds", [])[:12]:
            if fund.get("symbol") and fund["symbol"] not in symbols:
                symbols.append(fund["symbol"])
    except Exception:
        pass
    return symbols[:10]


def run_strategy_once(db, user: User, refresh: bool = False) -> dict[str, Any]:
    account = get_or_create_account(db, user)
    errors: list[str] = []
    try:
        market_news = rich_news_data.get_market_news(limit=50, refresh=refresh)
    except Exception as exc:
        market_news = {"news": [], "errors": [str(exc)]}
        errors.append(f"资讯读取失败：{exc}")
    try:
        signals = rich_signal_data.get_smart_money_signals(limit=10, refresh=refresh)
    except Exception as exc:
        signals = {"signals": [], "flows": [], "errors": [str(exc)]}
        errors.append(f"资金流读取失败：{exc}")
    symbols = _candidate_symbols(db, user)
    operations: list[dict[str, Any]] = []

    existing_positions = db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id).count()
    for symbol in symbols:
        try:
            detail = rich_fund_data.get_fund_detail(symbol, refresh=refresh)
        except Exception as exc:
            errors.append(f"{symbol} 基金数据读取失败：{exc}")
            continue
        fund = detail.get("fund", {})
        if not fund:
            errors.append(f"{symbol} 暂无基金详情数据")
            continue
        position = db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id, AdvisorSimPosition.symbol == symbol).first()
        if position:
            _refresh_position(position, fund)
        position_dict = _position_payload(position) if position else None
        try:
            matched_news = rich_news_data.match_news_for_funds(market_news.get("news", []), [fund])
        except Exception:
            matched_news = []
        try:
            advice = rich_scoring.recommendation_index(fund, matched_news, position=position_dict)
        except Exception as exc:
            errors.append(f"{fund.get('name') or symbol} 评分失败：{exc}")
            continue
        try:
            signal_hits = rich_signal_data.signals_for_fund(fund, signals)
        except Exception:
            signal_hits = []
        evidence = list(advice.get("evidence", [])) + signal_hits
        risk_flags = advice.get("risk_flags", [])
        nav = _num(fund.get("estimated_nav")) or _num(fund.get("latest_nav"))
        if nav <= 0:
            continue

        side = "hold"
        quantity = 0.0
        amount = 0.0
        profit = 0.0
        reason = advice.get("reason_sentence") or advice.get("plain_explanation") or "信号不足，继续观察。"

        total_before = _summary(db, user)["total_asset"]
        current_weight = (position.market_value / total_before) if position and total_before else 0.0
        buy_threshold = 60 if existing_positions == 0 else 72
        sell_limit = 72 if existing_positions == 0 else 60
        if advice["buy_index"] >= buy_threshold and advice["sell_index"] < sell_limit and account.cash >= MIN_TRADE_AMOUNT and current_weight < MAX_POSITION_WEIGHT:
            side = "buy"
            if existing_positions == 0 and "买" not in str(advice.get("action", "")):
                reason = f"系统启动建仓理由：当前为空仓，买入指数 {advice['buy_index']:.1f}、卖出/减仓指数 {advice['sell_index']:.1f}，先用小仓位跟踪验证；核心依据是 {'；'.join(evidence[:3])}。"
            amount = min(BUY_AMOUNT, account.cash, max(MIN_TRADE_AMOUNT, total_before * MAX_POSITION_WEIGHT - (position.market_value if position else 0)))
            quantity = amount / nav
            if position:
                new_qty = position.quantity + quantity
                position.avg_cost = ((position.avg_cost * position.quantity) + amount) / new_qty
                position.quantity = new_qty
            else:
                position = AdvisorSimPosition(
                    user_id=user.id,
                    symbol=symbol,
                    name=fund.get("name") or symbol,
                    quantity=quantity,
                    avg_cost=nav,
                    current_nav=nav,
                    market_value=amount,
                    profit=0.0,
                    profit_rate=0.0,
                )
                db.add(position)
            account.cash -= amount
            position.last_action = "系统模拟买入"
            _refresh_position(position, fund)
            existing_positions += 1
        elif position and advice["sell_index"] >= 72:
            side = "sell"
            sell_ratio = 0.5 if advice["sell_index"] < 85 else 1.0
            quantity = position.quantity * sell_ratio
            amount = quantity * nav
            profit = (nav - position.avg_cost) * quantity
            reason = f"系统模拟减仓理由：卖出/减仓指数 {advice['sell_index']:.1f} 已达到阈值，买入指数 {advice['buy_index']:.1f}。主要依据：{'；'.join(evidence[:3]) or reason}"
            account.cash += amount
            position.quantity -= quantity
            position.last_action = "系统模拟减仓" if position.quantity > 0.0001 else "系统模拟清仓"
            if position.quantity <= 0.0001:
                db.delete(position)
            else:
                _refresh_position(position, fund)
        else:
            side = "hold"
            if position:
                position.last_action = "系统继续持有观察"

        if side in {"buy", "sell"}:
            trade = AdvisorSimTrade(
                user_id=user.id,
                symbol=symbol,
                name=fund.get("name") or symbol,
                side=side,
                price=nav,
                quantity=quantity,
                amount=amount,
                profit=profit,
                reason=reason,
                evidence_json=json.dumps(evidence[:6] + list(risk_flags[:3]), ensure_ascii=False),
                signal_json=json.dumps(signal_hits, ensure_ascii=False),
            )
            db.add(trade)
            db.flush()
            operations.append(_trade_payload(trade))

    db.commit()
    snap = _snapshot(db, user, f"本次系统模拟执行 {len(operations)} 笔操作。")
    message = f"本次系统模拟执行 {len(operations)} 笔操作。"
    if not operations:
        message += "没有操作不代表失败，而是当前信号未达到买入/减仓阈值。"
    return {
        "summary": _summary(db, user),
        "operations": operations,
        "snapshot": {
            "total_asset": round(snap.total_asset, 2),
            "profit": round(snap.profit, 2),
            "profit_rate": round(snap.profit_rate, 2),
            "created_at": snap.created_at,
        },
        "signals": signals,
        "errors": errors[:8],
        "message": message,
        "disclaimer": rich_scoring.DISCLAIMER,
    }


def get_dashboard(db, user: User) -> dict[str, Any]:
    account = get_or_create_account(db, user)
    positions = db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id).order_by(AdvisorSimPosition.market_value.desc()).all()
    for position in positions:
        try:
            detail = rich_fund_data.get_fund_detail(position.symbol)
            _refresh_position(position, detail.get("fund", {}))
        except Exception:
            pass
    db.commit()
    positions = db.query(AdvisorSimPosition).filter(AdvisorSimPosition.user_id == user.id).order_by(AdvisorSimPosition.market_value.desc()).all()
    trades = db.query(AdvisorSimTrade).filter(AdvisorSimTrade.user_id == user.id).order_by(AdvisorSimTrade.created_at.desc(), AdvisorSimTrade.id.desc()).limit(30).all()
    snapshots = db.query(AdvisorSimSnapshot).filter(AdvisorSimSnapshot.user_id == user.id).order_by(AdvisorSimSnapshot.created_at.asc(), AdvisorSimSnapshot.id.asc()).limit(200).all()
    if not snapshots:
        _snapshot(db, user, "初始化系统模拟账户")
        snapshots = db.query(AdvisorSimSnapshot).filter(AdvisorSimSnapshot.user_id == user.id).order_by(AdvisorSimSnapshot.created_at.asc(), AdvisorSimSnapshot.id.asc()).limit(200).all()
    return {
        "summary": _summary(db, user),
        "positions": [_position_payload(item) for item in positions],
        "trades": [_trade_payload(item) for item in trades],
        "curve": [
            {
                "time": item.created_at.isoformat() if item.created_at else "",
                "total_asset": round(item.total_asset, 2),
                "profit_rate": round(item.profit_rate, 2),
            }
            for item in snapshots
        ],
        "signals": rich_signal_data.get_smart_money_signals(limit=8),
        "disclaimer": rich_scoring.DISCLAIMER,
    }
