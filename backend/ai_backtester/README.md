# backend/ai_backtester

这是 MarketSim 的 AI 基金回测实验模块。

当前阶段是最小可用骨架：

- 不连接券商；
- 不真实交易；
- 不提供投资建议；
- 只根据历史净值做模拟回测。

## 代码结构

```text
backend/ai_backtester/
├── __init__.py
├── models.py   # 数据模型
├── signals.py  # 规则信号，后续可替换为 AI Agent
└── engine.py   # 回测引擎
```

## 最小调用示例

```python
from ai_backtester import BacktestConfig, run_backtest

nav_points = [
    {"trade_date": "2024-01-01", "unit_nav": 1.0000},
    {"trade_date": "2024-01-02", "unit_nav": 1.0020},
    # 这里需要传入完整历史净值序列
]

result = run_backtest(
    nav_points,
    BacktestConfig(
        fund_code="014855",
        initial_cash=100000,
        trade_amount=10000,
        max_position_ratio=0.8,
        buy_fee_rate=0.001,
        sell_fee_rate=0.005,
    ),
)

print(result.to_dict())
```

## 当前策略说明

当前信号在 `signals.py` 中：

- 20 日均线；
- 60 日均线；
- 近 60 日回撤风控；
- 只允许 `buy`、`sell`、`hold`。

这只是为了先把回测链路跑通，不代表最终策略。

## 下一步接入 MarketSim

建议 Codex 下一步执行：

1. 找到现有基金净值获取函数；
2. 新增一个 adapter，把现有净值数据转换成 `FundNavPoint`；
3. 新增 FastAPI 路由：

```text
POST /api/ai-backtest/run
```

4. 前端新增“AI 回测”页面，展示：

- 总收益率；
- 最大回撤；
- 交易记录；
- 每日资产曲线；
- 每次买卖原因。

## 注意

第一阶段先不要接大模型。先让规则回测稳定跑通，再把 `signals.py` 替换成多 Agent 决策。
