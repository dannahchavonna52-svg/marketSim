from typing import Any, Dict, List


DISCLAIMER = "仅供学习和模拟研究，不构成投资建议。"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _score_positive(value: float, best: float, points: float) -> float:
    return _clamp(value / best * points, 0, points)


def _score_drawdown(drawdown: float) -> float:
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


def score_fund(fund: Dict[str, Any], news_heat: float = 3.0) -> Dict[str, Any]:
    year_return = float(fund.get("year_return") or 0)
    three_year_return = float(fund.get("three_year_return") or 0)
    month_return = float(fund.get("month_return") or 0)
    max_drawdown = float(fund.get("max_drawdown") or 0)
    sharpe = float(fund.get("sharpe_ratio") or 0)
    size = float(fund.get("fund_size") or 0)
    daily_change = float(fund.get("daily_change") or 0)

    income = _clamp(_score_positive(year_return, 25, 12) + _score_positive(three_year_return, 60, 8), 0, 20)
    stability = _clamp(_score_positive(sharpe, 1.2, 10) + (5 if abs(month_return) <= 8 else 2), 0, 15)
    drawdown = _score_drawdown(max_drawdown)
    manager = 10 if fund.get("manager") and fund.get("manager") != "暂无数据" else 7
    manager += 3 if three_year_return > 15 else 1
    size_score = 10 if 20 <= size <= 200 else 7 if 5 <= size <= 500 else 4
    industry = 8 if any(key in str(fund.get("industries", "")) for key in ["科技", "新能源", "医药", "消费"]) else 6
    valuation = 8 if max_drawdown <= -15 and daily_change < 1.5 else 5 if daily_change < 3 else 3
    news = _clamp(news_heat, 0, 5)

    dimensions = [
        {"name": "收益能力", "score": round(income, 1), "max": 20, "explain": "看近一年和近三年表现，越稳定跑出正收益越好。"},
        {"name": "稳定性", "score": round(stability, 1), "max": 15, "explain": "看波动和夏普比率，波动太大分数会降低。"},
        {"name": "回撤控制", "score": round(drawdown, 1), "max": 15, "explain": "跌得越深，普通用户越难拿得住。"},
        {"name": "基金经理能力", "score": round(manager, 1), "max": 15, "explain": "目前公开数据不足时采用保守评分。"},
        {"name": "规模合理性", "score": round(size_score, 1), "max": 10, "explain": "规模过小有清盘风险，过大也可能影响灵活性。"},
        {"name": "行业景气度", "score": round(industry, 1), "max": 10, "explain": "结合持仓行业是否处在市场关注方向。"},
        {"name": "估值位置", "score": round(valuation, 1), "max": 10, "explain": "回撤后分批关注更稳，短期涨太快会扣分。"},
        {"name": "资讯热度与政策影响", "score": round(news, 1), "max": 5, "explain": "热点和政策有帮助，但只占小权重。"},
    ]
    total = round(sum(item["score"] for item in dimensions), 1)

    if total >= 80:
        grade, action = "优秀", "分批买入 / 持有"
    elif total >= 68:
        grade, action = "良好", "少量买入 / 持有"
    elif total >= 55:
        grade, action = "一般", "观望 / 小额试探"
    else:
        grade, action = "谨慎", "暂不追高 / 降低仓位"

    if daily_change > 3:
        action = "短期上涨过快，注意回撤"
    if max_drawdown < -30:
        action = "波动较大，只适合小仓位观察"

    latest_nav = float(fund.get("latest_nav") or 1)
    return {
        "symbol": fund.get("symbol"),
        "name": fund.get("name"),
        "total_score": total,
        "grade": grade,
        "dimensions": dimensions,
        "suitability": "适合能接受净值波动、愿意分批买入的人；新手建议先小额观察。",
        "action": action,
        "buy_reason": "如果基金方向和你的风险承受能力匹配，可以用分批方式降低买在高点的风险。",
        "risk_note": "基金净值会波动，评分下降、行业转弱或短期涨幅过大时要谨慎。",
        "buy_range": f"{latest_nav * 0.94:.3f} - {latest_nav * 1.00:.3f}",
        "take_profit_range": f"{latest_nav * 1.12:.3f} - {latest_nav * 1.20:.3f}",
        "stop_loss_range": f"{latest_nav * 0.86:.3f} - {latest_nav * 0.90:.3f}",
        "holding_period": "更适合中长期持有，不建议频繁追涨杀跌。",
        "disclaimer": DISCLAIMER,
    }


