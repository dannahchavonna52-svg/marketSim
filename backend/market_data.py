from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


SUPPORTED_TYPES = {"stock", "etf", "fund", "index"}
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_SECONDS = 20


def _load_akshare():
    try:
        import akshare as ak

        return ak, None
    except Exception as exc:
        return None, f"AKShare 未安装或导入失败：{exc}"


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        text = str(value).replace("%", "").replace(",", "").strip()
        if text in {"", "-", "--", "nan", "None"}:
            return None
        return float(text)
    except Exception:
        return None


def _cached_df(cache_key: str, loader: Callable[[], Any]):
    cached = _CACHE.get(cache_key)
    now = datetime.now().timestamp()
    if cached and now - cached["time"] < _CACHE_SECONDS:
        return cached["data"]
    df = loader()
    _CACHE[cache_key] = {"time": now, "data": df}
    return df


def _find_column(columns, exact_names=None, contains=None, endswith=None, exclude=None):
    exact_names = exact_names or []
    contains = contains or []
    endswith = endswith or []
    exclude = exclude or []
    for name in exact_names:
        if name in columns:
            return name
    for col in columns:
        text = str(col)
        if any(item in text for item in exclude):
            continue
        if contains and all(item in text for item in contains):
            return col
        if endswith and any(text.endswith(item) for item in endswith):
            return col
    return None


def _find_row(df, symbol: str, code_candidates: List[str]):
    symbol = _normalize_symbol(symbol)
    for code_col in code_candidates:
        if code_col in df.columns:
            match = df[df[code_col].astype(str).str.upper().str.strip() == symbol]
            if not match.empty:
                return match.iloc[0]
    return None


def _quote_from_row(row, symbol: str, asset_type: str, name_col: str, price_col: str, pct_col: Optional[str], date_col: Optional[str] = None):
    price = _to_float(row.get(price_col))
    pct = _to_float(row.get(pct_col)) if pct_col else None
    update_time = str(row.get(date_col)) if date_col and row.get(date_col) is not None else _now_text()
    if price is None:
        raise ValueError("行情价格为空")
    return {
        "symbol": _normalize_symbol(symbol),
        "name": str(row.get(name_col, "")),
        "asset_type": asset_type,
        "price": price,
        "change_percent": pct,
        "update_time": update_time,
        "source": "AKShare",
    }


def get_quote(symbol: str, asset_type: str) -> Dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    asset_type = str(asset_type).strip().lower()
    if asset_type not in SUPPORTED_TYPES:
        return {"success": False, "error": f"暂不支持的标的类型：{asset_type}", "data": None}

    try:
        if asset_type == "stock":
            data = _get_stock_quote(symbol)
        elif asset_type == "etf":
            data = _get_etf_quote(symbol)
        elif asset_type == "fund":
            data = _get_fund_quote(symbol)
        else:
            data = _get_index_quote(symbol)
        return {"success": True, "error": "", "data": data}
    except Exception as exc:
        return {"success": False, "error": f"{symbol} 行情获取失败：{exc}", "data": None}


def _get_stock_quote(symbol: str) -> Dict[str, Any]:
    ak, error = _load_akshare()
    if error:
        raise RuntimeError(error)
    df = _cached_df("stock_zh_a_spot_em", ak.stock_zh_a_spot_em)
    row = _find_row(df, symbol, ["代码", "code"])
    if row is None:
        raise ValueError("未在 A 股实时行情中找到该代码")
    price_col = _find_column(df.columns, exact_names=["最新价"])
    pct_col = _find_column(df.columns, exact_names=["涨跌幅"])
    return _quote_from_row(row, symbol, "stock", "名称", price_col, pct_col)


def _get_etf_quote(symbol: str) -> Dict[str, Any]:
    ak, error = _load_akshare()
    if error:
        raise RuntimeError(error)
    df = _cached_df("fund_etf_spot_em", ak.fund_etf_spot_em)
    row = _find_row(df, symbol, ["代码", "code"])
    if row is None:
        raise ValueError("未在 ETF 实时行情中找到该代码")
    price_col = _find_column(df.columns, exact_names=["最新价"])
    pct_col = _find_column(df.columns, exact_names=["涨跌幅"])
    return _quote_from_row(row, symbol, "etf", "名称", price_col, pct_col)


def _get_fund_quote(symbol: str) -> Dict[str, Any]:
    ak, error = _load_akshare()
    if error:
        raise RuntimeError(error)

    try:
        df = _cached_df("fund_open_fund_daily_em", ak.fund_open_fund_daily_em)
        row = _find_row(df, symbol, ["基金代码"])
        if row is not None:
            price_col = _find_column(df.columns, exact_names=["单位净值"], contains=["单位净值"], exclude=["前交易日", "累计"])
            pct_col = _find_column(df.columns, exact_names=["日增长率"])
            return _quote_from_row(row, symbol, "fund", "基金简称", price_col, pct_col)
    except Exception:
        # Daily list can be temporarily unavailable; single-fund history is a useful fallback.
        pass

    hist = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
    if hist is None or hist.empty:
        raise ValueError("未获取到该基金净值数据")
    row = hist.iloc[-1]
    price = _to_float(row.get("单位净值"))
    if price is None:
        raise ValueError("基金净值为空")
    return {
        "symbol": symbol,
        "name": "",
        "asset_type": "fund",
        "price": price,
        "change_percent": _to_float(row.get("日增长率")),
        "update_time": str(row.get("净值日期", _now_text())),
        "source": "AKShare",
    }


