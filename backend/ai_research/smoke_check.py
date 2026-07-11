from __future__ import annotations

from datetime import date, timedelta
import math

from .agents import macro_agent, quality_agent, risk_agent, sentiment_agent, technical_agent
from .style_models import run_style_models


def run_smoke_check() -> None:
    history = []
    current = date(2025, 1, 1)
    for index in range(220):
        history.append({
            "date": current.isoformat(),
            "nav": 1 + index * 0.001 + math.sin(index / 12) * 0.03,
        })
        current += timedelta(days=1)
    fund = {
        "symbol": "014855",
        "name": "测试基金",
        "history": history,
        "year_return": 18,
        "month_return": 4,
        "max_drawdown": -12,
        "sharpe_ratio": 0.9,
        "fund_size": 80,
        "manager": "测试经理",
        "company": "测试公司",
        "industries": "科技,半导体",
    }
    agents = [
        technical_agent(fund), quality_agent(fund), sentiment_agent(fund, []),
        macro_agent(fund, []), risk_agent(fund, []),
    ]
    styles = run_style_models(fund)
    assert len(agents) == 5
    assert len(styles) == 3
    assert all(0 <= item.score <= 100 for item in agents + styles)
    assert all(item.summary and item.evidence for item in agents + styles)
    print("AI research smoke check passed (5 core agents, 3 China fund styles)")


if __name__ == "__main__":
    run_smoke_check()
