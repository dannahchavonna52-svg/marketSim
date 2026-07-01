from __future__ import annotations

import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "data_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TTL = 60 * 10
HISTORY_TTL = 60 * 60 * 6

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/",
}

SAMPLE_FUNDS: list[dict[str, Any]] = [
    {
        "symbol": "000001",
        "name": "华夏成长混合",
        "fund_type": "混合型",
        "manager": "资料待补全",
        "company": "华夏基金",
        "latest_nav": 1.238,
        "estimated_nav": 1.241,
        "daily_change": 0.42,
        "week_return": 1.8,
        "month_return": 3.6,
        "three_month_return": 6.2,
        "six_month_return": 8.5,
        "year_return": 12.6,
        "three_year_return": 25.2,
        "max_drawdown": -16.5,
        "sharpe_ratio": 0.82,
        "fund_size": 58.4,
        "inception_date": "2001-12-18",
        "industries": "消费,科技,医药",
        "top_stocks": "资料待补全",
        "fee": "以销售平台展示为准",
        "risk_level": "中高",
        "peer_rank": "资料待补全",
        "data_source": "本地兜底样例",
    },
    {
        "symbol": "110022",
        "name": "易方达消费行业股票",
        "fund_type": "股票型",
        "manager": "资料待补全",
        "company": "易方达基金",
        "latest_nav": 3.118,
        "estimated_nav": 3.126,
        "daily_change": 0.76,
        "week_return": 2.1,
        "month_return": 4.2,
        "three_month_return": 5.7,
        "six_month_return": 7.3,
        "year_return": 10.8,
        "three_year_return": 18.4,
        "max_drawdown": -22.3,
        "sharpe_ratio": 0.66,
        "fund_size": 181.7,
        "inception_date": "2010-08-20",
        "industries": "消费,食品饮料,家电,零售",
        "top_stocks": "资料待补全",
        "fee": "以销售平台展示为准",
        "risk_level": "高",
        "peer_rank": "资料待补全",
        "data_source": "本地兜底样例",
    },
    {
        "symbol": "161725",
        "name": "招商中证白酒指数",
        "fund_type": "指数型",
        "manager": "资料待补全",
        "company": "招商基金",
        "latest_nav": 0.912,
        "estimated_nav": 0.918,
        "daily_change": 0.33,
        "week_return": 1.1,
        "month_return": 2.5,
        "three_month_return": -1.2,
        "six_month_return": -4.7,
        "year_return": -9.8,
        "three_year_return": -28.0,
        "max_drawdown": -42.0,
        "sharpe_ratio": 0.28,
        "fund_size": 302.3,
        "inception_date": "2015-05-27",
        "industries": "白酒,食品饮料,消费",
        "top_stocks": "资料待补全",
        "fee": "以销售平台展示为准",
        "risk_level": "高",
        "peer_rank": "资料待补全",
        "data_source": "本地兜底样例",
    },
    {
        "symbol": "005827",
        "name": "易方达蓝筹精选混合",
        "fund_type": "混合型",
        "manager": "资料待补全",
        "company": "易方达基金",
        "latest_nav": 2.021,
        "estimated_nav": 2.018,
        "daily_change": -0.16,
        "week_return": 0.6,
        "month_return": 2.0,
        "three_month_return": 4.8,
        "six_month_return": 6.4,
        "year_return": 9.2,
        "three_year_return": 16.5,
        "max_drawdown": -20.1,
        "sharpe_ratio": 0.72,
        "fund_size": 421.6,
        "inception_date": "2018-09-05",
        "industries": "消费,互联网,医药,港股",
        "top_stocks": "资料待补全",
        "fee": "以销售平台展示为准",
        "risk_level": "中高",
        "peer_rank": "资料待补全",
        "data_source": "本地兜底样例",
    },
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_code(value: Any) -> str:
    text = re.sub(r"\D", "", str(value or ""))
    return text[:6]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).replace("%", "").replace(",", "").strip()
        if text in {"", "-", "--", "None", "nan", "null"}:
            return default
        return float(text)
    except Exception:
        return default