def _get_index_quote(symbol: str) -> Dict[str, Any]:
    ak, error = _load_akshare()
    if error:
        raise RuntimeError(error)

    if hasattr(ak, "stock_zh_index_spot_em"):
        df = _cached_df("stock_zh_index_spot_em", ak.stock_zh_index_spot_em)
        row = _find_row(df, symbol, ["代码", "code"])
        if row is not None:
            price_col = _find_column(df.columns, exact_names=["最新价"])
            pct_col = _find_column(df.columns, exact_names=["涨跌幅"])
            return _quote_from_row(row, symbol, "index", "名称", price_col, pct_col)

    hist = ak.index_zh_a_hist(symbol=symbol, period="daily", start_date="19700101", end_date="22220101")
    if hist is None or hist.empty:
        raise ValueError("未获取到该指数行情")
    row = hist.iloc[-1]
    price = _to_float(row.get("收盘"))
    if price is None:
        raise ValueError("指数收盘价为空")
    return {
        "symbol": symbol,
        "name": "",
        "asset_type": "index",
        "price": price,
        "change_percent": _to_float(row.get("涨跌幅")),
        "update_time": str(row.get("日期", _now_text())),
        "source": "AKShare",
    }


def get_quotes(items: List[Any]) -> List[Dict[str, Any]]:
    quotes = []
    for item in items:
        result = get_quote(item.symbol, item.asset_type)
        if result["success"]:
            quote = result["data"]
            if not quote.get("name"):
                quote["name"] = item.name
            quote["watchlist_id"] = item.id
            quote["note"] = item.note
            quotes.append({"success": True, "data": quote, "error": ""})
        else:
            quotes.append(
                {
                    "success": False,
                    "error": result["error"],
                    "data": {
                        "watchlist_id": item.id,
                        "symbol": item.symbol,
                        "name": item.name,
                        "asset_type": item.asset_type,
                        "note": item.note,
                    },
                }
            )
    return quotes


def get_major_indices() -> Dict[str, Any]:
    indices = [
        {"symbol": "000001", "name": "上证指数"},
        {"symbol": "399001", "name": "深证成指"},
        {"symbol": "399006", "name": "创业板指"},
        {"symbol": "000300", "name": "沪深300"},
        {"symbol": "000905", "name": "中证500"},
    ]
    rows = []
    errors = []
    for item in indices:
        result = get_quote(item["symbol"], "index")
        if result["success"]:
            quote = result["data"]
            quote["name"] = quote.get("name") or item["name"]
            rows.append(quote)
        else:
            errors.append(result["error"])
            rows.append(
                {
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "asset_type": "index",
                    "price": None,
                    "change_percent": None,
                    "update_time": "",
                    "source": "AKShare",
                    "error": result["error"],
                }
            )
    return {"indices": rows, "errors": errors}


# Final override for the dashboard indices. AKShare may inherit a broken system
# proxy, so this path uses a direct public Eastmoney quote endpoint first and
# falls back to readable local placeholders.
def get_major_indices() -> Dict[str, Any]:
    import requests

    mapping = [
        {"secid": "1.000001", "symbol": "000001", "name": "上证指数"},
        {"secid": "0.399001", "symbol": "399001", "name": "深证成指"},
        {"secid": "0.399006", "symbol": "399006", "name": "创业板指"},
        {"secid": "1.000300", "symbol": "000300", "name": "沪深300"},
        {"secid": "1.000905", "symbol": "000905", "name": "中证500"},
    ]
    fallback_prices = {
        "000001": 3000.0,
        "399001": 9500.0,
        "399006": 1800.0,
        "000300": 3500.0,
        "000905": 5200.0,
    }
    try:
        session = requests.Session()
        session.trust_env = False
        params = {
            "fltt": "2",
            "secids": ",".join(item["secid"] for item in mapping),
            "fields": "f12,f14,f2,f3",
        }
        last_error = None
        response = None
        for url in [
            "https://push2.eastmoney.com/api/qt/ulist.np/get",
            "https://82.push2.eastmoney.com/api/qt/ulist.np/get",
            "https://48.push2.eastmoney.com/api/qt/ulist.np/get",
        ]:
            try:
                response = session.get(
                    url,
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
                    timeout=15,
                )
                response.raise_for_status()
                break
            except Exception as exc:
                last_error = exc
                response = None
        if response is None:
            raise last_error or RuntimeError("指数接口无响应")
        rows = response.json().get("data", {}).get("diff", []) or []
        by_code = {str(row.get("f12")): row for row in rows}
        indices = []
        for item in mapping:
            row = by_code.get(item["symbol"], {})
            price = _to_float(row.get("f2"))
            pct = _to_float(row.get("f3"))
            indices.append(
                {
                    "symbol": item["symbol"],
                    "name": str(row.get("f14") or item["name"]),
                    "asset_type": "index",
                    "price": price,
                    "change_percent": pct,
                    "update_time": _now_text(),
                    "source": "东方财富公开行情",
                }
            )
        if any(item["price"] is not None for item in indices):
            return {"indices": indices, "errors": []}
        raise ValueError("指数接口返回为空")
    except Exception as exc:
        return {
            "indices": [
                {
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "asset_type": "index",
                    "price": fallback_prices[item["symbol"]],
                    "change_percent": None,
                    "update_time": _now_text(),
                    "source": "本地兜底",
                    "error": "实时指数暂不可用，显示兜底参考值",
                }
                for item in mapping
            ],
            "errors": [f"实时指数获取失败：{exc}"],
        }


