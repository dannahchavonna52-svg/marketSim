# backend/ai_backtester

这是 MarketSim 的 AI 基金回测模块。

当前阶段已经完成：

- 不连接券商；
- 不真实交易；
- 不提供投资建议；
- 根据历史净值做模拟回测；
- 后端 service/router 已完成；
- `backend/main_ai.py` 已挂载回测接口；
- 前端 `ai-backtest.js` 已接入页面；
- 后端异常时，前端可自动使用同款规则 fallback；
- 已提供竖屏视频演示模式。

## 代码结构

```text
backend/ai_backtester/
├── __init__.py
├── models.py        # 数据模型
├── signals.py       # 规则信号，后续可替换为 AI Agent
├── engine.py        # 回测引擎和仓位控制
├── service.py       # 复用 rich_fund_data 获取净值并运行回测
├── routes.py        # POST /api/ai-backtest/run
├── smoke_check.py   # 本地冒烟检查
└── README.md
```

## 启动方式

项目根目录双击：

```text
start.bat
```

或者：

```powershell
cd backend
python -m uvicorn main_ai:app --host 0.0.0.0 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

## 冒烟检查

在 `backend` 目录执行：

```powershell
python -m ai_backtester.smoke_check
```

该检查不依赖真实基金数据源，会验证：

- 回测引擎可以运行；
- 最大仓位不会被突破；
- 收益曲线可以生成；
- AI 回测 API 路由存在；
- 新增前端静态资源路由存在；
- 视频演示资源文件存在。

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

前端优先请求：

```text
POST /api/ai-backtest/run
```

如果后端接口异常，会自动退回到前端规则回测，并复用：

```text
GET /api/funds/{symbol}
```

fallback 的作用是避免演示期间直接白屏，不代表可以跳过后端联调。

## 视频演示模式

录屏地址：

```text
http://127.0.0.1:8000/?demo=1&fund=014855&focus=1
```

或者双击：

```text
start-demo.bat
```

演示模式会遮挡账号、聚焦回测页面，并优化手机竖屏录制布局。

更多说明：

```text
docs/VIDEO_DEMO_PLAN.md
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
- 只允许 `buy`、`sell`、`hold`；
- 买入金额会被最大仓位上限精确截断。

这只是为了先把回测链路跑通，不代表最终策略，也不代表真正的 AI 预测。

## 留给 Codex 的工作

Codex 只需完成：

1. 在用户本地运行冒烟检查；
2. 启动 `main_ai:app`；
3. 测试真实基金数据源；
4. 测试普通模式和演示模式；
5. 修复本地环境、导入、路径或样式兼容问题；
6. 输出完整测试报告。

具体清单：

```text
docs/CODEX_REMAINING_TASKS.md
```

## 注意

第一阶段先不要接大模型。先让规则回测稳定跑通，再把 `signals.py` 替换成多 Agent 决策或增加 LLM 复盘解释。