def _cache_path(key: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", key)
    return CACHE_DIR / f"{safe}.json"


def _read_cache(key: str, ttl: int, allow_stale: bool = True) -> tuple[Any | None, bool]:
    path = _cache_path(key)
    if not path.exists():
        return None, False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        is_stale = time.time() - float(payload.get("cached_at_ts", 0)) > ttl
        if is_stale and not allow_stale:
            return None, False
        data = payload.get("data")
        if isinstance(data, dict):
            data.setdefault("cache", {})
            data["cache"].update(
                {
                    "hit": True,
                    "stale": is_stale,
                    "cached_at": payload.get("cached_at"),
                }
            )
        return data, is_stale
    except Exception:
        return None, False


def _write_cache(key: str, data: Any) -> Any:
    payload = {"cached_at_ts": time.time(), "cached_at": _now(), "data": data}
    _cache_path(key).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _request_text(url: str, params: dict[str, Any] | None = None, timeout: int = 10) -> str:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def _request_json(url: str, params: dict[str, Any] | None = None, timeout: int = 10) -> Any:
    text = _request_text(url, params=params, timeout=timeout).strip()
    if "(" in text and text.rfind(")") > text.find("("):
        text = text[text.find("(") + 1 : text.rfind(")")]
    return json.loads(text)


def _regex_json(text: str, name: str) -> Any:
    match = re.search(rf"{re.escape(name)}\s*=\s*(.*?);", text, flags=re.S)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


def _regex_string(text: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*=\s*['\"](.*?)['\"]", text, flags=re.S)
    return match.group(1).strip() if match else ""


def _infer_type(name: str) -> str:
    if any(key in name for key in ["货币", "现金"]):
        return "货币型"
    if "债" in name:
        return "债券型"
    if any(key in name for key in ["指数", "ETF", "联接", "中证", "沪深", "创业板"]):
        return "指数型"
    if "股票" in name:
        return "股票型"
    if "混合" in name:
        return "混合型"
    return "公募基金"


def _infer_industries(name: str) -> str:
    mapping = [
        ("白酒", "白酒,食品饮料,消费"),
        ("消费", "消费,食品饮料,零售"),
        ("新能源", "新能源,电池,光伏,汽车"),
        ("光伏", "新能源,光伏"),
        ("医药", "医药,医疗服务,创新药"),
        ("医疗", "医药,医疗服务"),
        ("半导体", "半导体,芯片,科技"),
        ("芯片", "半导体,芯片,科技"),
        ("人工智能", "人工智能,科技,算力"),
        ("科技", "科技,软件,硬件"),
        ("互联网", "互联网,港股,科技"),
        ("军工", "军工,高端制造"),
        ("红利", "红利,价值,央企"),
        ("银行", "银行,金融"),
        ("证券", "证券,金融"),
        ("黄金", "黄金,资源"),
    ]
    for key, value in mapping:
        if key in name:
            return value
    return "资料待补全"


def _normalize_fund(raw: dict[str, Any]) -> dict[str, Any]:
    symbol = _clean_code(raw.get("symbol") or raw.get("code") or raw.get("FCODE"))
    name = str(raw.get("name") or raw.get("SHORTNAME") or raw.get("NAME") or symbol).strip()
    latest = _to_float(raw.get("latest_nav") or raw.get("DWJZ") or raw.get("NAV"))
    estimated = _to_float(raw.get("estimated_nav") or raw.get("GSZ"), latest)
    return {
        "symbol": symbol,
        "name": name,
        "fund_type": str(raw.get("fund_type") or raw.get("FTYPE") or _infer_type(name)),
        "manager": str(raw.get("manager") or raw.get("JJJL") or "资料待补全"),
        "company": str(raw.get("company") or raw.get("JJGS") or "资料待补全"),
        "latest_nav": latest,
        "estimated_nav": estimated,
        "daily_change": _to_float(raw.get("daily_change") or raw.get("RZDF") or raw.get("GSZZL")),
        "week_return": _to_float(raw.get("week_return")),
        "month_return": _to_float(raw.get("month_return")),
        "three_month_return": _to_float(raw.get("three_month_return")),
        "six_month_return": _to_float(raw.get("six_month_return")),
        "year_return": _to_float(raw.get("year_return")),
        "three_year_return": _to_float(raw.get("three_year_return")),
        "max_drawdown": _to_float(raw.get("max_drawdown")),
        "sharpe_ratio": _to_float(raw.get("sharpe_ratio")),
        "fund_size": _to_float(raw.get("fund_size")),
        "inception_date": str(raw.get("inception_date") or "资料待补全"),
        "industries": str(raw.get("industries") or _infer_industries(name)),
        "top_stocks": str(raw.get("top_stocks") or "资料待补全"),
        "fee": str(raw.get("fee") or "以销售平台展示为准"),
        "risk_level": str(raw.get("risk_level") or "资料待补全"),
        "peer_rank": str(raw.get("peer_rank") or "资料待补全"),
        "data_source": str(raw.get("data_source") or "公开数据"),
        "updated_at": str(raw.get("updated_at") or _now()),
    }


def _sample_history(base: float = 1.0, limit: int = 60) -> list[dict[str, Any]]:
    rows = []
    for idx in range(limit):
        swing = math.sin(idx / 5) * 0.018 + (idx - limit / 2) * 0.0008
        nav = round(max(0.1, base * (1 + swing)), 4)
        rows.append({"date": f"样例{idx + 1}", "nav": nav, "change_percent": round(math.sin(idx / 4) * 0.8, 2)})
    return rows


def _history_metrics(history: list[dict[str, Any]]) -> dict[str, float]:
    navs = [_to_float(item.get("nav")) for item in history if _to_float(item.get("nav")) > 0]
    changes = [_to_float(item.get("change_percent")) for item in history]
    if len(navs) < 2:
        return {}

    def ret(days: int) -> float:
        if len(navs) <= days:
            return 0.0
        return round((navs[-1] / navs[-days - 1] - 1) * 100, 2)

    peak = navs[0]
    max_drawdown = 0.0
    for nav in navs:
        peak = max(peak, nav)
        max_drawdown = min(max_drawdown, (nav / peak - 1) * 100)
    vol = pstdev(changes) if len(changes) > 2 else 0.0
    sharpe = round((mean(changes) / vol) * math.sqrt(252), 2) if vol else 0.0
    return {
        "week_return": ret(5),
        "month_return": ret(21),
        "three_month_return": ret(63),
        "six_month_return": ret(126),
        "year_return": ret(252),
        "three_year_return": ret(756),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": sharpe,
    }


def _search_eastmoney(keyword: str) -> list[dict[str, Any]]:
    if not keyword:
        return []
    payload = _request_json(
        "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx",
        {"m": "1", "key": keyword},
    )
    rows = payload.get("Datas") or payload.get("Data") or payload.get("datas") or []
    funds = []
    for row in rows[:80]:
        if isinstance(row, str):
            parts = row.split("|")
            raw = {"symbol": parts[0] if parts else "", "name": parts[2] if len(parts) > 2 else ""}
        else:
            raw = {
                "symbol": row.get("CODE") or row.get("FCODE") or row.get("code"),
                "name": row.get("NAME") or row.get("SHORTNAME") or row.get("name"),
                "fund_type": row.get("FundBaseType") or row.get("FTYPE"),
                "data_source": "东方财富公开搜索",
            }
        fund = _normalize_fund(raw)
        if fund["symbol"]:
            funds.append(fund)
    return funds


def _rank_eastmoney(limit: int = 80) -> list[dict[str, Any]]:
    today = datetime.now().strftime("%Y-%m-%d")
    text = _request_text(
        "https://fund.eastmoney.com/data/rankhandler.aspx",
        {
            "op": "ph",
            "dt": "kf",
            "ft": "all",
            "rs": "",
            "gs": "0",
            "sc": "1nzf",
            "st": "desc",
            "sd": "2024-01-01",
            "ed": today,
            "qdii": "",
            "tabSubtype": ",,,,,",
            "pi": "1",
            "pn": str(limit),
            "dx": "1",
            "v": str(int(time.time() * 1000)),
        },
    )
    match = re.search(r"datas:\[(.*?)\],allRecords", text, flags=re.S)
    if not match:
        return []
    rows = re.findall(r'"(.*?)"', match.group(1), flags=re.S)
    funds = []
    for row in rows:
        parts = row.split(",")
        if len(parts) < 7:
            continue
        raw = {
            "symbol": parts[0],
            "name": parts[1],
            "fund_type": _infer_type(parts[1]),
            "latest_nav": parts[3] if len(parts) > 3 else 0,
            "daily_change": parts[6] if len(parts) > 6 else 0,
            "week_return": parts[7] if len(parts) > 7 else 0,
            "month_return": parts[8] if len(parts) > 8 else 0,
            "three_month_return": parts[9] if len(parts) > 9 else 0,
            "six_month_return": parts[10] if len(parts) > 10 else 0,
            "year_return": parts[11] if len(parts) > 11 else 0,
            "three_year_return": parts[13] if len(parts) > 13 else 0,
            "data_source": "东方财富公开排行",
        }
        fund = _normalize_fund(raw)
        if fund["symbol"]:
            funds.append(fund)
    return funds


def _fund_realtime(symbol: str) -> dict[str, Any]:
    text = _request_text(f"https://fundgz.1234567.com.cn/js/{symbol}.js", {"rt": int(time.time() * 1000)}, timeout=6)
    match = re.search(r"jsonpgz\((.*)\)", text)
    if not match:
        return {}
    payload = json.loads(match.group(1))
    return {
        "symbol": payload.get("fundcode"),
        "name": payload.get("name"),
        "latest_nav": _to_float(payload.get("dwjz")),
        "estimated_nav": _to_float(payload.get("gsz")),
        "daily_change": _to_float(payload.get("gszzl")),
        "updated_at": payload.get("gztime") or _now(),
        "data_source": "天天基金公开估值",
    }


def _fund_page_data(symbol: str) -> dict[str, Any]:
    text = _request_text(f"https://fund.eastmoney.com/pingzhongdata/{symbol}.js", {"v": int(time.time() * 1000)}, timeout=10)
    data: dict[str, Any] = {}
    name = _regex_string(text, "fS_name")
    if name:
        data["name"] = name
    code = _regex_string(text, "fS_code")
    if code:
        data["symbol"] = code
    managers = _regex_json(text, "Data_currentFundManager") or []
    if managers:
        manager_names = [item.get("name") for item in managers if isinstance(item, dict) and item.get("name")]
        if manager_names:
            data["manager"] = "、".join(manager_names)
    performance = _regex_json(text, "Data_performanceEvaluation") or {}
    if isinstance(performance, dict):
        data["peer_rank"] = str(performance.get("avr") or performance.get("score") or "资料待补全")
    net_worth = _regex_json(text, "Data_netWorthTrend") or []
    history = []
    for row in net_worth[-760:]:
        if not isinstance(row, dict):
            continue
        timestamp = row.get("x")
        date_text = ""
        if timestamp:
            try:
                date_text = datetime.fromtimestamp(int(timestamp) / 1000).strftime("%Y-%m-%d")
            except Exception:
                date_text = ""
        history.append({"date": date_text, "nav": _to_float(row.get("y")), "change_percent": _to_float(row.get("equityReturn"))})
    if history:
        data["history"] = history
    size_match = re.search(r"基金规模[：:]\s*([\d.]+)\s*亿元", text)
    if size_match:
        data["fund_size"] = _to_float(size_match.group(1))
    return data


def _history_from_eastmoney(symbol: str, page_size: int = 760) -> list[dict[str, Any]]:
    payload = _request_json(
        "https://api.fund.eastmoney.com/f10/lsjz",
        {"fundCode": symbol, "pageIndex": 1, "pageSize": page_size},
    )
    rows = payload.get("Data", {}).get("LSJZList", [])
    history = []
    for row in reversed(rows):
        history.append(
            {
                "date": row.get("FSRQ", ""),
                "nav": _to_float(row.get("DWJZ")),
                "change_percent": _to_float(row.get("JZZZL")),
            }
        )
    return [item for item in history if item["nav"] > 0]


def _quick_nav(symbol: str) -> dict[str, Any]:
    history = _history_from_eastmoney(symbol, page_size=2)
    if not history:
        return {}
    latest = history[-1]
    return {
        "latest_nav": latest.get("nav"),
        "estimated_nav": latest.get("nav"),
        "daily_change": latest.get("change_percent"),
        "updated_at": latest.get("date") or _now(),
        "data_source": "东方财富历史净值",
    }


def search_funds(keyword: str = "", refresh: bool = False) -> dict[str, Any]:
    keyword = str(keyword or "").strip()
    key = f"fund_search_{keyword or 'rank'}"
    if not refresh:
        cached, is_stale = _read_cache(key, DEFAULT_TTL, allow_stale=False)
        if cached is not None and not is_stale:
            return cached

    errors: list[str] = []
    funds: list[dict[str, Any]] = []
    try:
        funds = _search_eastmoney(keyword) if keyword else _rank_eastmoney(80)
    except Exception as exc:
        errors.append(f"东方财富基金数据暂不可用：{exc}")
    if keyword and not funds:
        try:
            funds = _rank_eastmoney(120)
            low = keyword.lower()
            funds = [item for item in funds if keyword in item["symbol"] or low in item["name"].lower()]
        except Exception as exc:
            errors.append(f"基金排行补充搜索失败：{exc}")

    if not funds:
        funds = [
            item.copy()
            for item in SAMPLE_FUNDS
            if not keyword or keyword in item["symbol"] or keyword.lower() in item["name"].lower()
        ]

    need_nav = [fund for fund in funds[:20] if not _to_float(fund.get("latest_nav"))]
    if need_nav:
        by_symbol = {fund["symbol"]: fund for fund in need_nav}

        def enrich_nav(symbol: str) -> tuple[str, dict[str, Any]]:
            try:
                realtime = _fund_realtime(symbol)
                if _to_float(realtime.get("latest_nav")):
                    return symbol, realtime
            except Exception:
                pass
            try:
                return symbol, _quick_nav(symbol)
            except Exception:
                return symbol, {}

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(enrich_nav, fund["symbol"]) for fund in need_nav]
            for future in as_completed(futures):
                symbol, payload = future.result()
                if payload:
                    by_symbol[symbol].update({k: v for k, v in payload.items() if v not in ("", None, 0)})

    result = {
        "funds": funds[:80],
        "errors": errors,
        "updated_at": _now(),
        "source": "东方财富/天天基金公开数据",
        "cache": {"hit": False, "stale": False, "cached_at": ""},
    }
    return _write_cache(key, result)


def get_fund_detail(symbol: str, refresh: bool = False) -> dict[str, Any]:
    symbol = _clean_code(symbol)
    key = f"fund_detail_{symbol}"
    if not refresh:
        cached, _ = _read_cache(key, HISTORY_TTL, allow_stale=True)
        if cached is not None:
            return cached

    errors: list[str] = []
    fund = next((item.copy() for item in SAMPLE_FUNDS if item["symbol"] == symbol), None)
    if not fund:
        search_result = search_funds(symbol)
        fund = next((item.copy() for item in search_result.get("funds", []) if item["symbol"] == symbol), None)
        errors.extend(search_result.get("errors", []))
    if not fund:
        fund = _normalize_fund({"symbol": symbol, "name": f"{symbol} 基金", "data_source": "代码占位"})

    history: list[dict[str, Any]] = []
    try:
        page_data = _fund_page_data(symbol)
        fund.update({k: v for k, v in page_data.items() if k != "history" and v not in ("", None, 0)})
        history = page_data.get("history") or []
    except Exception as exc:
        errors.append(f"基金详情页数据暂不可用：{exc}")
    if not history:
        try:
            history = _history_from_eastmoney(symbol)
        except Exception as exc:
            errors.append(f"历史净值暂不可用：{exc}")
    try:
        realtime = _fund_realtime(symbol)
        fund.update({k: v for k, v in realtime.items() if v not in ("", None, 0)})
    except Exception as exc:
        errors.append(f"估算净值暂不可用：{exc}")

    if not history:
        history = _sample_history(_to_float(fund.get("latest_nav"), 1.0), 90)
    metrics = _history_metrics(history)
    fund.update(metrics)
    if history:
        latest = history[-1]
        fund["latest_nav"] = _to_float(fund.get("latest_nav")) or latest.get("nav")
        fund["daily_change"] = _to_float(fund.get("daily_change")) or latest.get("change_percent")
    fund["history"] = history[-360:]
    fund["updated_at"] = _now()
    fund["data_source"] = fund.get("data_source") or "东方财富/天天基金公开数据"

    result = {
        "fund": fund,
        "errors": list(dict.fromkeys(errors)),
        "updated_at": _now(),
        "source": "东方财富/天天基金公开数据",
        "cache": {"hit": False, "stale": False, "cached_at": ""},
    }
    return _write_cache(key, result)


def get_fund_trend(symbol: str, limit: int = 45, refresh: bool = False) -> dict[str, Any]:
    symbol = _clean_code(symbol)
    key = f"fund_trend_{symbol}_{limit}"
    if not refresh:
        cached, _ = _read_cache(key, HISTORY_TTL, allow_stale=True)
        if cached is not None:
            return cached

    errors: list[str] = []
    history: list[dict[str, Any]] = []
    try:
        history = _history_from_eastmoney(symbol, page_size=max(limit, 90))[-limit:]
    except Exception as exc:
        errors.append(f"净值走势暂不可用：{exc}")
    if not history:
        detail = get_fund_detail(symbol)
        history = (detail.get("fund", {}).get("history") or [])[-limit:]
    if not history:
        history = _sample_history(1.0, limit)

    latest = history[-1] if history else {}
    result = {
        "history": history,
        "latest_nav": latest.get("nav"),
        "daily_change": latest.get("change_percent"),
        "errors": errors,
        "updated_at": _now(),
        "cache": {"hit": False, "stale": False, "cached_at": ""},
    }
    return _write_cache(key, result)


def recommendation_pool(refresh: bool = False) -> dict[str, Any]:
    result = search_funds("", refresh=refresh)
    return result


def data_status() -> dict[str, Any]:
    cache_files = list(CACHE_DIR.glob("*.json"))
    return {
        "sources": [
            {"name": "东方财富基金搜索", "status": "enabled"},
            {"name": "东方财富历史净值", "status": "enabled"},
            {"name": "天天基金估算净值", "status": "enabled"},
        ],
        "cache_files": len(cache_files),
        "cache_dir": str(CACHE_DIR),
        "updated_at": _now(),
    }
