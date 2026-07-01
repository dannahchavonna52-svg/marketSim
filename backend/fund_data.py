from datetime import datetime
from typing import Any, Dict, List


SAMPLE_FUNDS = [
    {
        "symbol": "000001",
        "name": "华夏成长混合",
        "fund_type": "混合型",
        "manager": "暂无数据",
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
        "top_stocks": "贵州茅台,宁德时代,迈瑞医疗",
        "fee": "申购费以平台展示为准",
        "risk_level": "中高",
        "peer_rank": "同类前 35%",
        "data_source": "本地示例/公开数据兜底",
    },
    {
        "symbol": "110022",
        "name": "易方达消费行业股票",
        "fund_type": "股票型",
        "manager": "暂无数据",
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
        "industries": "食品饮料,家电,零售",
        "top_stocks": "贵州茅台,五粮液,美的集团",
        "fee": "申购费以平台展示为准",
        "risk_level": "高",
        "peer_rank": "同类前 40%",
        "data_source": "本地示例/公开数据兜底",
    },
    {
        "symbol": "161725",
        "name": "招商中证白酒指数",
        "fund_type": "指数型",
        "manager": "暂无数据",
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
        "industries": "白酒,食品饮料",
        "top_stocks": "贵州茅台,五粮液,泸州老窖",
        "fee": "申购费以平台展示为准",
        "risk_level": "高",
        "peer_rank": "同类后 45%",
        "data_source": "本地示例/公开数据兜底",
    },
    {
        "symbol": "005827",
        "name": "易方达蓝筹精选混合",
        "fund_type": "混合型",
        "manager": "暂无数据",
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
        "industries": "消费,互联网,医药",
        "top_stocks": "腾讯控股,贵州茅台,药明生物",
        "fee": "申购费以平台展示为准",
        "risk_level": "中高",
        "peer_rank": "同类前 45%",
        "data_source": "本地示例/公开数据兜底",
    },
]


def _load_akshare():
    try:
        import akshare as ak

        return ak, None
    except Exception as exc:
        return None, f"AKShare 不可用：{exc}"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).replace("%", "").replace(",", "").strip()
        if text in {"", "-", "--", "nan", "None"}:
            return default
        return float(text)
    except Exception:
        return default


def _sample_history(base: float) -> List[Dict[str, Any]]:
    rows = []
    for i in range(30):
        nav = round(base * (1 + (i - 15) * 0.002), 4)
        rows.append({"date": f"近{i + 1}日", "nav": nav, "change_percent": round((i % 7 - 3) * 0.18, 2)})
    return rows


