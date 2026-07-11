from __future__ import annotations

from datetime import datetime
from typing import Any
import re

import rich_fund_data
import rich_news_data

from .agents import macro_agent, quality_agent, risk_agent, sentiment_agent, technical_agent
from .style_models import run_style_models


DISCLAIMER = "历史数据和规则分析仅供学习与模拟研究，不构成投资建议，不连接券商，不执行真实交易。"


def _fund_code(value: str) -> str:
    code = re.sub(r"\D", "", str(value or ""))
    if len(code) != 6:
        raise ValueError("基金代码必须是 6 位数字")
    return code


def _portfolio_decision(opinions: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {"technical": 0.25, "quality": 0.25, "sentiment": 0.15, "macro": 0.15, "risk": 0.20}
    score = round(sum(item["score"] * weights[item["agent_id"]] for item in opinions), 1)
    risk = next(item for item in opinions if item["agent_id"] == "risk")
    technical = next(item for item in opinions if item["agent_id"] == "technical")
    quality = next(item for item in opinions if item["agent_id"] == "quality")
    missing_count = sum(len(item["missing_data"]) for item in opinions)
    confidence = round(max(35, min(92, 88 - missing_count * 7)), 1)

    if risk["score"] < 40:
        action, action_level = "高风险，暂缓加仓", "avoid"
        reason = "风控 Agent 给出高风险结论；在不知道用户是否持有的情况下，只建议暂缓增加模拟仓位。"
    elif score >= 68 and technical["score"] >= 58 and quality["score"] >= 58:
        action, action_level = "小额分批关注", "accumulate"
        reason = "综合分数达到关注区间，趋势和基金质量没有明显冲突；仍需分批并设置仓位上限。"
    elif score < 45 or (technical["score"] < 40 and quality["score"] < 50):
        action, action_level = "暂缓买入", "avoid"
        reason = "综合证据偏弱，趋势与基金质量没有形成足够支持。"
    else:
        action, action_level = "持有或继续观察", "hold"
        reason = "多 Agent 意见存在分歧，目前没有足够证据支持明显加仓或减仓。"

    supporting = sorted(opinions, key=lambda item: item["score"], reverse=True)[:2]
    opposing = sorted(opinions, key=lambda item: item["score"])[:2]
    return {
        "score": score,
        "confidence": confidence,
        "action": action,
        "action_level": action_level,
        "reason": reason,
        "supporting_evidence": [f"{item['name']}：{item['summary']}（{item['score']:.1f}）" for item in supporting],
        "opposing_evidence": [f"{item['name']}：{item['summary']}（{item['score']:.1f}）" for item in opposing],
        "position_rule": "首次模拟仓位建议不超过总资产的 10%，单只基金上限 20%；只有后续证据改善才考虑分批增加。",
    }


def run_fund_research(fund_code: str, refresh: bool = False) -> dict[str, Any]:
    code = _fund_code(fund_code)
    detail = rich_fund_data.get_fund_detail(code, refresh=refresh)
    fund = detail.get("fund") or {}
    market = rich_news_data.get_market_news(limit=50, refresh=refresh)
    related = rich_news_data.match_news_for_funds(market.get("news") or [], [fund])
    source_errors = list(detail.get("errors") or []) + list(market.get("errors") or [])

    opinions = [
        technical_agent(fund),
        quality_agent(fund),
        sentiment_agent(fund, related),
        macro_agent(fund, market.get("news") or []),
        risk_agent(fund, source_errors),
    ]
    opinion_rows = [item.to_dict() for item in opinions]
    style_rows = [item.to_dict() for item in run_style_models(fund)]
    return {
        "fund": {
            "symbol": fund.get("symbol") or code,
            "name": fund.get("name") or f"{code} 基金",
            "fund_type": fund.get("fund_type") or "公募基金",
            "latest_nav": fund.get("latest_nav"),
            "daily_change": fund.get("daily_change"),
            "data_source": fund.get("data_source"),
        },
        "agents": opinion_rows,
        "style_models": style_rows,
        "decision": _portfolio_decision(opinion_rows),
        "related_news": related[:5],
        "data_quality": {
            "history_count": len(fund.get("history") or []),
            "source_errors": source_errors,
            "is_fallback": "兜底" in str(fund.get("data_source") or ""),
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "规则型多 Agent 投研会议 v1（不使用大模型预测价格）",
        "disclaimer": DISCLAIMER,
    }