# Final cache-aware override. If live quote fetching fails, show the last
# successful real quote instead of synthetic fallback numbers.
def get_major_indices() -> Dict[str, Any]:
    import json
    from pathlib import Path

    import requests

    mapping = [
        {"secid": "1.000001", "symbol": "000001", "name": "上证指数"},
        {"secid": "0.399001", "symbol": "399001", "name": "深证成指"},
        {"secid": "0.399006", "symbol": "399006", "name": "创业板指"},
        {"secid": "1.000300", "symbol": "000300", "name": "沪深300"},
        {"secid": "1.000905", "symbol": "000905", "name": "中证500"},
    ]
    cache_file = Path(__file__).resolve().parent / "data" / "market_indices_cache.json"

    def load_cache() -> Optional[Dict[str, Any]]:
        try:
            if cache_file.exists():
                return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        return None

    def save_cache(payload: Dict[str, Any]) -> None:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    try:
        session = requests.Session()
        session.trust_env = False
        response = session.get(
            "https://push2.eastmoney.com/api/qt/ulist.np/get",
            params={
                "fltt": "2",
                "secids": ",".join(item["secid"] for item in mapping),
                "fields": "f12,f14,f2,f3",
            },
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
            timeout=6,
        )
        response.raise_for_status()
        rows = response.json().get("data", {}).get("diff", []) or []
        by_code = {str(row.get("f12")): row for row in rows}
        now = _now_text()
        indices = []
        for item in mapping:
            row = by_code.get(item["symbol"], {})
            indices.append(
                {
                    "symbol": item["symbol"],
                    "name": str(row.get("f14") or item["name"]),
                    "asset_type": "index",
                    "price": _to_float(row.get("f2")),
                    "change_percent": _to_float(row.get("f3")),
                    "update_time": now,
                    "source": "东方财富公开行情",
                    "is_stale": False,
                }
            )
        if not any(item["price"] is not None for item in indices):
            raise ValueError("指数接口返回为空")
        payload = {"indices": indices, "errors": [], "last_success_at": now, "is_stale": False}
        save_cache(payload)
        return payload
    except Exception as exc:
        cached = load_cache()
        if cached and cached.get("indices"):
            last_time = cached.get("last_success_at") or cached["indices"][0].get("update_time") or ""
            stale_rows = []
            for row in cached["indices"]:
                copied = dict(row)
                copied["is_stale"] = True
                copied["source"] = f"{copied.get('source', '历史缓存')}（上次成功）"
                copied["error"] = f"实时获取失败，显示上次成功数据：{last_time}"
                stale_rows.append(copied)
            return {
                "indices": stale_rows,
                "errors": [f"实时指数获取失败，已显示上次成功数据：{exc}"],
                "last_success_at": last_time,
                "is_stale": True,
            }
        now = _now_text()
        return {
            "indices": [
                {
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "asset_type": "index",
                    "price": None,
                    "change_percent": None,
                    "update_time": now,
                    "source": "暂无缓存",
                    "is_stale": True,
                    "error": "实时获取失败，且还没有上次成功数据",
                }
                for item in mapping
            ],
            "errors": [f"实时指数获取失败，暂无历史缓存：{exc}"],
            "last_success_at": "",
            "is_stale": True,
        }


# Fund quote override: use the richer fund-data adapter for watchlist/position
# refreshes so public fund NAV keeps working even when AKShare is unavailable.
def _get_fund_quote(symbol: str) -> Dict[str, Any]:
    import rich_fund_data

    detail = rich_fund_data.get_fund_detail(symbol)
    fund = detail.get("fund", {})
    price = _to_float(fund.get("estimated_nav")) or _to_float(fund.get("latest_nav"))
    if price is None:
        raise ValueError("未获取到该基金净值")
    return {
        "symbol": _normalize_symbol(symbol),
        "name": str(fund.get("name") or ""),
        "asset_type": "fund",
        "price": price,
        "change_percent": _to_float(fund.get("daily_change")),
        "update_time": str(fund.get("updated_at") or _now_text()),
        "source": str(fund.get("data_source") or "公开基金数据"),
    }