def search_funds(keyword: str = "") -> Dict[str, Any]:
    keyword = str(keyword or "").strip()
    errors = []
    funds = []
    ak, error = _load_akshare()
    if ak:
        try:
            df = ak.fund_open_fund_daily_em()
            if df is not None and not df.empty:
                code_col = "基金代码"
                name_col = "基金简称"
                filtered = df
                if keyword:
                    filtered = df[
                        df[code_col].astype(str).str.contains(keyword, case=False, na=False)
                        | df[name_col].astype(str).str.contains(keyword, case=False, na=False)
                    ]
                for _, row in filtered.head(30).iterrows():
                    funds.append(
                        {
                            "symbol": str(row.get(code_col, "")).strip(),
                            "name": str(row.get(name_col, "")).strip(),
                            "fund_type": "公募基金",
                            "manager": "暂无数据",
                            "company": "暂无数据",
                            "latest_nav": _to_float(row.get("单位净值")),
                            "estimated_nav": _to_float(row.get("估算净值")),
                            "daily_change": _to_float(row.get("日增长率")),
                            "week_return": 0.0,
                            "month_return": 0.0,
                            "three_month_return": 0.0,
                            "six_month_return": 0.0,
                            "year_return": 0.0,
                            "three_year_return": 0.0,
                            "max_drawdown": 0.0,
                            "sharpe_ratio": 0.0,
                            "fund_size": 0.0,
                            "inception_date": "暂无数据",
                            "industries": "暂无数据",
                            "top_stocks": "暂无数据",
                            "fee": "以销售平台展示为准",
                            "risk_level": "暂无数据",
                            "peer_rank": "暂无数据",
                            "data_source": "AKShare/东方财富公开数据",
                        }
                    )
        except Exception as exc:
            errors.append(f"公开基金列表获取失败：{exc}")
    elif error:
        errors.append(error)

    if not funds:
        funds = [
            fund
            for fund in SAMPLE_FUNDS
            if not keyword or keyword in fund["symbol"] or keyword.lower() in fund["name"].lower()
        ]

    return {"funds": funds, "errors": errors, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def get_fund_detail(symbol: str) -> Dict[str, Any]:
    symbol = str(symbol).strip()
    fund = next((item.copy() for item in SAMPLE_FUNDS if item["symbol"] == symbol), None)
    errors = []
    ak, error = _load_akshare()
    history = []

    if ak:
        try:
            hist = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
            if hist is not None and not hist.empty:
                recent = hist.tail(120)
                history = [
                    {
                        "date": str(row.get("净值日期", "")),
                        "nav": _to_float(row.get("单位净值")),
                        "change_percent": _to_float(row.get("日增长率")),
                    }
                    for _, row in recent.iterrows()
                ]
                latest = history[-1] if history else {}
                if not fund:
                    fund = {
                        "symbol": symbol,
                        "name": symbol,
                        "fund_type": "公募基金",
                        "manager": "暂无数据",
                        "company": "暂无数据",
                        "latest_nav": latest.get("nav", 0.0),
                        "estimated_nav": latest.get("nav", 0.0),
                        "daily_change": latest.get("change_percent", 0.0),
                        "week_return": 0.0,
                        "month_return": 0.0,
                        "three_month_return": 0.0,
                        "six_month_return": 0.0,
                        "year_return": 0.0,
                        "three_year_return": 0.0,
                        "max_drawdown": 0.0,
                        "sharpe_ratio": 0.0,
                        "fund_size": 0.0,
                        "inception_date": "暂无数据",
                        "industries": "暂无数据",
                        "top_stocks": "暂无数据",
                        "fee": "以销售平台展示为准",
                        "risk_level": "暂无数据",
                        "peer_rank": "暂无数据",
                        "data_source": "AKShare/东方财富公开数据",
                    }
                else:
                    fund["latest_nav"] = latest.get("nav", fund["latest_nav"])
                    fund["daily_change"] = latest.get("change_percent", fund["daily_change"])
        except Exception as exc:
            errors.append(f"基金净值走势获取失败：{exc}")
    elif error:
        errors.append(error)

    if not fund:
        fund = SAMPLE_FUNDS[0].copy()
        fund["symbol"] = symbol
        fund["name"] = f"{symbol} 基金"
    if not history:
        history = _sample_history(fund.get("latest_nav") or 1.0)

    fund["history"] = history
    fund["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"fund": fund, "errors": errors}


# ---------------------------------------------------------------------------
# UTF-8 fund data implementation, appended to override the early prototype
# above.  It uses legal public data sources only: AKShare wrappers first,
# Eastmoney public JSON/JS endpoints second, and local examples last.
# ---------------------------------------------------------------------------
import json
import math
import re
import time
from functools import lru_cache

import pandas as pd
import requests


SAMPLE_FUNDS = [
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
        "top_stocks": "贵州茅台,宁德时代,迈瑞医疗",
        "fee": "以销售平台展示为准",
        "risk_level": "中高",
        "peer_rank": "同类前35%",
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
        "industries": "食品饮料,家电,零售",
        "top_stocks": "贵州茅台,五粮液,美的集团",
        "fee": "以销售平台展示为准",
        "risk_level": "高",
        "peer_rank": "同类前40%",
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
        "industries": "白酒,食品饮料",
        "top_stocks": "贵州茅台,五粮液,泸州老窖",
        "fee": "以销售平台展示为准",
        "risk_level": "高",
        "peer_rank": "同类后45%",
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
        "industries": "消费,互联网,医药",
        "top_stocks": "腾讯控股,贵州茅台,药明生物",
        "fee": "以销售平台展示为准",
        "risk_level": "中高",
        "peer_rank": "同类前45%",
        "data_source": "本地兜底样例",
    },
]


_CACHE: Dict[str, Any] = {}
_CACHE_TS: Dict[str, float] = {}
_TTL = 300


def _cache_get(key: str):
    if key in _CACHE and time.time() - _CACHE_TS.get(key, 0) < _TTL:
        return _CACHE[key]
    return None


def _cache_set(key: str, value: Any):
    _CACHE[key] = value
    _CACHE_TS[key] = time.time()
    return value


def _request_json(url: str, params: Dict[str, Any] | None = None) -> Any:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://fund.eastmoney.com/",
    }
    session = requests.Session()
    session.trust_env = False
    resp = session.get(url, params=params, headers=headers, timeout=8)
    resp.raise_for_status()
    text = resp.text.strip()
    if text.startswith(("jQuery", "callback")):
        text = text[text.find("(") + 1 : text.rfind(")")]
    return json.loads(text)


