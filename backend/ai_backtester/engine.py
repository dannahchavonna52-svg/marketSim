from __future__ import annotations

from .models import (
    AgentSignal,
    BacktestConfig,
    BacktestResult,
    DailyPortfolioPoint,
    FundNavPoint,
    TradeRecord,
)
from .signals import moving_average_signal


def _max_drawdown_pct(values: list[float]) -> float:
    if not values:
        return 0.0

    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        if peak <= 0:
            continue
        dd = (value - peak) / peak * 100
        max_dd = min(max_dd, dd)
    return max_dd


def _position_ratio(cash: float, units: float, nav: float) -> float:
    total = cash + units * nav
    if total <= 0:
        return 0.0
    return units * nav / total


def run_backtest(
    nav_points: list[FundNavPoint | dict],
    config: BacktestConfig,
) -> BacktestResult:
    """Run a simplified fund backtest.

    Current phase assumptions:
    - The input NAV series is already sorted or sortable by trade_date.
    - Buy and sell both execute at the same day's unit NAV.
    - No T+1 confirmation yet.
    - No real trading, only simulation.
    """

    normalized_points = [
        item if isinstance(item, FundNavPoint) else FundNavPoint.from_dict(item)
        for item in nav_points
    ]
    normalized_points.sort(key=lambda x: x.trade_date)

    if len(normalized_points) < 2:
        raise ValueError("回测至少需要 2 条基金净值数据")

    cash = float(config.initial_cash)
    units = 0.0
    last_buy_index: int | None = None
    trades: list[TradeRecord] = []
    equity_curve: list[DailyPortfolioPoint] = []
    total_values: list[float] = []

    for index, point in enumerate(normalized_points):
        history = normalized_points[: index + 1]
        signal = moving_average_signal(history)
        nav = point.unit_nav
        action = signal.action

        if action == "buy":
            current_ratio = _position_ratio(cash, units, nav)
            if current_ratio >= config.max_position_ratio:
                signal = AgentSignal(
                    action="hold",
                    confidence=80,
                    reasoning="已达到最大仓位限制，暂停买入",
                )
            elif cash <= 0:
                signal = AgentSignal(
                    action="hold",
                    confidence=80,
                    reasoning="现金不足，无法买入",
                )
            else:
                amount = min(config.trade_amount, cash)
                fee = amount * config.buy_fee_rate
                net_amount = max(0.0, amount - fee)
                bought_units = net_amount / nav if nav > 0 else 0.0
                if bought_units > 0:
                    cash -= amount
                    units += bought_units
                    last_buy_index = index
                    trades.append(
                        TradeRecord(
                            trade_date=point.trade_date,
                            fund_code=config.fund_code,
                            action="buy",
                            nav=nav,
                            amount=amount,
                            units=bought_units,
                            fee=fee,
                            cash_after=cash,
                            units_after=units,
                            reasoning=signal.reasoning,
                        )
                    )

        elif action == "sell":
            if units <= 0:
                signal = AgentSignal(
                    action="hold",
                    confidence=80,
                    reasoning="当前无持仓，无法卖出",
                )
            elif last_buy_index is not None and index - last_buy_index < config.min_hold_days:
                signal = AgentSignal(
                    action="hold",
                    confidence=80,
                    reasoning=f"持有时间不足 {config.min_hold_days} 个交易日，暂不卖出",
                )
            else:
                sell_units = units
                gross_amount = sell_units * nav
                fee = gross_amount * config.sell_fee_rate
                net_amount = max(0.0, gross_amount - fee)
                cash += net_amount
                units = 0.0
                trades.append(
                    TradeRecord(
                        trade_date=point.trade_date,
                        fund_code=config.fund_code,
                        action="sell",
                        nav=nav,
                        amount=net_amount,
                        units=sell_units,
                        fee=fee,
                        cash_after=cash,
                        units_after=units,
                        reasoning=signal.reasoning,
                    )
                )

        market_value = units * nav
        total_value = cash + market_value
        total_values.append(total_value)
        peak = max(total_values)
        drawdown_pct = (total_value - peak) / peak * 100 if peak > 0 else 0.0

        equity_curve.append(
            DailyPortfolioPoint(
                trade_date=point.trade_date,
                nav=nav,
                cash=cash,
                units=units,
                market_value=market_value,
                total_value=total_value,
                drawdown_pct=drawdown_pct,
                signal=signal.action,
                reasoning=signal.reasoning,
            )
        )

    final_value = equity_curve[-1].total_value
    total_return_pct = (final_value / config.initial_cash - 1) * 100
    max_drawdown_pct = _max_drawdown_pct(total_values)

    return BacktestResult(
        fund_code=config.fund_code,
        initial_cash=config.initial_cash,
        final_value=final_value,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        trades=trades,
        equity_curve=equity_curve,
    )