def recommendation_buckets(funds: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = []
    for fund in funds:
        score = score_fund(fund)
        scored.append(
            {
                "symbol": fund["symbol"],
                "name": fund["name"],
                "score": score["total_score"],
                "grade": score["grade"],
                "reason": score["buy_reason"],
                "risk": score["risk_note"],
                "action": score["action"],
                "cycle": score["holding_period"],
                "hot_news": "关注政策、行业景气度和市场情绪变化。",
                "disclaimer": DISCLAIMER,
            }
        )

    high = sorted(scored, key=lambda item: item["score"], reverse=True)
    low = sorted(scored, key=lambda item: item["score"])
    return {
        "today": high[:3],
        "week": high[:5],
        "undervalued": [item for item in high if "观察" in item["action"] or item["score"] >= 60][:4],
        "growth": high[:4],
        "stable": [item for item in high if item["score"] >= 65][:4],
        "aggressive": [item for item in high if item["score"] >= 70][:4],
        "beginner": [item for item in high if item["score"] >= 60][:4],
        "avoid_chasing": low[:3],
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# UTF-8 scoring implementation, appended to override the early prototype.
# The output is an explainable simulation score, not investment advice.
# ---------------------------------------------------------------------------

DISCLAIMER = "仅供学习和模拟研究，不构成投资建议。"


def score_fund(fund: Dict[str, Any], news_heat: float = 3.0) -> Dict[str, Any]:
    year_return = float(fund.get("year_return") or 0)
    three_year_return = float(fund.get("three_year_return") or 0)
    month_return = float(fund.get("month_return") or 0)
    max_drawdown = float(fund.get("max_drawdown") or 0)
    sharpe = float(fund.get("sharpe_ratio") or 0)
    size = float(fund.get("fund_size") or 0)
    daily_change = float(fund.get("daily_change") or 0)

    income = _clamp(_score_positive(year_return, 25, 12) + _score_positive(three_year_return, 60, 8), 0, 20)
    stability = _clamp(_score_positive(sharpe, 1.2, 10) + (5 if abs(month_return) <= 8 else 2), 0, 15)
    drawdown = _score_drawdown(max_drawdown)
    manager_name = str(fund.get("manager") or "")
    manager = 10 if manager_name and manager_name not in {"公开数据暂缺", "资料待补全", "暂无数据"} else 7
    manager += 3 if three_year_return > 15 else 1
    size_score = 10 if size == 0 or 20 <= size <= 200 else 7 if 5 <= size <= 500 else 4
    industry = 8 if any(key in str(fund.get("industries", "")) for key in ["科技", "新能源", "医药", "消费", "半导体", "人工智能"]) else 6
    valuation = 8 if max_drawdown <= -15 and daily_change < 1.5 else 5 if daily_change < 3 else 3
    news = _clamp(news_heat, 0, 5)

    dimensions = [
        {"name": "收益能力", "score": round(income, 1), "max": 20, "explain": "看近一年和近三年表现，越稳定跑出正收益越好。"},
        {"name": "稳定性", "score": round(stability, 1), "max": 15, "explain": "看波动和夏普比率，波动太大分数会降低。"},
        {"name": "回撤控制", "score": round(drawdown, 1), "max": 15, "explain": "跌得越深，普通用户越难拿得住。"},
        {"name": "基金经理能力", "score": round(manager, 1), "max": 15, "explain": "公开数据不足时采用保守评分。"},
        {"name": "规模合理性", "score": round(size_score, 1), "max": 10, "explain": "规模过小有清盘风险，过大也可能影响灵活性。"},
        {"name": "行业景气度", "score": round(industry, 1), "max": 10, "explain": "结合持仓行业是否处在市场关注方向。"},
        {"name": "估值位置", "score": round(valuation, 1), "max": 10, "explain": "回撤后分批关注更稳，短期涨太快会扣分。"},
        {"name": "资讯热度与政策影响", "score": round(news, 1), "max": 5, "explain": "热点和政策有帮助，但只占小权重。"},
    ]
    total = round(sum(item["score"] for item in dimensions), 1)

    if total >= 80:
        grade, action = "优秀", "分批买入 / 持有"
    elif total >= 68:
        grade, action = "良好", "少量买入 / 持有"
    elif total >= 55:
        grade, action = "一般", "观望 / 小额试探"
    else:
        grade, action = "谨慎", "暂不追高 / 降低仓位"
    if daily_change > 3:
        action = "短期上涨过快，注意回撤"
    if max_drawdown < -30:
        action = "波动较大，只适合小仓位观察"

    latest_nav = float(fund.get("latest_nav") or 1)
    return {
        "symbol": fund.get("symbol"),
        "name": fund.get("name"),
        "total_score": total,
        "grade": grade,
        "dimensions": dimensions,
        "suitability": "适合能接受净值波动、愿意分批买入的人；新手建议先小额观察。",
        "action": action,
        "buy_reason": "如果基金方向和你的风险承受能力匹配，可以用分批方式降低买在高点的风险。",
        "risk_note": "基金净值会波动，评分下降、行业转弱或短期涨幅过大时要谨慎。",
        "buy_range": f"{latest_nav * 0.94:.3f} - {latest_nav * 1.00:.3f}",
        "take_profit_range": f"{latest_nav * 1.12:.3f} - {latest_nav * 1.20:.3f}",
        "stop_loss_range": f"{latest_nav * 0.86:.3f} - {latest_nav * 0.90:.3f}",
        "holding_period": "更适合中长期持有，不建议频繁追涨杀跌。",
        "disclaimer": DISCLAIMER,
    }


def recommendation_index(fund: Dict[str, Any], related_news: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    score = score_fund(fund)
    total = float(score["total_score"])
    daily_change = float(fund.get("daily_change") or 0)
    month_return = float(fund.get("month_return") or 0)
    max_drawdown = float(fund.get("max_drawdown") or 0)
    related_news = related_news or []

    positive_news = sum(1 for item in related_news if "利好" in str(item.get("effect", "")))
    negative_news = sum(1 for item in related_news if "利空" in str(item.get("effect", "")) or "风险" in str(item.get("effect", "")))
    news_adjust = positive_news * 5 - negative_news * 8

    buy_index = total + news_adjust
    if max_drawdown <= -12:
        buy_index += 8
    if daily_change > 3 or month_return > 12:
        buy_index -= 18
    if total < 60:
        buy_index = min(buy_index, 62)

    sell_index = 100 - total + negative_news * 8
    if daily_change > 3:
        sell_index += 10
    if month_return > 15:
        sell_index += 12
    if max_drawdown < -30:
        sell_index += 10

    hold_index = 70 - abs(total - 70) * 0.45
    if 55 <= total <= 82:
        hold_index += 12
    hold_index += positive_news * 3 - negative_news * 3

    buy_index = round(_clamp(buy_index, 0, 100), 1)
    hold_index = round(_clamp(hold_index, 0, 100), 1)
    sell_index = round(_clamp(sell_index, 0, 100), 1)

    if total < 60 and sell_index < 70:
        action = "观望"
        simple = "综合评分还不够高，先观察净值和资讯变化，不急着买。"
    elif sell_index >= 70:
        action = "卖出/止盈观察"
        simple = "短期风险信号偏多，适合先减仓或观察，不建议继续追高。"
    elif buy_index >= 72 and sell_index < 55:
        action = "小额分批买入"
        simple = "评分和位置相对可以，但仍建议分批，不要一次性重仓。"
    elif hold_index >= 65:
        action = "持有观察"
        simple = "当前更适合继续观察，不建议频繁操作。"
    else:
        action = "观望"
        simple = "信号不够明确，先看后续净值和资讯变化。"

    reasons = []
    if total >= 68:
        reasons.append("综合评分较高")
    if max_drawdown <= -12:
        reasons.append("近期有一定回撤，分批关注更合适")
    if daily_change > 3 or month_return > 12:
        reasons.append("短期涨幅偏快，追高风险上升")
    if positive_news:
        reasons.append(f"匹配到 {positive_news} 条偏利好资讯")
    if negative_news:
        reasons.append(f"匹配到 {negative_news} 条风险资讯")
    if not reasons:
        reasons.append("公开数据暂未出现特别强的买卖信号")

    if total < 60 and sell_index < 70:
        reason_sentence = f"买入判断：先观望，因为综合评分只有 {total:.1f} 分，买入信号还不够强。"
    elif buy_index >= 72 and sell_index < 55:
        reason_sentence = f"买入判断：可以买一点点分批试，因为综合评分 {total:.1f} 分、买入指数 {buy_index:.1f}，但仍要控制仓位。"
    elif sell_index >= 70:
        reason_sentence = f"买入判断：暂不适合买入，因为卖出/风险指数达到 {sell_index:.1f}，短期波动或追高风险偏大。"
    elif hold_index >= 65:
        reason_sentence = f"买入判断：更适合持有观察，因为持有指数 {hold_index:.1f}，信号不支持一次性重仓。"
    else:
        reason_sentence = f"买入判断：先观望，因为买入指数 {buy_index:.1f} 还不够强，需要等净值和资讯继续确认。"

    return {
        "buy_index": buy_index,
        "hold_index": hold_index,
        "sell_index": sell_index,
        "action": action,
        "plain_explanation": simple,
        "reason_sentence": reason_sentence,
        "reasons": reasons,
        "score": total,
        "grade": score["grade"],
        "disclaimer": DISCLAIMER,
    }


def recommendation_buckets(funds: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = []
    for fund in funds:
        score = score_fund(fund)
        advice = recommendation_index(fund)
        scored.append(
            {
                "symbol": fund["symbol"],
                "name": fund["name"],
                "score": score["total_score"],
                "grade": score["grade"],
                "reason": score["buy_reason"],
                "risk": score["risk_note"],
                "action": advice["action"],
                "buy_index": advice["buy_index"],
                "hold_index": advice["hold_index"],
                "sell_index": advice["sell_index"],
                "trend": fund.get("history", [])[-45:],
                "latest_nav": fund.get("latest_nav"),
                "daily_change": fund.get("daily_change"),
                "month_return": fund.get("month_return"),
                "cycle": score["holding_period"],
                "hot_news": "关注政策、行业景气度和市场情绪变化。",
                "disclaimer": DISCLAIMER,
            }
        )

    high = sorted(scored, key=lambda item: item["score"], reverse=True)
    low = sorted(scored, key=lambda item: item["sell_index"], reverse=True)
    return {
        "today": high[:3],
        "week": high[:5],
        "undervalued": [item for item in high if item["buy_index"] >= 60 and item["sell_index"] < 60][:4],
        "growth": high[:4],
        "stable": [item for item in high if item["hold_index"] >= 65][:4],
        "aggressive": [item for item in high if item["buy_index"] >= 70][:4],
        "beginner": [item for item in high if item["score"] >= 60 and item["sell_index"] < 65][:4],
        "avoid_chasing": low[:4],
        "disclaimer": DISCLAIMER,
    }
 
