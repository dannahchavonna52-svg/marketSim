from datetime import datetime
from typing import Any, Dict, List


SAMPLE_NEWS = [
    {
        "title": "政策继续支持科技创新和数字经济",
        "source": "公开资讯整理",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": "市场关注科技创新、人工智能和数字经济相关方向。",
        "impact_direction": "偏利好成长类基金",
        "positive_types": "科技,人工智能,数字经济,成长",
        "negative_types": "短期涨幅过高的主题基金",
        "impact_level": "中",
        "plain_explanation": "这类消息会提高市场对科技方向的关注。如果你的基金重仓科技股，短期可能受益，但涨得太快也容易回调。",
        "operation_reference": "适合观察或小额分批，不建议一次性重仓追高。",
    },
    {
        "title": "消费板块出现修复迹象",
        "source": "公开资讯整理",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": "食品饮料、家电、零售等方向受到资金关注。",
        "impact_direction": "偏利好消费基金",
        "positive_types": "消费,食品饮料,家电",
        "negative_types": "短线追高资金",
        "impact_level": "中",
        "plain_explanation": "消费恢复会让相关公司的预期变好，消费主题基金可能受益。但消费基金波动也不小，需要看估值和持仓。",
        "operation_reference": "已有持仓可继续观察，没买的人更适合分批而不是追涨。",
    },
    {
        "title": "债券市场波动加大，稳健类产品需要关注久期风险",
        "source": "公开资讯整理",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": "利率变化会影响债券基金净值表现。",
        "impact_direction": "影响债券基金",
        "positive_types": "短债,货币基金",
        "negative_types": "长债,高久期债券基金",
        "impact_level": "低",
        "plain_explanation": "债券基金不是完全不会跌，利率变化时也会有净值波动。稳健用户要注意产品持仓久期。",
        "operation_reference": "稳健资金可优先看短债或货币类，长债基金不适合盲目重仓。",
    },
]

MORE_SAMPLE_TOPICS = [
    ("人工智能产业链继续活跃，算力和应用端受关注", "科技,人工智能,半导体,成长", "短期涨幅过高的主题基金"),
    ("半导体国产替代预期升温，芯片主题基金关注度提高", "半导体,科技,高端制造", "高位追涨基金"),
    ("新能源车销量数据改善，电池和汽车产业链情绪修复", "新能源,电池,汽车", "短线追高资金"),
    ("光伏板块仍在消化产能压力，相关基金波动可能加大", "光伏,新能源", "高波动主题基金"),
    ("创新药政策环境改善，医药基金关注度回升", "医药,创新药,医疗服务", "短期涨幅过高的医药基金"),
    ("消费数据温和修复，食品饮料和白酒方向进入观察期", "消费,食品饮料,白酒", "短线追高资金"),
    ("红利资产继续受到稳健资金关注", "红利,央企,高股息", "估值过高的红利基金"),
    ("债券收益率波动，长债基金净值可能出现起伏", "短债,货币基金,债券", "长债,高久期债券基金"),
    ("港股互联网出现反弹，QDII 和港股基金关注度上升", "互联网,QDII,港股", "海外市场高波动基金"),
    ("美元和汇率变化影响海外资产表现", "QDII,黄金,资源", "汇率敏感基金"),
    ("黄金价格波动加大，商品基金需要控制仓位", "黄金,资源", "高波动商品基金"),
    ("原油价格影响能源和化工方向", "资源,能源,化工", "油价敏感基金"),
    ("地产政策边际改善，地产链基金仍需观察持续性", "地产,建材,家居", "高杠杆地产链基金"),
    ("银行保险板块偏稳，低估值风格受到关注", "银行,保险,价值", "短线追高资金"),
    ("军工板块消息催化增多，但主题波动较大", "军工,高端制造", "高波动主题基金"),
    ("市场成交回暖，券商和金融科技方向活跃", "券商,金融科技", "短线追高资金"),
    ("中证A500、沪深300等宽基指数关注度提升", "宽基指数,指数基金", "短期涨幅过快的指数基金"),
]


def _load_akshare():
    try:
        import akshare as ak

        return ak, None
    except Exception as exc:
        return None, f"AKShare 不可用：{exc}"


