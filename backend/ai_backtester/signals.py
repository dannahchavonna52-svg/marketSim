from __future__ import annotations

from statistics import mean

from .models import AgentSignal, FundNavPoint


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous


def moving_average_signal(
    nav_points: list[FundNavPoint],
    *,
    short_window: int = 20,
    long_window: int = 60,
    stop_loss_drawdown: float = -0.08,
) -> AgentSignal:
    """Generate a simple buy/sell/hold signal from fund NAV history.

    This is deliberately deterministic for the first phase. Later it can be
    replaced or combined with LLM-based agents.
    """

    if len(nav_points) < max(short_window, long_window) + 1:
        return AgentSignal(
            action="hold",
            confidence=30,
            reasoning="净值历史不足，暂时观望",
        )

    navs = [p.unit_nav for p in nav_points]
    latest_nav = navs[-1]
    short_ma = mean(navs[-short_window:])
    long_ma = mean(navs[-long_window:])
    previous_short_ma = mean(navs[-short_window - 1 : -1])
    previous_long_ma = mean(navs[-long_window - 1 : -1])

    recent_high = max(navs[-long_window:])
    drawdown = _pct_change(latest_nav, recent_high)
    one_month_return = _pct_change(latest_nav, navs[-short_window])

    crossed_up = previous_short_ma <= previous_long_ma and short_ma > long_ma
    crossed_down = previous_short_ma >= previous_long_ma and short_ma < long_ma

    if drawdown <= stop_loss_drawdown:
        return AgentSignal(
            action="sell",
            confidence=85,
            reasoning=f"近{long_window}日回撤{drawdown:.2%}，触发风控",
        )

    if crossed_up and one_month_return > 0:
        return AgentSignal(
            action="buy",
            confidence=75,
            reasoning=f"{short_window}日均线上穿{long_window}日均线，动量转强",
        )

    if crossed_down:
        return AgentSignal(
            action="sell",
            confidence=70,
            reasoning=f"{short_window}日均线下穿{long_window}日均线，趋势转弱",
        )

    if short_ma > long_ma and one_month_return > 0.03:
        return AgentSignal(
            action="buy",
            confidence=65,
            reasoning=f"短期均线在长期均线上方，近{short_window}日收益为{one_month_return:.2%}",
        )

    return AgentSignal(
        action="hold",
        confidence=55,
        reasoning="趋势信号不明确，维持观望",
    )
