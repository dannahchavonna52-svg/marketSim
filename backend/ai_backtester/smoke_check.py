from __future__ import annotations

from datetime import date, timedelta
import math
from pathlib import Path

from .engine import run_backtest
from .models import BacktestConfig, FundNavPoint


def _synthetic_nav_points(count: int = 220) -> list[FundNavPoint]:
    points: list[FundNavPoint] = []
    current_date = date(2025, 1, 1)
    for index in range(count):
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)
        trend = 1 + index * 0.0012
        cycle = math.sin(index / 9) * 0.035
        correction = -0.10 if 125 <= index <= 140 else 0
        points.append(
            FundNavPoint(
                trade_date=current_date,
                unit_nav=max(0.2, trend + cycle + correction),
            )
        )
        current_date += timedelta(days=1)
    return points


def run_smoke_check() -> None:
    results = []
    for cap in (0.2, 0.5, 0.8, 1.0):
        config = BacktestConfig(
            fund_code="014855",
            initial_cash=100000,
            trade_amount=10000,
            max_position_ratio=cap,
            buy_fee_rate=0.001,
            sell_fee_rate=0.005,
        )
        result = run_backtest(_synthetic_nav_points(), config)
        results.append((cap, result))

        assert result.equity_curve, "equity curve should not be empty"
        assert math.isfinite(result.final_value) and result.final_value > 0
        assert result.max_drawdown_pct <= 0, "max drawdown should not be positive"
        dates = [point.trade_date for point in result.equity_curve]
        assert dates == sorted(dates), "equity dates should be ascending"
        for point in result.equity_curve:
            total = point.cash + point.market_value
            assert math.isclose(total, point.total_value, rel_tol=0, abs_tol=1e-7)
            ratio = point.market_value / total if total > 0 else 0
            assert ratio <= cap + 1e-9, f"position cap {cap:.0%} was exceeded"

    from main_ai import app

    route_paths = {route.path for route in app.routes}
    required_paths = {
        "/api/ai-backtest/run",
        "/api/ai-research/{fund_code}",
        "/ai-backtest.js",
        "/app-final.js",
        "/demo-mode.js",
        "/demo-mode.css",
    }
    missing = sorted(required_paths - route_paths)
    assert not missing, f"missing routes: {missing}"

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    required_files = {
        "ai-backtest.js",
        "demo-mode.js",
        "demo-mode.css",
        "app-final.js",
        "index.html",
    }
    missing_files = sorted(name for name in required_files if not (frontend_dir / name).exists())
    assert not missing_files, f"missing frontend files: {missing_files}"

    print("AI backtester smoke check passed")
    result = results[-1][1]
    print(f"equity points: {len(result.equity_curve)}")
    print(f"position caps: {', '.join(f'{cap:.0%}' for cap, _ in results)}")
    print(f"trades: {len(result.trades)}")
    print(f"final value: {result.final_value:.2f}")
    print(f"max drawdown: {result.max_drawdown_pct:.2f}%")
    print("video demo assets: ok")


if __name__ == "__main__":
    run_smoke_check()
