# backend/ai_backtester

这是 MarketSim 的 AI 基金回测模块。

当前阶段已经完成：

- 不连接券商；
- 不真实交易；
- 不提供投资建议；
- 根据历史净值做模拟回测；
- 后端 service/router 已准备好；
- 前端 `ai-backtest.js` 已接入页面，后端未挂载时会自动使用前端同款规则回测。

## 代码结构

```text
backend/ai_backtester/
├── __init__.py
├── models.py   # 数据模型
├── signals.py  # 规则信号，后续可替换为 AI Agent
├── engine.py   # 回测引擎
├── service.py  # 复用 rich_fund_data 获取净值并运行回测
├── routes.py   # FastAPI router，等待挂载到 main.py
└── README.md
```

## 当前前端功能

`frontend/ai-backtest.js` 会在登录后的底部导航自动增加“回测”入口。

页面支持：

- 基金代码；
- 开始日期 / 结束日期；
- 初始资金；
- 单次买入金额；
- 最大仓位；
- 买入费率；
- 卖出费率；
- 刷新数据；
- 资产曲线；
- 交易记录；
- 最近 20 个交易日资产明细。

前端会先尝试请求：

```text
POST /api/ai-backtest/run
```

如果后端 router 还没有挂载，会自动退回到前端规则回测，直接复用现有：

```text
GET /api/funds/{symbol}
```

所以即使 Codex 还没挂后端路由，页面也可以先跑通。

## 后端挂载方式

在 `backend/main.py` 增加两行即可：

```python
from ai_backtester.routes import router as ai_backtest_router

app.include_router(ai_backtest_router)
```

建议把 import 放在其他业务 import 附近，把 `include_router` 放在 `app = FastAPI(...)` 和 CORS 配置之后、路由定义之前。

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

## 现在留给 Codex 的细化工作

1. 把 `ai_backtester.routes` 挂载进 `backend/main.py`；
2. 本地启动后确认 `/api/ai-backtest/run` 返回成功；
3. 根据真实页面宽度微调 `AI 基金回测` 表单样式；
4. 视需要把前端 fallback 关闭，全部改用后端接口；
5. 后续再把 `signals.py` 升级成多 Agent 或 LLM 复盘。

## 注意

第一阶段先不要接大模型。先让规则回测稳定跑通，再把 `signals.py` 替换成多 Agent 决策。
