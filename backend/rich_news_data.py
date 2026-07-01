from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "data_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
NEWS_TTL = 60 * 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn/",
}

TOPIC_RULES = [
    (["AI", "人工智能", "算力", "半导体", "芯片", "科技", "数字经济"], ["科技", "人工智能", "半导体", "成长"], "偏利好科技成长基金"),
    (["新能源", "电池", "光伏", "储能", "汽车", "电动车"], ["新能源", "电池", "光伏", "高端制造"], "偏利好新能源基金"),
    (["消费", "白酒", "食品", "家电", "旅游", "零售"], ["消费", "食品饮料", "白酒", "家电"], "偏利好消费基金"),
    (["医药", "创新药", "医疗", "生物"], ["医药", "创新药", "医疗服务"], "偏利好医药基金"),
    (["红利", "央企", "高股息", "银行", "保险"], ["红利", "央企", "价值", "金融"], "偏利好红利价值基金"),
    (["债券", "利率", "降息", "货币", "国债"], ["短债", "货币基金", "债券"], "影响债券和稳健类基金"),
    (["港股", "互联网", "恒生", "QDII", "美股"], ["港股", "互联网", "QDII"], "影响港股和海外基金"),
    (["黄金", "原油", "汇率", "美元", "资源"], ["黄金", "资源", "QDII"], "影响商品和海外资产基金"),
]

FALLBACK_TOPICS = [
    ("人工智能产业链保持活跃，算力和应用端仍是市场关注方向", "科技,人工智能,半导体", "短期涨幅过高的主题基金"),
    ("半导体国产替代预期升温，芯片主题基金关注度提高", "半导体,科技,高端制造", "高位追涨基金"),
    ("新能源车销量数据改善，电池和汽车产业链情绪修复", "新能源,电池,汽车", "短线追高资金"),
    ("创新药政策环境改善，医药基金关注度回升", "医药,创新药,医疗服务", "短期涨幅过高的医药基金"),
    ("消费数据温和修复，食品饮料和白酒方向进入观察期", "消费,食品饮料,白酒", "短线追高资金"),
    ("红利资产继续受到稳健资金关注", "红利,央企,高股息", "估值过高的红利基金"),
    ("债券收益率波动，长债基金净值可能出现起伏", "短债,货币基金,债券", "长债,高久期债券基金"),
    ("港股互联网反弹，QDII 和港股基金关注度上升", "互联网,QDII,港股", "海外市场高波动基金"),
    ("黄金价格波动加大，商品基金需要控制仓位", "黄金,资源", "高波动商品基金"),
    ("市场成交回暖，券商和金融科技方向活跃", "券商,金融科技", "短线追高资金"),
]