def _clean_code(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))[:6]


def _pick(row: Any, names: List[str], default: Any = "") -> Any:
    if row is None:
        return default
    for name in names:
        try:
            value = row.get(name)
        except Exception:
            value = None
        if value not in (None, "", "-", "--", "nan"):
            return value
    return default


def _history_metrics(history: List[Dict[str, Any]]) -> Dict[str, float]:
    if not history:
        return {}
    navs = [float(item["nav"]) for item in history if _to_float(item.get("nav")) > 0]
    changes = [float(item.get("change_percent") or 0) for item in history]
    if not navs:
        return {}

    def ret(days: int) -> float:
        if len(navs) <= days:
            return 0.0
        return round((navs[-1] / navs[-days - 1] - 1) * 100, 2)

    peak = navs[0]
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        max_dd = min(max_dd, (nav / peak - 1) * 100)
    volatility = pd.Series(changes).std() if len(changes) > 3 else 0
    avg = pd.Series(changes).mean() if changes else 0
    sharpe = round((avg / volatility) * math.sqrt(252), 2) if volatility else 0
    return {
        "week_return": ret(5),
        "month_return": ret(21),
        "three_month_return": ret(63),
        "six_month_return": ret(126),
        "year_return": ret(252),
        "three_year_return": ret(756),
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": sharpe,
    }


def _normalize_fund(raw: Dict[str, Any]) -> Dict[str, Any]:
    symbol = _clean_code(raw.get("symbol") or raw.get("code") or raw.get("基金代码") or raw.get("FCODE"))
    name = str(raw.get("name") or raw.get("基金简称") or raw.get("SHORTNAME") or raw.get("NAME") or symbol)
    return {
        "symbol": symbol,
        "name": name,
        "fund_type": str(raw.get("fund_type") or raw.get("基金类型") or raw.get("FTYPE") or "公募基金"),
        "manager": str(raw.get("manager") or raw.get("基金经理") or raw.get("JJJL") or "资料待补全"),
        "company": str(raw.get("company") or raw.get("基金公司") or raw.get("JJGS") or "资料待补全"),
        "latest_nav": _to_float(raw.get("latest_nav") or raw.get("单位净值") or raw.get("DWJZ") or raw.get("NAV")),
        "estimated_nav": _to_float(raw.get("estimated_nav") or raw.get("估算净值") or raw.get("GSZ")),
        "daily_change": _to_float(raw.get("daily_change") or raw.get("日增长率") or raw.get("RZDF") or raw.get("GSZZL")),
        "week_return": _to_float(raw.get("week_return") or raw.get("近1周")),
        "month_return": _to_float(raw.get("month_return") or raw.get("近1月")),
        "three_month_return": _to_float(raw.get("three_month_return") or raw.get("近3月")),
        "six_month_return": _to_float(raw.get("six_month_return") or raw.get("近6月")),
        "year_return": _to_float(raw.get("year_return") or raw.get("近1年") or raw.get("今年来")),
        "three_year_return": _to_float(raw.get("three_year_return") or raw.get("近3年")),
        "max_drawdown": _to_float(raw.get("max_drawdown") or raw.get("最大回撤")),
        "sharpe_ratio": _to_float(raw.get("sharpe_ratio") or raw.get("夏普比率")),
        "fund_size": _to_float(raw.get("fund_size") or raw.get("基金规模") or raw.get("规模")),
        "inception_date": str(raw.get("inception_date") or raw.get("成立时间") or raw.get("成立日期") or "暂无数据"),
        "industries": str(raw.get("industries") or "暂无数据"),
        "top_stocks": str(raw.get("top_stocks") or "暂无数据"),
        "fee": str(raw.get("fee") or "以销售平台展示为准"),
        "risk_level": str(raw.get("risk_level") or "资料待补全"),
        "peer_rank": str(raw.get("peer_rank") or raw.get("同类排名") or "暂无数据"),
        "data_source": str(raw.get("data_source") or "公开数据"),
    }


