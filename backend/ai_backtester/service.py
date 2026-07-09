from __future__ import annotations

from datetime import date, datetime
from typing import Any

import rich_fund_data as fund_data

from .engine import run_backtest
from .models import BacktestConfig, BacktestResult, FundNavPoint


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def _history_to_nav_points(history: list[dict[str, Any]]) -> list[FundNavPoint]:
    points: list[FundNavPoint] = []
    for item in history or []:
        raw_date = item.get("date") or item.get("trade_date") or item.get("nav_date")
        raw_nav = item.get("nav") or item.get("unit_nav") or item.get("close")
        if not raw_date or raw_nav in (None, "", "--", "-"):
            continue
        try:
            points.append(
                FundNavPoint(
                    trade_date=datetime.strptime(str(raw_date), "%Y-%m-%d").date(),
                    unit_nav=float(raw_nav),
                    daily_return=float(item.get("change_percent") or item.get("daily_return") or 0),
                )
            )
        except Exception:
            continue
    points.sort(key=lambda item: item.trade_date)
    return points


def run_ai_backtest_for_fund(
    *,
    fund_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    initial_cash: float = 100000.0,
    trade_amount: float = 10000.0,
    max_position_ratio: float = 0.8,
    buy_fee_rate: float = 0.001,
    sell_fee_rate: float = 0.005,
    refresh: bool = False,
) -> dict[str, Any]:
    """Fetch fund NAV data and run a deterministic AI-style backtest.

    The first phase deliberately uses rule-based signals. This keeps the module
    stable and testable before plugging in a large language model.
    """

    detail = fund_data.get_fund_detail(fund_code, refresh=refresh)
    fund = detail.get("fund") or {}
    history = fund.get("history") or []
    points = _history_to_nav_points(history)

    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start:
        points = [item for item in points if item.trade_date >= start]
    if end:
        points = [item for item in points if item.trade_date <= end]

    if len(points) < 80:
        raise ValueError("有效净值数据不足，至少建议 80 个交易日以上")

    config = BacktestConfig(
        fund_code=fund_code,
        initial_cash=initial_cash,
        trade_amount=trade_amount,
        max_position_ratio=max_position_ratio,
        buy_fee_rate=buy_fee_rate,
        sell_fee_rate=sell_fee_rate,
    )
    result: BacktestResult = run_backtest(points, config)
    payload = result.to_dict()
    payload["fund"] = {
        "symbol": fund.get("symbol") or fund_code,
        "name": fund.get("name") or f"{fund_code} 基金",
        "fund_type": fund.get("fund_type") or "公募基金",
        "latest_nav": fund.get("latest_nav"),
        "daily_change": fund.get("daily_change"),
        "data_source": fund.get("data_source"),
    }
    payload["params"] = {
        "fund_code": fund_code,
        "start_date": start_date,
        "end_date": end_date,
        "initial_cash": initial_cash,
        "trade_amount": trade_amount,
        "max_position_ratio": max_position_ratio,
        "buy_fee_rate": buy_fee_rate,
        "sell_fee_rate": sell_fee_rate,
        "refresh": refresh,
    }
    payload["source_errors"] = detail.get("errors", [])
    payload["disclaimer"] = "仅供学习和模拟研究，不构成投资建议；系统不会连接券商或执行真实交易。"
    return payload