def get_market_news(limit: int = 20) -> Dict[str, Any]:
    news = []
    errors = []
    ak, error = _load_akshare()
    if ak:
        try:
            if hasattr(ak, "stock_news_em"):
                df = ak.stock_news_em()
                if df is not None and not df.empty:
                    for _, row in df.head(limit).iterrows():
                        title = str(row.get("新闻标题", row.get("标题", "")))
                        content = str(row.get("新闻内容", row.get("摘要", "")))
                        news.append(analyze_news_item(title, content, str(row.get("文章来源", "东方财富公开资讯")), str(row.get("发布时间", ""))))
        except Exception as exc:
            errors.append(f"公开资讯获取失败：{exc}")
    elif error:
        errors.append(error)

    if not news:
        news = SAMPLE_NEWS[:limit]
    return {"news": news, "errors": errors, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def analyze_news_item(title: str, content: str = "", source: str = "公开资讯", published_at: str = "") -> Dict[str, Any]:
    text = f"{title} {content}"
    positive = []
    negative = []
    direction = "需要观察"
    level = "中"

    if any(key in text for key in ["科技", "人工智能", "半导体", "数字"]):
        positive.extend(["科技", "人工智能", "半导体", "成长"])
        direction = "偏利好科技成长基金"
    if any(key in text for key in ["消费", "食品", "白酒", "家电"]):
        positive.extend(["消费", "食品饮料", "白酒"])
        direction = "偏利好消费基金"
    if any(key in text for key in ["新能源", "光伏", "电池", "汽车"]):
        positive.extend(["新能源", "高端制造"])
        direction = "偏利好新能源基金"
    if any(key in text for key in ["利率", "债券", "汇率"]):
        positive.extend(["短债", "货币基金"])
        negative.extend(["长债", "高久期债券基金"])
        direction = "影响债券和稳健类基金"
    if any(key in text for key in ["风险", "下跌", "监管", "亏损"]):
        level = "高"
        negative.extend(["高波动主题基金", "短期追高基金"])

    positive_text = ",".join(dict.fromkeys(positive)) or "暂无明确方向"
    negative_text = ",".join(dict.fromkeys(negative)) or "暂无明确方向"
    plain = f"这条消息可能影响{positive_text}方向。普通用户可以先看自己基金是否重仓相关行业，不要只因为一条新闻就重仓买入。"
    return {
        "title": title or "市场资讯",
        "source": source or "公开资讯",
        "published_at": published_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": content[:160] if content else title,
        "impact_direction": direction,
        "positive_types": positive_text,
        "negative_types": negative_text,
        "impact_level": level,
        "plain_explanation": plain,
        "operation_reference": "仅作为观察线索，适合结合基金评分、估值和自身仓位一起判断。",
    }


def match_news_for_funds(news: List[Dict[str, Any]], funds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matched = []
    for item in news:
        news_text = " ".join(
            [
                item.get("title", ""),
                item.get("summary", ""),
                item.get("positive_types", ""),
                item.get("negative_types", ""),
            ]
        )
        for fund in funds:
            fund_terms = [
                fund.get("name", ""),
                fund.get("symbol", ""),
                fund.get("fund_type", ""),
                fund.get("industries", ""),
                fund.get("top_stocks", ""),
                fund.get("manager", ""),
                fund.get("company", ""),
            ]
            fund_terms = [term for part in fund_terms for term in str(part).replace("，", ",").split(",") if term]
            if any(term and term in news_text for term in fund_terms):
                effect = "利好" if any(term in item.get("positive_types", "") for term in fund_terms) else "观察"
                matched.append(
                    {
                        "news": item,
                        "fund": fund,
                        "reason": "资讯内容与基金名称、持仓行业、重仓股票或基金类型存在关联。",
                        "effect": effect,
                        "nav_impact": "短期净值可能跟随相关行业情绪波动，实际表现还要看基金持仓和市场走势。",
                        "decision_hint": "先观察评分和仓位变化，不建议只根据单条新闻买卖。",
                        "plain_explanation": f"这条资讯和 {fund.get('name')} 可能有关，因为它提到了基金关注的方向或持仓线索。",
                    }
                )
    return matched


# ---------------------------------------------------------------------------
# UTF-8 market news implementation, appended to override the early prototype.
# It collects more rows, keeps original text/link fields, and adds plain
# explanations for ordinary users.
# ---------------------------------------------------------------------------
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from urllib.parse import quote_plus

import requests


SAMPLE_NEWS = [
    {
        "title": "政策继续支持科技创新和数字经济",
        "source": "公开资讯整理",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": "市场关注人工智能、半导体、数字经济等方向。",
        "original_text": "市场关注人工智能、半导体、数字经济等方向，相关基金可能受市场情绪影响。",
        "original_url": "",
        "impact_direction": "偏利好科技成长基金",
        "positive_types": "科技,人工智能,半导体,数字经济,成长",
        "negative_types": "短期涨幅过高的主题基金",
        "impact_level": "中",
        "plain_explanation": "这类消息会提高市场对科技方向的关注。如果基金重仓科技股，短期可能受益，但涨得太快也容易回调。",
        "operation_reference": "适合观察或小额分批，不建议一次性重仓追高。",
    },
    {
        "title": "消费板块出现修复迹象",
        "source": "公开资讯整理",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": "食品饮料、家电、零售等方向受到资金关注。",
        "original_text": "消费方向短期有修复迹象，但需要观察持续性。",
        "original_url": "",
        "impact_direction": "偏利好消费基金",
        "positive_types": "消费,食品饮料,白酒,家电",
        "negative_types": "短线追高资金",
        "impact_level": "中",
        "plain_explanation": "消费恢复会让相关公司预期变好，消费主题基金可能受益。但消费基金波动也不小，需要看估值和持仓。",
        "operation_reference": "已有持仓可继续观察，没买的人更适合分批而不是追涨。",
    },
    {
        "title": "债券市场波动加大，稳健产品需要关注久期风险",
        "source": "公开资讯整理",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": "利率变化会影响债券基金净值表现。",
        "original_text": "债券基金也会随着利率变化产生净值波动，长久期产品波动更明显。",
        "original_url": "",
        "impact_direction": "影响债券和稳健类基金",
        "positive_types": "短债,货币基金",
        "negative_types": "长债,高久期债券基金",
        "impact_level": "低",
        "plain_explanation": "债券基金不是完全不会跌，利率变化时也会有净值波动。稳健用户要注意产品持仓久期。",
        "operation_reference": "稳健资金可优先看短债或货币类，长债基金不适合盲目重仓。",
    },
]


_NEWS_CACHE: Dict[str, Any] = {}
_NEWS_CACHE_TS = 0.0
_NEWS_TTL = 240


def _row_value(row: Any, candidates: List[str], default: str = "") -> str:
    for key in candidates:
        try:
            value = row.get(key)
        except Exception:
            value = None
        if value not in (None, "", "-", "--", "nan"):
            return str(value)
    return default


def _append_rows_from_df(news: List[Dict[str, Any]], df: Any, source_name: str, limit: int) -> None:
    if df is None or getattr(df, "empty", True):
        return
    for _, row in df.head(limit).iterrows():
        title = _row_value(row, ["标题", "新闻标题", "title", "内容标题"])
        summary = _row_value(row, ["摘要", "新闻内容", "内容", "简介", "summary"], title)
        if not title:
            continue
        item = analyze_news_item(
            title=title,
            content=summary,
            source=_row_value(row, ["来源", "文章来源", "source"], source_name),
            published_at=_row_value(row, ["发布时间", "时间", "日期", "显示时间"], datetime.now().strftime("%Y-%m-%d %H:%M")),
            original_url=_row_value(row, ["链接", "网址", "新闻链接", "url", "URL"], ""),
        )
        news.append(item)


def _request_json_direct(url: str, params: Dict[str, Any] | None = None) -> Any:
    session = requests.Session()
    session.trust_env = False
    resp = session.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
    resp.raise_for_status()
    text = resp.text.strip()
    if text.startswith(("callback", "jQuery")):
        text = text[text.find("(") + 1 : text.rfind(")")]
    return json.loads(text)


def _fetch_sina_roll(limit: int) -> List[Dict[str, Any]]:
    rows = []
    for lid in ["2515", "2516", "2517"]:
        payload = _request_json_direct(
            "https://feed.mix.sina.com.cn/api/roll/get",
            {"pageid": "153", "lid": lid, "num": min(20, limit), "page": 1},
        )
        for row in (payload.get("result", {}).get("data") or [])[:limit]:
            rows.append(
                analyze_news_item(
                    title=str(row.get("title", "")),
                    content=str(row.get("intro") or row.get("keywords") or row.get("title", "")),
                    source="新浪财经公开资讯",
                    published_at=str(row.get("ctime") or datetime.now().strftime("%Y-%m-%d %H:%M")),
                    original_url=str(row.get("url") or ""),
                )
            )
    return rows


def _fetch_eastmoney_news(limit: int) -> List[Dict[str, Any]]:
    payload = _request_json_direct(
        "https://newsapi.eastmoney.com/kuaixun/v2/api/list",
        {"column": "102", "limit": limit},
    )
    rows = payload.get("data") or payload.get("LivesList") or payload.get("list") or []
    news = []
    for row in rows[:limit]:
        news.append(
            analyze_news_item(
                title=str(row.get("title") or row.get("digest") or row.get("content") or ""),
                content=str(row.get("digest") or row.get("content") or ""),
                source=str(row.get("source") or "东方财富公开快讯"),
                published_at=str(row.get("showtime") or row.get("time") or datetime.now().strftime("%Y-%m-%d %H:%M")),
                original_url=str(row.get("url") or row.get("news_url") or ""),
            )
        )
    return news


def _fallback_news(limit: int) -> List[Dict[str, Any]]:
    rows = []
    for item in SAMPLE_NEWS:
        copied = item.copy()
        copied["original_url"] = copied.get("original_url") or f"https://www.baidu.com/s?wd={quote_plus(copied['title'])}"
        copied["original_text"] = copied.get("original_text") or copied.get("summary") or copied["title"]
        rows.append(copied)
    for title, positive, negative in MORE_SAMPLE_TOPICS:
        rows.append(
            analyze_news_item(
                title=title,
                content=f"{title}。这是本地兜底资讯，用于公开资讯源异常时保持页面可读，实际使用时请以原文链接和公开数据源为准。",
                source="本地兜底资讯",
                published_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                original_url=f"https://www.baidu.com/s?wd={quote_plus(title)}",
            )
        )
        rows[-1]["positive_types"] = positive
        rows[-1]["negative_types"] = negative
    return rows[:limit]


def _load_with_timeout(loader, timeout: int = 5):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(loader)
    try:
        return future.result(timeout=timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def get_market_news(limit: int = 50, refresh: bool = False) -> Dict[str, Any]:
    global _NEWS_CACHE, _NEWS_CACHE_TS
    if _NEWS_CACHE and not refresh and time.time() - _NEWS_CACHE_TS < _NEWS_TTL:
        return _NEWS_CACHE

    news: List[Dict[str, Any]] = []
    errors: List[str] = []
    direct_sources = [
        ("新浪财经滚动资讯", lambda: _fetch_sina_roll(limit)),
        ("东方财富快讯", lambda: _fetch_eastmoney_news(limit)),
    ]
    for name, loader in direct_sources:
        try:
            news.extend(_load_with_timeout(loader, timeout=6))
        except TimeoutError:
            errors.append(f"{name} 响应超时，已跳过")
        except Exception as exc:
            errors.append(f"{name} 暂不可用：{exc}")

    ak, error = _load_akshare()
    if ak and len(news) < max(12, limit // 2):
        sources = [
            ("东方财富全球财经", lambda: ak.stock_info_global_em()),
            ("财联社快讯", lambda: ak.stock_info_global_cls(symbol="全部")),
            ("财新市场新闻", lambda: ak.stock_news_main_cx()),
            ("央视新闻", lambda: ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))),
        ]
        for name, loader in sources:
            try:
                _append_rows_from_df(news, _load_with_timeout(loader), name, max(8, limit // 2))
            except TimeoutError:
                errors.append(f"{name} 响应超时，已跳过")
            except Exception as exc:
                errors.append(f"{name} 暂不可用：{exc}")
    elif error:
        errors.append(error)

    deduped = []
    seen = set()
    for item in news:
        key = item["title"].strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    if len(deduped) < min(limit, 12):
        existing = {item["title"].strip() for item in deduped}
        deduped.extend([item for item in _fallback_news(limit) if item["title"].strip() not in existing])

    result = {
        "news": deduped[:limit],
        "errors": errors,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(deduped[:limit]),
    }
    _NEWS_CACHE = result
    _NEWS_CACHE_TS = time.time()
    return result


def analyze_news_item(
    title: str,
    content: str = "",
    source: str = "公开资讯",
    published_at: str = "",
    original_url: str = "",
) -> Dict[str, Any]:
    text = f"{title} {content}"
    positive: List[str] = []
    negative: List[str] = []
    direction = "需要观察"
    level = "中"

    rules = [
        (["科技", "人工智能", "AI", "半导体", "芯片", "算力", "数字"], ["科技", "人工智能", "半导体", "成长"], "偏利好科技成长基金"),
        (["消费", "食品", "白酒", "家电", "旅游", "零售"], ["消费", "食品饮料", "白酒", "家电"], "偏利好消费基金"),
        (["新能源", "光伏", "电池", "储能", "汽车", "电动车"], ["新能源", "光伏", "电池", "高端制造"], "偏利好新能源基金"),
        (["医药", "创新药", "医疗", "生物"], ["医药", "创新药", "医疗服务"], "偏利好医药基金"),
        (["红利", "央企", "高股息"], ["红利", "央企", "价值"], "偏利好红利价值基金"),
        (["债券", "利率", "降息", "货币"], ["短债", "货币基金", "债券"], "影响债券和稳健类基金"),
        (["黄金", "原油", "汇率", "美元"], ["黄金", "资源", "QDII"], "影响商品和海外基金"),
    ]
    for keys, tags, rule_direction in rules:
        if any(key in text for key in keys):
            positive.extend(tags)
            direction = rule_direction

    risk_keys = ["风险", "下跌", "监管", "亏损", "回调", "利空", "退潮", "高位"]
    if any(key in text for key in risk_keys):
        level = "高"
        negative.extend(["高波动主题基金", "短期追高基金"])
    if "债券" in text or "利率" in text:
        negative.extend(["长债", "高久期债券基金"])
    if not positive:
        positive.append("暂无明确方向")
    if not negative:
        negative.append("暂无明确方向")

    positive_text = ",".join(dict.fromkeys(positive))
    negative_text = ",".join(dict.fromkeys(negative))
    plain = (
        f"这条消息可能影响 {positive_text} 方向。普通用户可以先看自己的基金是否重仓相关行业，"
        "不要只因为一条新闻就重仓买入或立刻卖出。"
    )
    if level == "高":
        plain += " 这条消息带有较强风险信号，短期净值波动可能会变大。"

    safe_title = title or "市场资讯"
    return {
        "title": safe_title,
        "source": source or "公开资讯",
        "published_at": published_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": (content or safe_title)[:220],
        "original_text": content or safe_title,
        "original_url": original_url or f"https://www.baidu.com/s?wd={quote_plus(safe_title)}",
        "impact_direction": direction,
        "positive_types": positive_text,
        "negative_types": negative_text,
        "impact_level": level,
        "plain_explanation": plain,
        "operation_reference": "仅作为观察线索，请结合基金评分、估值位置、自己的仓位和风险承受能力一起判断。",
    }


def match_news_for_funds(news: List[Dict[str, Any]], funds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matched = []
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
            raw_terms = [
                fund.get("name", ""),
                fund.get("symbol", ""),
                fund.get("fund_type", ""),
                fund.get("industries", ""),
                fund.get("top_stocks", ""),
                fund.get("manager", ""),
                fund.get("company", ""),
            ]
            terms = []
            for part in raw_terms:
                terms.extend([term.strip() for term in str(part).replace("，", ",").split(",") if len(term.strip()) >= 2])
            hit_terms = [term for term in terms if term and term in news_text]
            if not hit_terms:
                continue
            effect = "利好" if any(term in item.get("positive_types", "") for term in hit_terms) else "观察"
            if any(term in item.get("negative_types", "") for term in hit_terms):
                effect = "利空/风险"
            matched.append(
                {
                    "news": item,
                    "fund": fund,
                    "reason": f"匹配到：{','.join(hit_terms[:6])}",
                    "effect": effect,
                    "nav_impact": "短期净值可能跟随相关行业情绪波动，实际表现还要看基金真实持仓和市场走势。",
                    "decision_hint": "先观察评分、仓位和近期涨跌，不建议只根据单条新闻买卖。",
                    "plain_explanation": f"这条资讯和 {fund.get('name')} 可能有关，因为它提到了基金名称、类型、行业或重仓线索。",
                }
            )
    return matched