@lru_cache(maxsize=1)
def _ak_daily_map() -> Dict[str, Dict[str, Any]]:
    ak, error = _load_akshare()
    if not ak:
        raise RuntimeError(error)
    df = ak.fund_open_fund_daily_em()
    result = {}
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            code = _clean_code(_pick(row, ["基金代码"]))
            if code:
                result[code] = {
                    "symbol": code,
                    "name": _pick(row, ["基金简称"]),
                    "fund_type": "公募基金",
                    "latest_nav": _to_float(_pick(row, ["单位净值"])),
                    "estimated_nav": _to_float(_pick(row, ["估算净值"])),
                    "daily_change": _to_float(_pick(row, ["日增长率"])),
                    "data_source": "AKShare/东方财富公开基金列表",
                }
    return result


def _search_eastmoney(keyword: str) -> List[Dict[str, Any]]:
    if not keyword:
        return []
    payload = _request_json(
        "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx",
        {"m": "1", "key": keyword},
    )
    rows = payload.get("Datas") or payload.get("datas") or payload.get("Data") or []
    funds = []
    for row in rows[:50]:
        if isinstance(row, str):
            parts = row.split("|")
            row = {"code": parts[0] if parts else "", "name": parts[2] if len(parts) > 2 else ""}
        funds.append(
            _normalize_fund(
                {
                    "symbol": row.get("CODE") or row.get("FCODE") or row.get("code"),
                    "name": row.get("NAME") or row.get("SHORTNAME") or row.get("name"),
                    "fund_type": row.get("FundBaseType") or row.get("FTYPE") or "公募基金",
                    "data_source": "东方财富公开搜索接口",
                }
            )
        )
    return [item for item in funds if item["symbol"]]


def _search_akshare(keyword: str) -> List[Dict[str, Any]]:
    ak, error = _load_akshare()
    if not ak:
        raise RuntimeError(error)
    funds = []
    if keyword:
        df = ak.fund_name_em()
        if df is not None and not df.empty:
            code_col = "基金代码"
            name_col = "基金简称"
            type_col = "基金类型"
            filtered = df[
                df[code_col].astype(str).str.contains(keyword, case=False, na=False)
                | df[name_col].astype(str).str.contains(keyword, case=False, na=False)
            ]
            daily = {}
            try:
                daily = _ak_daily_map()
            except Exception:
                daily = {}
            for _, row in filtered.head(50).iterrows():
                code = _clean_code(row.get(code_col))
                base = {
                    "symbol": code,
                    "name": row.get(name_col),
                    "fund_type": row.get(type_col),
                    "data_source": "AKShare/东方财富基金名称库",
                }
                base.update(daily.get(code, {}))
                funds.append(_normalize_fund(base))
    else:
        df = ak.fund_open_fund_rank_em(symbol="全部")
        if df is not None and not df.empty:
            for _, row in df.head(80).iterrows():
                funds.append(
                    _normalize_fund(
                        {
                            "symbol": _pick(row, ["基金代码"]),
                            "name": _pick(row, ["基金简称"]),
                            "fund_type": _pick(row, ["基金类型"]),
                            "latest_nav": _pick(row, ["单位净值"]),
                            "daily_change": _pick(row, ["日增长率"]),
                            "week_return": _pick(row, ["近1周"]),
                            "month_return": _pick(row, ["近1月"]),
                            "three_month_return": _pick(row, ["近3月"]),
                            "six_month_return": _pick(row, ["近6月"]),
                            "year_return": _pick(row, ["近1年", "今年来"]),
                            "three_year_return": _pick(row, ["近3年"]),
                            "data_source": "AKShare/东方财富开放基金排行",
                        }
                    )
                )
    return [item for item in funds if item["symbol"]]


