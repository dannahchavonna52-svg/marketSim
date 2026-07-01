from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

import rich_news_data


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value or "").replace("%", "").replace(",", "").strip()
        if text in {"", "-", "--", "nan", "None"}:
            return default
        return float(text)
    except Exception:
        return default


def _fallback_flows() -> list[dict[str, Any]]:
    return [
        {"name": "人工智能/算力", "net_inflow": 0.0, "change_percent": 0.0, "heat": "高", "hint": "公开资金流接口异常时的观察方向，需结合资讯确认。"},
        {"name": "半导体/芯片", "net_inflow": 0.0, "change_percent": 0.0, "heat": "中", "hint": "关注政策、国产替代和估值位置。"},
        {"name": "消费/白酒", "net_inflow": 0.0, "change_percent": 0.0, "heat": "中", "hint": "关注消费修复持续性，避免短线追高。"},
        {"name": "医药/创新药", "net_inflow": 0.0, "change_percent": 0.0, "heat": "中", "hint": "关注政策变化和行业景气度。"},
        {"name": "红利/央企", "net_inflow": 0.0, "change_percent": 0.0, "heat": "中", "hint": "适合观察稳健风格资金是否延续。"},
    ]


def _load_public_flows(limit: int) -> list[dict[str, Any]]:
    session = requests.Session()
    session.trust_env = False
    response = session.get(
        "https://push2.eastmoney.com/api/qt/clist/get",
        params={
            "pn": "1",
            "pz": str(max(limit, 20)),
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f62",
            "fs": "m:90 t:2",
            "fields": "f12,f14,f2,f3,f62,f184",
        },
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
        timeout=10,
    )
    response.raise_for_status()
    raw_rows = response.json().get("data", {}).get("diff", []) or []
    flows: list[dict[str, Any]] = []
    for row in raw_rows[:limit]:
        name = str(row.get("f14") or "")
        if not name:
            continue
        net = _to_float(row.get("f62"))
        pct = _to_float(row.get("f3"))
        heat = "高" if abs(net) >= 1000000000 else "中" if abs(net) >= 300000000 else "低"
        flows.append(
            {
                "name": name,
                "net_inflow": net,
                "change_percent": pct,
                "heat": heat,
                "hint": "来自公开行业资金流，数值口径以上游数据源为准。",
            }
        )
    return flows


def get_smart_money_signals(limit: int = 10, refresh: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    flows: list[dict[str, Any]] = []
    try:
        flows = _load_public_flows(limit)
    except Exception as exc:
        errors.append(f"行业资金流暂不可用：{exc}")
    if not flows:
        flows = _fallback_flows()[:limit]

    try:
        news_payload = rich_news_data.get_market_news(limit=30, refresh=refresh)
        news = news_payload.get("news", [])
    except Exception as exc:
        errors.append(f"行业动态资讯暂不可用：{exc}")
        news = []

    dynamics = []
    for item in news:
        tags = f"{item.get('positive_types', '')},{item.get('impact_direction', '')}"
        if any(key in tags for key in ["科技", "人工智能", "半导体", "新能源", "消费", "医药", "红利", "债券", "QDII"]):
            dynamics.append(
                {
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "published_at": item.get("published_at"),
                    "direction": item.get("impact_direction"),
                    "plain_explanation": item.get("plain_explanation"),
                    "original_url": item.get("original_url"),
                }
            )
        if len(dynamics) >= limit:
            break

    return {
        "flows": flows[:limit],
        "dynamics": dynamics[:limit],
        "errors": errors,
        "updated_at": _now(),
        "disclaimer": "资金流和行业动态仅作为模拟研究证据，不构成投资建议。",
    }


def signals_for_fund(fund: dict[str, Any], signals: dict[str, Any]) -> list[str]:
    text = " ".join([str(fund.get("name", "")), str(fund.get("fund_type", "")), str(fund.get("industries", ""))])
    hits: list[str] = []
    for flow in signals.get("flows", []):
        name = str(flow.get("name") or "")
        if name and any(part and part in text for part in name.replace("/", ",").split(",")):
            hits.append(f"{name} 资金流热度{flow.get('heat')}，涨跌幅{flow.get('change_percent', 0)}%")
    for item in signals.get("dynamics", []):
        direction = str(item.get("direction") or "")
        if direction and any(key in text for key in direction.replace("/", ",").split(",")):
            hits.append(f"资讯方向匹配：{direction}")
    return hits[:3]
