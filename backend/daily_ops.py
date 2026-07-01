import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List

import crud
import rich_fund_data as fund_data
import rich_news_data as news_data
import rich_scoring as scoring
from database import SessionLocal
from models import DailyOperationLog, DailyOperationSetting, User


_started = False


def setting_to_dict(setting: DailyOperationSetting | None) -> Dict[str, Any]:
    if not setting:
        return {"enabled": False, "run_time": "02:55", "email": "", "last_run_date": ""}
    return {
        "enabled": bool(setting.enabled),
        "run_time": setting.run_time or "02:55",
        "email": setting.email or "",
        "last_run_date": setting.last_run_date or "",
    }


def get_or_create_setting(db, user: User) -> DailyOperationSetting:
    setting = db.query(DailyOperationSetting).filter(DailyOperationSetting.user_id == user.id).first()
    if not setting:
        setting = DailyOperationSetting(user_id=user.id, enabled=0, run_time="02:55", email="")
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def update_setting(db, user: User, enabled: bool, run_time: str, email: str) -> DailyOperationSetting:
    setting = get_or_create_setting(db, user)
    setting.enabled = 1 if enabled else 0
    setting.run_time = run_time or "02:55"
    setting.email = (email or "").strip()
    db.commit()
    db.refresh(setting)
    return setting


def log_to_dict(log: DailyOperationLog) -> Dict[str, Any]:
    detail = {}
    try:
        detail = json.loads(log.detail_json or "{}")
    except Exception:
        detail = {}
    return {
        "id": log.id,
        "run_at": log.run_at.isoformat() if log.run_at else "",
        "run_date": log.run_date,
        "summary": log.summary,
        "detail": detail,
        "email": log.email or "",
        "email_status": log.email_status or "",
        "email_error": log.email_error or "",
    }


def list_logs(db, user: User, limit: int = 20) -> List[Dict[str, Any]]:
    rows = (
        db.query(DailyOperationLog)
        .filter(DailyOperationLog.user_id == user.id)
        .order_by(DailyOperationLog.run_at.desc(), DailyOperationLog.id.desc())
        .limit(limit)
        .all()
    )
    return [log_to_dict(row) for row in rows]


def _decision_for_fund(fund: Dict[str, Any], relation: str, position: Dict[str, Any] | None, matched_news: List[Dict[str, Any]]) -> Dict[str, Any]:
    advice = scoring.recommendation_index(fund, matched_news, position=position)
    action = advice.get("action") or "观察"
    if position and float(position.get("profit_rate") or 0) > 12 and advice.get("sell_index", 0) >= 55:
        action = "止盈观察"
    elif position and float(position.get("profit_rate") or 0) < -10 and advice.get("sell_index", 0) >= 60:
        action = "风险复查"
    reason = advice.get("reason_sentence") or advice.get("plain_explanation") or ""
    evidence = advice.get("evidence") or []
    if evidence:
        reason = f"{reason} 主要依据：{'；'.join(str(item) for item in evidence[:3])}"

    return {
        "symbol": fund.get("symbol"),
        "name": fund.get("name"),
        "relation": relation,
        "action": action,
        "buy_index": advice.get("buy_index"),
        "hold_index": advice.get("hold_index"),
        "sell_index": advice.get("sell_index"),
        "reason": reason or "公开数据不足，暂时只做观察，不做激进操作。",
        "latest_nav": fund.get("latest_nav"),
        "daily_change": fund.get("daily_change"),
        "position": position,
        "related_news_count": len(matched_news),
        "evidence": evidence[:5],
        "risk_flags": advice.get("risk_flags", [])[:5],
    }