MARKET_KEYWORDS = [
    "A股",
    "港股",
    "美股",
    "基金",
    "市场",
    "指数",
    "板块",
    "行业",
    "政策",
    "经济",
    "央行",
    "利率",
    "汇率",
    "债券",
    "黄金",
    "原油",
    "消费",
    "科技",
    "人工智能",
    "半导体",
    "芯片",
    "新能源",
    "医药",
    "白酒",
    "银行",
    "证券",
    "红利",
    "QDII",
    "沪指",
    "深成指",
    "创业板",
    "北向",
    "资金",
    "财报",
    "上市公司",
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _cache_path() -> Path:
    return CACHE_DIR / "market_news.json"


def _read_cache(allow_stale: bool = True) -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stale = time.time() - float(payload.get("cached_at_ts", 0)) > NEWS_TTL
        if stale and not allow_stale:
            return None
        data = payload.get("data")
        if isinstance(data, dict):
            data["cache"] = {"hit": True, "stale": stale, "cached_at": payload.get("cached_at")}
        return data
    except Exception:
        return None


def _write_cache(data: dict[str, Any]) -> dict[str, Any]:
    _cache_path().write_text(
        json.dumps({"cached_at_ts": time.time(), "cached_at": _now(), "data": data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data


def _request_json(url: str, params: dict[str, Any] | None = None, timeout: int = 8) -> Any:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    text = response.text.strip()
    if "(" in text and text.rfind(")") > text.find("("):
        text = text[text.find("(") + 1 : text.rfind(")")]
    return json.loads(text)


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _is_market_related(title: str, content: str = "") -> bool:
    text = f"{title} {content}"
    return any(keyword in text for keyword in MARKET_KEYWORDS)


def analyze_news_item(
    title: str,
    content: str = "",
    source: str = "公开资讯",
    published_at: str = "",
    original_url: str = "",
) -> dict[str, Any]:
    title = _clean_html(title) or "市场资讯"
    content = _clean_html(content or title)
    text = f"{title} {content}"
    positive: list[str] = []
    negative: list[str] = []
    direction = "需要观察"
    for keys, tags, rule_direction in TOPIC_RULES:
        if any(key in text for key in keys):
            positive.extend(tags)
            direction = rule_direction

    risk_words = ["风险", "下跌", "监管", "亏损", "回调", "利空", "退潮", "高位", "减持"]
    impact_level = "中"
    if any(word in text for word in risk_words):
        impact_level = "高"
        negative.extend(["高波动主题基金", "短期追高基金"])
    if "债" in text or "利率" in text:
        negative.extend(["长债", "高久期债券基金"])
    if not positive:
        positive.append("暂无明确方向")
    if not negative:
        negative.append("暂无明确方向")

    positive_text = ",".join(dict.fromkeys(positive))
    negative_text = ",".join(dict.fromkeys(negative))
    plain = (
        f"这条消息可能影响 {positive_text} 方向。简单说，就是市场可能会重新关注这些行业，"
        "相关基金短期净值可能跟着情绪波动；但单条新闻不能直接决定买卖，还要看基金持仓、估值和近期涨跌。"
    )
    operation = "作为观察线索使用；如果基金已经涨很多，偏向等回调或减仓观察；如果近期回撤较多且评分较高，可以考虑小额分批。"

    return {
        "title": title,
        "source": source or "公开资讯",
        "published_at": published_at or _now(),
        "summary": content[:240],
        "original_text": content,
        "original_url": original_url or f"https://www.baidu.com/s?wd={quote_plus(title)}",
        "impact_direction": direction,
        "positive_types": positive_text,
        "negative_types": negative_text,
        "impact_level": impact_level,
        "plain_explanation": plain,
        "operation_reference": operation,
    }


def _fetch_sina(limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lid in ["2515", "2516", "2517", "2518"]:
        payload = _request_json(
            "https://feed.mix.sina.com.cn/api/roll/get",
            {"pageid": "153", "lid": lid, "num": min(30, limit), "page": 1},
        )
        for row in (payload.get("result", {}).get("data") or [])[:limit]:
            title = row.get("title") or ""
            content = row.get("intro") or row.get("keywords") or title
            if not _is_market_related(title, content):
                continue
            rows.append(
                analyze_news_item(
                    title=title,
                    content=content,
                    source="新浪财经公开资讯",
                    published_at=str(row.get("ctime") or _now()),
                    original_url=str(row.get("url") or ""),
                )
            )
    return rows


def _fetch_eastmoney(limit: int) -> list[dict[str, Any]]:
    payload = _request_json(
        "https://newsapi.eastmoney.com/kuaixun/v2/api/list",
        {"column": "102", "limit": min(limit, 50)},
    )
    rows = payload.get("data") or payload.get("LivesList") or payload.get("list") or []
    news: list[dict[str, Any]] = []
    for row in rows[:limit]:
        title = row.get("title") or row.get("digest") or row.get("content") or ""
        content = row.get("digest") or row.get("content") or ""
        if not _is_market_related(title, content):
            continue
        news.append(
            analyze_news_item(
                title=title,
                content=content,
                source=row.get("source") or "东方财富公开快讯",
                published_at=str(row.get("showtime") or row.get("time") or _now()),
                original_url=str(row.get("url") or row.get("news_url") or ""),
            )
        )
    return news


def _fallback_news(limit: int) -> list[dict[str, Any]]:
    rows = []
    for title, positive, negative in FALLBACK_TOPICS:
        item = analyze_news_item(
            title=title,
            content=f"{title}。这是公开数据源暂时不可用时的本地兜底资讯，用来保证页面可读；真实判断请优先看可打开的原文链接。",
            source="本地兜底资讯",
            published_at=_now(),
            original_url=f"https://www.baidu.com/s?wd={quote_plus(title)}",
        )
        item["positive_types"] = positive
        item["negative_types"] = negative
        rows.append(item)
    return rows[:limit]


def get_market_news(limit: int = 50, refresh: bool = False) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 100))
    if not refresh:
        cached = _read_cache(allow_stale=False)
        if cached:
            return cached

    errors: list[str] = []
    news: list[dict[str, Any]] = []
    for name, loader in [("新浪财经", _fetch_sina), ("东方财富快讯", _fetch_eastmoney)]:
        try:
            news.extend(loader(limit))
        except Exception as exc:
            errors.append(f"{name}暂不可用：{exc}")

    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in news:
        title = item.get("title", "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        deduped.append(item)

    if len(deduped) < min(limit, 12):
        deduped.extend([item for item in _fallback_news(limit) if item["title"] not in seen])

    result = {
        "news": deduped[:limit],
        "errors": errors,
        "updated_at": _now(),
        "count": len(deduped[:limit]),
        "source": "新浪财经/东方财富公开资讯",
        "cache": {"hit": False, "stale": False, "cached_at": ""},
    }
    if deduped:
        return _write_cache(result)
    cached = _read_cache(allow_stale=True)
    if cached:
        cached.setdefault("errors", []).extend(errors)
        return cached
    return result


def _terms_for_fund(fund: dict[str, Any]) -> list[str]:
    raw = [
        fund.get("name", ""),
        fund.get("symbol", ""),
        fund.get("fund_type", ""),
        fund.get("industries", ""),
        fund.get("top_stocks", ""),
        fund.get("manager", ""),
        fund.get("company", ""),
    ]
    terms: list[str] = []
    for part in raw:
        for term in re.split(r"[,，、\s]+", str(part or "")):
            term = term.strip()
            if len(term) >= 2 and term not in {"资料待补全", "暂无数据"}:
                terms.append(term)
    return list(dict.fromkeys(terms))


def match_news_for_funds(news: list[dict[str, Any]], funds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for item in news:
        news_text = " ".join(
            [
                item.get("title", ""),
                item.get("summary", ""),
                item.get("original_text", ""),
                item.get("positive_types", ""),
                item.get("negative_types", ""),
            ]
        )
        for fund in funds:
            hit_terms = [term for term in _terms_for_fund(fund) if term in news_text]
            if not hit_terms:
                continue
            effect = "观察"
            if any(term in item.get("positive_types", "") for term in hit_terms):
                effect = "利好"
            if any(term in item.get("negative_types", "") for term in hit_terms) or item.get("impact_level") == "高":
                effect = "风险"
            matched.append(
                {
                    "news": item,
                    "fund": fund,
                    "reason": f"匹配到：{','.join(hit_terms[:6])}",
                    "effect": effect,
                    "nav_impact": "短期净值可能跟随相关行业情绪波动，实际表现还要看基金真实持仓和市场走势。",
                    "decision_hint": "这条资讯只作为加减仓证据之一，需要和评分、回撤、近期涨幅、持仓盈亏一起看。",
                    "plain_explanation": f"这条资讯和 {fund.get('name')} 可能有关，因为内容里出现了基金名称、类型、行业或重仓线索。",
                }
            )
    return matched