def search_funds(keyword: str = "", refresh: bool = False) -> Dict[str, Any]:
    keyword = str(keyword or "").strip()
    cache_key = f"fund-search:{keyword}"
    if not refresh:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    errors = []
    funds: List[Dict[str, Any]] = []
    try:
        funds.extend(_search_eastmoney(keyword))
    except Exception as exc:
        errors.append(f"东方财富搜索暂不可用：{exc}")
    try:
        ak_rows = _search_akshare(keyword)
        known = {item["symbol"] for item in funds}
        funds.extend([item for item in ak_rows if item["symbol"] not in known])
    except Exception as exc:
        errors.append(f"AKShare 基金数据暂不可用：{exc}")

    if not funds:
        funds = [
            item.copy()
            for item in SAMPLE_FUNDS
            if not keyword or keyword in item["symbol"] or keyword.lower() in item["name"].lower()
        ]
    result = {"funds": funds[:80], "errors": errors, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    return _cache_set(cache_key, result)


def _history_from_akshare(symbol: str) -> List[Dict[str, Any]]:
    ak, error = _load_akshare()
    if not ak:
        raise RuntimeError(error)
    df = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
    history = []
    if df is not None and not df.empty:
        for _, row in df.tail(760).iterrows():
            history.append(
                {
                    "date": str(_pick(row, ["净值日期", "日期"])),
                    "nav": _to_float(_pick(row, ["单位净值", "净值"])),
                    "change_percent": _to_float(_pick(row, ["日增长率", "涨跌幅"])),
                }
            )
    return [item for item in history if item["nav"] > 0]


def _history_from_eastmoney(symbol: str) -> List[Dict[str, Any]]:
    payload = _request_json(
        "https://api.fund.eastmoney.com/f10/lsjz",
        {"fundCode": symbol, "pageIndex": 1, "pageSize": 760},
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


def _enrich_holdings(fund: Dict[str, Any], errors: List[str]) -> None:
    ak, _ = _load_akshare()
    if not ak:
        return
    year = str(datetime.now().year - 1)
    try:
        hold_df = ak.fund_portfolio_hold_em(symbol=fund["symbol"], date=year)
        if hold_df is not None and not hold_df.empty:
            name_col = "股票名称" if "股票名称" in hold_df.columns else hold_df.columns[0]
            fund["top_stocks"] = ",".join([str(v) for v in hold_df[name_col].head(8).tolist()])
    except Exception as exc:
        errors.append(f"重仓股票暂不可用：{exc}")
    try:
        industry_df = ak.fund_portfolio_industry_allocation_em(symbol=fund["symbol"], date=year)
        if industry_df is not None and not industry_df.empty:
            name_col = "行业类别" if "行业类别" in industry_df.columns else industry_df.columns[0]
            fund["industries"] = ",".join([str(v) for v in industry_df[name_col].head(6).tolist()])
    except Exception as exc:
        errors.append(f"行业配置暂不可用：{exc}")


def get_fund_detail(symbol: str, refresh: bool = False) -> Dict[str, Any]:
    symbol = _clean_code(symbol)
    cache_key = f"fund-detail:{symbol}"
    if not refresh:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    errors = []
    fund = next((item.copy() for item in SAMPLE_FUNDS if item["symbol"] == symbol), None)
    if not fund:
        search_result = search_funds(symbol)
        fund = next((item.copy() for item in search_result["funds"] if item["symbol"] == symbol), None)
        errors.extend(search_result.get("errors", []))
    if not fund:
        fund = _normalize_fund({"symbol": symbol, "name": f"{symbol} 基金", "data_source": "代码占位"})

    history = []
    try:
        history = _history_from_akshare(symbol)
    except Exception as exc:
        errors.append(f"AKShare 净值走势暂不可用：{exc}")
    if not history:
        try:
            history = _history_from_eastmoney(symbol)
        except Exception as exc:
            errors.append(f"东方财富历史净值暂不可用：{exc}")
    if not history:
        history = _sample_history(fund.get("latest_nav") or 1.0)

    metrics = _history_metrics(history)
    fund.update({k: v for k, v in metrics.items() if v is not None})
    if history:
        latest = history[-1]
        fund["latest_nav"] = latest.get("nav") or fund.get("latest_nav")
        fund["daily_change"] = latest.get("change_percent") or fund.get("daily_change")
        fund["estimated_nav"] = fund.get("estimated_nav") or fund["latest_nav"]
    _enrich_holdings(fund, errors)
    fund["history"] = history[-260:]
    fund["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = {"fund": fund, "errors": list(dict.fromkeys(errors))}
    return _cache_set(cache_key, result)


def recommendation_pool(refresh: bool = False) -> Dict[str, Any]:
    return search_funds("", refresh=refresh)


def get_fund_trend(symbol: str, limit: int = 45, refresh: bool = False) -> Dict[str, Any]:
    symbol = _clean_code(symbol)
    cache_key = f"fund-trend:{symbol}:{limit}"
    if not refresh:
        cached = _cache_get(cache_key)
        if cached:
            return cached
    errors = []
    history = []
    try:
        history = _history_from_eastmoney(symbol)[-limit:]
    except Exception as exc:
        errors.append(f"东方财富净值走势暂不可用：{exc}")
    if not history:
        base = next((item.get("latest_nav") for item in SAMPLE_FUNDS if item["symbol"] == symbol), 1.0)
        history = _sample_history(base)[-limit:]
    latest = history[-1] if history else {}
    result = {
        "history": history,
        "latest_nav": latest.get("nav"),
        "daily_change": latest.get("change_percent"),
        "errors": errors,
    }
    return _cache_set(cache_key, result)