def build_operation_report(db, user: User, refresh: bool = False) -> Dict[str, Any]:
    positions = crud.list_positions(db, user)
    watchlist = crud.list_watchlist(db, user)
    market = news_data.get_market_news(limit=50, refresh=refresh)

    symbols: List[dict[str, Any]] = []
    for position in positions:
        if position.asset_type == "fund":
            symbols.append({"symbol": position.symbol, "relation": "已买入", "name": position.name, "position": crud.serialize_position(position)})
    existing = {item["symbol"] for item in symbols}
    for watch in watchlist:
        if watch.asset_type == "fund" and watch.symbol not in existing:
            symbols.append({"symbol": watch.symbol, "relation": "自选", "name": watch.name, "position": None})
            existing.add(watch.symbol)
    if not symbols:
        try:
            pool = fund_data.recommendation_pool(refresh=refresh)
            for fund in pool.get("funds", [])[:12]:
                symbol = fund.get("symbol")
                if symbol and symbol not in existing:
                    symbols.append({"symbol": symbol, "relation": "系统筛选", "name": fund.get("name") or symbol, "position": None})
                    existing.add(symbol)
        except Exception:
            pass

    def analyze(item: dict[str, Any]) -> dict[str, Any]:
        symbol = item["symbol"]
        relation = item["relation"]
        try:
            detail = fund_data.get_fund_detail(symbol, refresh=refresh)
            fund = detail["fund"]
            matched = news_data.match_news_for_funds(market.get("news", []), [fund])
            position_payload = dict(item.get("position") or {}) or None
            if relation == "已买入":
                latest = float(fund.get("latest_nav") or position_payload.get("current_price") or 0)
                avg_cost = float(position_payload.get("avg_cost") or 0)
                quantity = float(position_payload.get("quantity") or 0)
                if latest and avg_cost:
                    position_payload["current_price"] = latest
                    position_payload["market_value"] = round(quantity * latest, 2)
                    position_payload["profit"] = round((latest - avg_cost) * quantity, 2)
                    position_payload["profit_rate"] = round((latest / avg_cost - 1) * 100, 2)
            return _decision_for_fund(fund, relation, position_payload, matched)
        except Exception as exc:
            return {
                "symbol": symbol,
                "name": item.get("name") or symbol,
                "relation": relation,
                "action": "数据暂缺",
                "buy_index": 0,
                "hold_index": 0,
                "sell_index": 0,
                "reason": f"该基金本次数据读取失败，先不做操作。原因：{exc}",
                "latest_nav": None,
                "daily_change": None,
                "position": None,
                "related_news_count": 0,
                "evidence": [],
                "risk_flags": ["数据源异常"],
            }

    decisions = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(analyze, item): index for index, item in enumerate(symbols[:24])}
        ordered: dict[int, dict[str, Any]] = {}
        for future in as_completed(future_map):
            ordered[future_map[future]] = future.result()
        decisions = [ordered[index] for index in sorted(ordered)]

    buy_count = sum(1 for item in decisions if "买" in item["action"])
    sell_count = sum(1 for item in decisions if "卖" in item["action"] or "止盈" in item["action"] or "风险" in item["action"])
    hold_count = len(decisions) - buy_count - sell_count
    summary = f"今日完成 {len(decisions)} 只基金模拟复盘：关注买入 {buy_count} 只，持有观察 {hold_count} 只，卖出/风险观察 {sell_count} 只。"

    return {
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "decisions": decisions,
        "market_news": market.get("news", [])[:8],
        "disclaimer": scoring.DISCLAIMER,
    }


def run_for_user(db, user: User, email: str = "") -> DailyOperationLog:
    report = build_operation_report(db, user, refresh=False)
    log = DailyOperationLog(
        user_id=user.id,
        run_date=report["run_date"],
        summary=report["summary"],
        detail_json=json.dumps(report, ensure_ascii=False),
        email="",
        email_status="disabled",
        email_error="邮件发送功能已关闭，当前只在本地保存自动操作记录。",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def run_due_jobs_once() -> None:
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        settings = db.query(DailyOperationSetting).filter(DailyOperationSetting.enabled == 1).all()
        for setting in settings:
            if setting.last_run_date == today:
                continue
            if current_time < (setting.run_time or "02:55"):
                continue
            user = db.query(User).filter(User.id == setting.user_id).first()
            if not user:
                continue
            run_for_user(db, user, setting.email or "")
            setting.last_run_date = today
            db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                run_due_jobs_once()
            except Exception:
                pass
            time.sleep(60)

    thread = threading.Thread(target=loop, name="marketsim-daily-ops", daemon=True)
    thread.start()
