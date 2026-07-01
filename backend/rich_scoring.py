from __future__ import annotations

from typing import Any


DISCLAIMER = "仅供学习和模拟研究，不构成投资建议；系统不会做真实交易。"


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(str(value).replace("%", "").replace(",", "").strip())
    except Exception:
        return default


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def _positive_score(value: float, good: float, points: float) -> float:
    return _clamp(value / good * points, 0, points)


def _drawdown_score(drawdown: float) -> float:
    dd = abs(drawdown)
    if dd <= 8:
        return 15
    if dd <= 15:
        return 12
    if dd <= 25:
        return 8
    if dd <= 35:
        return 5
    return 2


def _is_missing(value: Any) -> bool:
    return str(value or "").strip() in {"", "资料待补全", "暂无数据", "公开数据暂缺", "None", "null"}


def score_fund(fund: dict[str, Any], news_heat: float = 3.0) -> dict[str, Any]:
    year_return = _num(fund.get("year_return"))
    three_year_return = _num(fund.get("three_year_return"))
    month_return = _num(fund.get("month_return"))
    max_drawdown = _num(fund.get("max_drawdown"))
    sharpe = _num(fund.get("sharpe_ratio"))
    size = _num(fund.get("fund_size"))
    daily_change = _num(fund.get("daily_change"))
    industries = str(fund.get("industries") or "")

    income = _positive_score(year_return, 25, 12) + _positive_score(three_year_return, 60, 8)
    stability = _positive_score(sharpe, 1.2, 10) + (5 if abs(month_return) <= 8 else 2)
    drawdown = _drawdown_score(max_drawdown)
    manager = 12 if not _is_missing(fund.get("manager")) else 8
    if three_year_return > 15:
        manager += 2
    size_score = 10 if size == 0 or 20 <= size <= 200 else 7 if 5 <= size <= 500 else 4
    industry_score = 8 if any(key in industries for key in ["科技", "人工智能", "半导体", "新能源", "医药", "消费", "红利"]) else 6
    valuation = 8 if max_drawdown <= -15 and daily_change < 1.5 else 5 if daily_change < 3 else 3
    news = _clamp(news_heat, 0, 5)

    dimensions = [
        {"name": "收益能力", "score": round(income, 1), "max": 20, "explain": "看近一年和近三年表现，正收益越稳定越好。"},
        {"name": "稳定性", "score": round(stability, 1), "max": 15, "explain": "看波动和夏普比率，波动太大分数会降低。"},
        {"name": "回撤控制", "score": round(drawdown, 1), "max": 15, "explain": "跌得越深，普通用户越难拿住。"},
        {"name": "基金经理", "score": round(_clamp(manager, 0, 15), 1), "max": 15, "explain": "有基金经理和中长期业绩时加分，资料缺失时保守给分。"},
        {"name": "规模合理", "score": round(size_score, 1), "max": 10, "explain": "规模过小有清盘风险，过大可能影响灵活性。"},
        {"name": "行业景气", "score": round(industry_score, 1), "max": 10, "explain": "结合持仓行业是否处于市场关注方向。"},
        {"name": "估值位置", "score": round(valuation, 1), "max": 10, "explain": "回撤后分批更稳，短期涨太快会扣分。"},
        {"name": "资讯影响", "score": round(news, 1), "max": 5, "explain": "热点和政策只做小权重参考。"},
    ]
    total = round(sum(item["score"] for item in dimensions), 1)
    if total >= 80:
        grade = "优秀"
    elif total >= 68:
        grade = "良好"
    elif total >= 55:
        grade = "一般"
    else:
        grade = "谨慎"

    latest_nav = _num(fund.get("latest_nav"), 1.0) or 1.0
    return {
        "symbol": fund.get("symbol"),
        "name": fund.get("name"),
        "total_score": total,
        "grade": grade,
        "dimensions": dimensions,
        "suitability": "适合能接受净值波动、愿意分批操作的人；新手建议先小额观察。",
        "action": "结合买入/持有/卖出指数判断",
        "buy_reason": "评分、回撤、估值位置和资讯方向同时改善时，才考虑小额分批，不建议一次性重仓。",
        "risk_note": "基金净值会波动，评分下降、行业转弱、短期涨幅过大或资讯转弱时要谨慎。",
        "buy_range": f"{latest_nav * 0.94:.3f} - {latest_nav * 1.00:.3f}",
        "take_profit_range": f"{latest_nav * 1.12:.3f} - {latest_nav * 1.20:.3f}",
        "stop_loss_range": f"{latest_nav * 0.86:.3f} - {latest_nav * 0.90:.3f}",
        "holding_period": "更适合中长期观察，不建议频繁追涨杀跌。",
        "disclaimer": DISCLAIMER,
    }


