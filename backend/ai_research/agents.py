from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev
from typing import Any

import rich_scoring

from .models import AgentOpinion


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except Exception:
        return default


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _direction(score: float) -> str:
    if score >= 65:
        return "positive"
    if score < 45:
        return "negative"
    return "neutral"


def _history(fund: dict[str, Any]) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for item in fund.get("history") or []:
        nav = _num(item.get("nav") or item.get("unit_nav") or item.get("close"))
        date = str(item.get("date") or item.get("trade_date") or item.get("nav_date") or "")[:10]
        if date and nav > 0:
            rows.append((date, nav))
    return sorted(dict(rows).items())


def technical_agent(fund: dict[str, Any]) -> AgentOpinion:
    rows = _history(fund)
    missing: list[str] = []
    if len(rows) < 60:
        missing.append("不足 60 条有效净值，趋势判断可信度较低")
    navs = [nav for _, nav in rows]
    if not navs:
        return AgentOpinion("technical", "趋势 Agent", "净值趋势与动量", 40, "negative", "缺少有效净值，暂不判断趋势", missing_data=["历史净值"])

    short = mean(navs[-min(20, len(navs)):])
    long = mean(navs[-min(60, len(navs)):])
    latest = navs[-1]
    month_base = navs[-min(21, len(navs))]
    momentum = (latest / month_base - 1) * 100 if month_base else 0
    peak = max(navs[-min(120, len(navs)):])
    drawdown = (latest / peak - 1) * 100 if peak else 0
    score = 50 + (12 if short > long else -12) + max(-15, min(15, momentum * 1.2))
    if drawdown <= -15:
        score -= 8
    evidence = [
        f"最新净值 {latest:.4f}，20 日均值 {short:.4f}，60 日均值 {long:.4f}",
        f"近约 1 月变化 {momentum:.2f}%",
        f"距近 120 日高点 {drawdown:.2f}%",
    ]
    summary = "中期趋势偏强" if score >= 65 else "趋势偏弱，先观察" if score < 45 else "趋势没有形成明显优势"
    return AgentOpinion("technical", "趋势 Agent", "净值趋势与动量", _clamp(score), _direction(score), summary, evidence, missing_data=missing)


def quality_agent(fund: dict[str, Any]) -> AgentOpinion:
    scoring = rich_scoring.score_fund(fund)
    score = _num(scoring.get("total_score"), 50)
    evidence = [
        f"基础评分 {score:.1f}/100，等级 {scoring.get('grade', '暂无')}",
        f"近 1 年收益 {_num(fund.get('year_return')):.2f}%",
        f"最大回撤 {_num(fund.get('max_drawdown')):.2f}%，夏普比率 {_num(fund.get('sharpe_ratio')):.2f}",
    ]
    missing = []
    for key, label in (("manager", "基金经理"), ("fund_size", "基金规模"), ("company", "基金公司")):
        if str(fund.get(key) or "") in {"", "资料待补全", "暂无数据", "公开数据暂缺"}:
            missing.append(label)
    summary = "基金质量和长期指标较好" if score >= 68 else "基础质量一般，需要更多证据" if score >= 55 else "基础质量偏弱"
    return AgentOpinion("quality", "质量 Agent", "收益、回撤、经理与规模", _clamp(score), _direction(score), summary, evidence, missing_data=missing)


def sentiment_agent(fund: dict[str, Any], related_news: list[dict[str, Any]]) -> AgentOpinion:
    positive = sum(1 for item in related_news if item.get("effect") == "利好")
    negative = sum(1 for item in related_news if item.get("effect") == "风险")
    score = 50 + positive * 9 - negative * 12
    evidence = [f"匹配资讯 {len(related_news)} 条：偏利好 {positive} 条，风险 {negative} 条"]
    evidence.extend(str(item.get("news", {}).get("title")) for item in related_news[:3] if item.get("news", {}).get("title"))
    missing = [] if related_news else ["暂未匹配到和该基金直接相关的公开资讯"]
    summary = "资讯情绪偏正面" if score >= 65 else "资讯风险偏高" if score < 45 else "资讯面暂时中性"
    return AgentOpinion("sentiment", "资讯 Agent", "新闻、政策与市场情绪", _clamp(score), _direction(score), summary, evidence, missing_data=missing)


def macro_agent(fund: dict[str, Any], market_news: list[dict[str, Any]]) -> AgentOpinion:
    industries = str(fund.get("industries") or fund.get("fund_type") or "")
    terms = [term for term in ["科技", "人工智能", "半导体", "新能源", "医药", "消费", "红利", "黄金", "债券", "港股"] if term in industries]
    positive = 0
    negative = 0
    matched_titles: list[str] = []
    for item in market_news:
        text = f"{item.get('positive_types', '')} {item.get('negative_types', '')} {item.get('title', '')}"
        if terms and not any(term in text for term in terms):
            continue
        matched_titles.append(str(item.get("title") or ""))
        if any(term in str(item.get("positive_types", "")) for term in terms):
            positive += 1
        if any(term in str(item.get("negative_types", "")) for term in terms):
            negative += 1
    score = 50 + min(18, positive * 3) - min(24, negative * 5)
    evidence = [f"识别行业线索：{'、'.join(terms) if terms else '暂无明确行业标签'}", f"行业相关资讯：正面 {positive}，风险 {negative}"]
    evidence.extend(title for title in matched_titles[:2] if title)
    missing = [] if terms else ["基金行业标签不足，宏观匹配只能保守处理"]
    summary = "行业与宏观环境偏支持" if score >= 65 else "行业风险需要警惕" if score < 45 else "宏观行业信号中性"
    return AgentOpinion("macro", "宏观 Agent", "政策、行业景气与跨市场影响", _clamp(score), _direction(score), summary, evidence, missing_data=missing)


def risk_agent(fund: dict[str, Any], source_errors: list[Any]) -> AgentOpinion:
    rows = _history(fund)
    returns = [(rows[i][1] / rows[i - 1][1] - 1) for i in range(1, len(rows)) if rows[i - 1][1] > 0]
    annual_vol = pstdev(returns) * sqrt(250) * 100 if len(returns) >= 2 else 0
    max_drawdown = abs(_num(fund.get("max_drawdown")))
    if max_drawdown == 0 and rows:
        peak = rows[0][1]
        max_drawdown = 0
        for _, nav in rows:
            peak = max(peak, nav)
            max_drawdown = max(max_drawdown, (peak - nav) / peak * 100)
    score = 85 - max_drawdown * 1.35 - max(0, annual_vol - 12) * 0.8 - min(20, len(source_errors) * 8)
    risks = []
    if max_drawdown >= 25:
        risks.append("历史最大回撤较深，持有体验可能很差")
    if annual_vol >= 25:
        risks.append("年化波动较高，不适合一次性重仓")
    if source_errors:
        risks.append("部分公开数据源异常，结论可信度需要下调")
    evidence = [f"历史最大回撤约 {max_drawdown:.2f}%", f"净值年化波动约 {annual_vol:.2f}%", f"数据源异常 {len(source_errors)} 项"]
    summary = "风险处于可观察范围" if score >= 65 else "风险中等，必须控制仓位" if score >= 45 else "风险较高，不宜激进操作"
    return AgentOpinion("risk", "风控 Agent", "回撤、波动、仓位与数据质量", _clamp(score), _direction(score), summary, evidence, risks=risks)

