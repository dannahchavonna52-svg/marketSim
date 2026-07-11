from __future__ import annotations

from typing import Any

from .models import AgentOpinion


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except Exception:
        return default


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _direction(score: float) -> str:
    return "positive" if score >= 65 else "negative" if score < 45 else "neutral"


def value_balance_style(fund: dict[str, Any]) -> AgentOpinion:
    year_return = _num(fund.get("year_return"))
    drawdown = abs(_num(fund.get("max_drawdown")))
    sharpe = _num(fund.get("sharpe_ratio"))
    size = _num(fund.get("fund_size"))
    score = 55 + min(14, max(-12, year_return * 0.45)) + min(14, sharpe * 9) - max(0, drawdown - 15) * 0.8
    if size and not 5 <= size <= 500:
        score -= 8
    score = _clamp(score)
    return AgentOpinion(
        "style_value_balance",
        "价值均衡风格",
        "重视安全边际、回撤与长期持有体验",
        score,
        _direction(score),
        "估值与风险收益比较均衡" if score >= 65 else "安全边际还不够明显" if score < 45 else "可以观察，但不适合激进追高",
        [f"近 1 年收益 {year_return:.2f}%", f"最大回撤 {drawdown:.2f}%", f"夏普比率 {sharpe:.2f}", f"基金规模 {size:.2f} 亿元"],
        ["短期收益不是核心，若回撤控制恶化会快速降低评价"],
    )


def industry_growth_style(fund: dict[str, Any]) -> AgentOpinion:
    month_return = _num(fund.get("month_return"))
    year_return = _num(fund.get("year_return"))
    industries = str(fund.get("industries") or fund.get("fund_type") or "")
    growth_terms = [term for term in ["科技", "人工智能", "半导体", "新能源", "医药", "高端制造"] if term in industries]
    score = 48 + min(20, max(-18, year_return * 0.55)) + min(14, max(-14, month_return * 0.7)) + min(12, len(growth_terms) * 4)
    if month_return > 15:
        score -= 16
    score = _clamp(score)
    return AgentOpinion(
        "style_industry_growth",
        "产业成长风格",
        "关注产业趋势、成长空间与政策方向",
        score,
        _direction(score),
        "产业趋势和成长动量较强" if score >= 65 else "成长线索偏弱" if score < 45 else "产业方向可跟踪，但需要等待更好位置",
        [f"识别成长行业：{'、'.join(growth_terms) if growth_terms else '暂无'}", f"近 1 月收益 {month_return:.2f}%", f"近 1 年收益 {year_return:.2f}%"],
        ["成长风格波动通常较大，近月涨幅过高时会主动降低评价"],
        missing_data=[] if growth_terms else ["基金行业标签不足"],
    )


def contrarian_drawdown_style(fund: dict[str, Any]) -> AgentOpinion:
    month_return = _num(fund.get("month_return"))
    drawdown = abs(_num(fund.get("max_drawdown")))
    year_return = _num(fund.get("year_return"))
    score = 50
    if -15 <= month_return <= -4:
        score += 18
    elif month_return > 12:
        score -= 20
    if 10 <= drawdown <= 25:
        score += 12
    elif drawdown > 35:
        score -= 18
    if year_return < -20:
        score -= 12
    score = _clamp(score)
    return AgentOpinion(
        "style_contrarian",
        "逆向回撤风格",
        "寻找非基本面恶化造成的回撤机会",
        score,
        _direction(score),
        "回撤进入逆向观察区" if score >= 65 else "下跌可能不是机会，先排查基本面" if score < 45 else "回撤程度一般，继续等待证据",
        [f"近 1 月收益 {month_return:.2f}%", f"历史最大回撤 {drawdown:.2f}%", f"近 1 年收益 {year_return:.2f}%"],
        ["逆向不等于抄底，长期业绩恶化或深度回撤会被视为风险"],
    )


def run_style_models(fund: dict[str, Any]) -> list[AgentOpinion]:
    return [value_balance_style(fund), industry_growth_style(fund), contrarian_drawdown_style(fund)]