def recommendation_index(
    fund: dict[str, Any],
    related_news: list[dict[str, Any]] | None = None,
    position: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = score_fund(fund)
    total = _num(score["total_score"])
    daily_change = _num(fund.get("daily_change"))
    week_return = _num(fund.get("week_return"))
    month_return = _num(fund.get("month_return"))
    max_drawdown = _num(fund.get("max_drawdown"))
    sharpe = _num(fund.get("sharpe_ratio"))
    latest_nav = _num(fund.get("latest_nav"))
    related_news = related_news or []

    positive_news = sum(1 for item in related_news if "利好" in str(item.get("effect", "")))
    risk_news = sum(1 for item in related_news if any(k in str(item.get("effect", "")) for k in ["风险", "利空"]))
    profit_rate = _num((position or {}).get("profit_rate")) if position else 0.0

    evidence: list[str] = []
    risk_flags: list[str] = []
    if total >= 68:
        evidence.append(f"综合评分 {total:.1f} 分，基础质量较好")
    else:
        risk_flags.append(f"综合评分 {total:.1f} 分，还不算强")
    if max_drawdown <= -12:
        evidence.append(f"最大回撤 {max_drawdown:.1f}%，已经有一定回撤，适合观察分批机会")
    if max_drawdown <= -30:
        risk_flags.append(f"最大回撤 {max_drawdown:.1f}%，波动很大")
    if month_return > 12:
        risk_flags.append(f"近1月涨幅 {month_return:.1f}%，短期偏热，不适合追高")
    elif month_return < -6:
        evidence.append(f"近1月回撤 {month_return:.1f}%，如果基本面没变坏，可进入观察区")
    if daily_change > 3:
        risk_flags.append(f"单日涨幅 {daily_change:.1f}%，短线追高风险升高")
    if sharpe > 0.8:
        evidence.append(f"夏普比率 {sharpe:.2f}，波动收益比相对更好")
    if positive_news:
        evidence.append(f"匹配到 {positive_news} 条偏利好资讯")
    if risk_news:
        risk_flags.append(f"匹配到 {risk_news} 条风险资讯")
    if position:
        if profit_rate >= 15:
            risk_flags.append(f"你的持仓收益率 {profit_rate:.1f}%，已进入止盈观察区")
        elif profit_rate <= -10:
            risk_flags.append(f"你的持仓收益率 {profit_rate:.1f}%，需要复查是否继续持有")
        else:
            evidence.append(f"你的持仓收益率 {profit_rate:.1f}%，暂未触发极端止盈/止损")
    if not evidence:
        evidence.append("公开数据没有出现足够强的加仓信号")

    buy_index = total
    if max_drawdown <= -12:
        buy_index += 8
    if month_return < -6:
        buy_index += 6
    if positive_news:
        buy_index += positive_news * 4
    if month_return > 12 or daily_change > 3:
        buy_index -= 18
    if risk_news:
        buy_index -= risk_news * 8
    if total < 60:
        buy_index = min(buy_index, 62)

    sell_index = 100 - total
    if month_return > 12:
        sell_index += 12
    if daily_change > 3:
        sell_index += 10
    if max_drawdown <= -30:
        sell_index += 10
    if risk_news:
        sell_index += risk_news * 10
    if position and profit_rate >= 15:
        sell_index += 18
    if position and profit_rate <= -12 and total < 60:
        sell_index += 12

    hold_index = 70 - abs(total - 70) * 0.45
    if 55 <= total <= 82:
        hold_index += 12
    if position and -10 < profit_rate < 15:
        hold_index += 6
    hold_index += positive_news * 2 - risk_news * 4

    buy_index = round(_clamp(buy_index), 1)
    hold_index = round(_clamp(hold_index), 1)
    sell_index = round(_clamp(sell_index), 1)

    if sell_index >= 72:
        action = "减仓/止盈观察"
        reason = f"减仓理由：卖出/减仓指数 {sell_index:.1f}，主要因为 {'；'.join(risk_flags[:3])}。"
    elif buy_index >= 72 and sell_index < 58:
        action = "小额分批加仓"
        reason = f"加仓理由：买入指数 {buy_index:.1f}，主要因为 {'；'.join(evidence[:3])}。仍建议分批，不要一次性重仓。"
    elif hold_index >= 65:
        action = "持有观察"
        reason = f"持有理由：持有指数 {hold_index:.1f}，当前证据支持继续观察，核心依据是 {'；'.join(evidence[:3])}。"
    else:
        action = "观望"
        reason = f"观望理由：买入指数 {buy_index:.1f}、卖出/减仓指数 {sell_index:.1f}，信号不够明确；主要风险是 {'；'.join(risk_flags[:3]) or '数据证据不足'}。"

    return {
        "buy_index": buy_index,
        "hold_index": hold_index,
        "sell_index": sell_index,
        "action": action,
        "plain_explanation": reason,
        "reason_sentence": reason,
        "evidence": evidence,
        "risk_flags": risk_flags,
        "reasons": evidence + risk_flags,
        "score": total,
        "grade": score["grade"],
        "latest_nav": latest_nav,
        "disclaimer": DISCLAIMER,
    }


def recommendation_buckets(funds: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    for fund in funds:
        score = score_fund(fund)
        advice = recommendation_index(fund)
        row = {
            "symbol": fund.get("symbol"),
            "name": fund.get("name"),
            "score": score["total_score"],
            "grade": score["grade"],
            "reason": advice["reason_sentence"],
            "risk": "；".join(advice.get("risk_flags", [])[:2]) or score["risk_note"],
            "action": advice["action"],
            "buy_index": advice["buy_index"],
            "hold_index": advice["hold_index"],
            "sell_index": advice["sell_index"],
            "evidence": advice["evidence"],
            "risk_flags": advice["risk_flags"],
            "trend": fund.get("history", [])[-45:],
            "latest_nav": fund.get("latest_nav"),
            "daily_change": fund.get("daily_change"),
            "month_return": fund.get("month_return"),
            "cycle": score["holding_period"],
            "hot_news": "关注政策、行业景气度和市场情绪变化。",
            "disclaimer": DISCLAIMER,
        }
        scored.append(row)

    high = sorted(scored, key=lambda item: (item["buy_index"], item["score"]), reverse=True)
    hold = sorted(scored, key=lambda item: item["hold_index"], reverse=True)
    risk = sorted(scored, key=lambda item: item["sell_index"], reverse=True)
    low_valuation = [item for item in high if item["buy_index"] >= 60 and item["sell_index"] < 65]
    return {
        "today": high[:5],
        "week": high[:8],
        "undervalued": low_valuation[:6],
        "growth": high[:6],
        "stable": hold[:6],
        "aggressive": [item for item in high if item["buy_index"] >= 70][:6],
        "beginner": [item for item in hold if item["sell_index"] < 65][:6],
        "avoid_chasing": risk[:6],
        "disclaimer": DISCLAIMER,
    }
