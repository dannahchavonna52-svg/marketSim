# AI 基金回测模块改造计划

本分支用于把现有 `marketSim` 项目逐步扩展为“中国基金 AI 分析 + 模拟回测”应用。

当前策略：不直接搬运 `virattt/ai-hedge-fund` 的整套代码，而是吸收它的核心思想：

- 多 Agent 分析；
- 风控模块；
- 组合经理决策；
- 回测引擎；
- 前后端分离展示。

## 为什么不直接 Fork 原项目

`virattt/ai-hedge-fund` 默认面向美股股票，依赖：

- Financial Datasets API；
- 美股 ticker，例如 AAPL、MSFT、NVDA；
- 股票 OHLCV 数据；
- 公司财报、公司新闻、内部人交易；
- 做多、做空、平空等股票交易动作。

中国基金模拟交易更需要：

- 基金代码，例如 `014855`、`000001`、`510300`；
- 基金历史净值；
- 场外基金申购 / 赎回；
- T+1 确认；
- 申购费、赎回费；
- 定投、调仓、最大回撤、收益曲线。

因此本项目采用“轻量重构”路线。

## 第一阶段目标

先做一个不影响现有功能的后端子模块：

```text
backend/ai_backtester/
├── __init__.py
├── models.py
├── signals.py
└── engine.py
```

第一阶段只实现：

1. 接收基金净值序列；
2. 根据简单技术信号生成买入 / 卖出 / 持有；
3. 执行简化回测；
4. 输出每日资产曲线、交易记录、总收益率、最大回撤。

暂时不做：

- 真实交易；
- 券商接口；
- 自动下单；
- 绕过任何平台接口；
- 投资建议。

## 第二阶段目标

接入现有 `marketSim` 的数据层：

- 复用已有 AKShare 基金搜索 / 净值数据；
- 新增回测 API，例如：

```text
POST /api/ai-backtest/run
```

请求示例：

```json
{
  "fund_code": "014855",
  "start_date": "2024-01-01",
  "end_date": "2026-07-01",
  "initial_cash": 100000,
  "trade_amount": 10000
}
```

响应示例：

```json
{
  "summary": {
    "initial_cash": 100000,
    "final_value": 112300.5,
    "total_return_pct": 12.3,
    "max_drawdown_pct": -8.2
  },
  "trades": [],
  "equity_curve": []
}
```

## 第三阶段目标

加入更接近真实基金的规则：

- T 日提交；
- T+1 确认份额；
- T+2 可赎回；
- 申购费；
- 持有天数赎回费；
- 节假日跳过；
- 定投模拟。

## 第四阶段目标

引入 AI Agent：

- 技术面 Agent：趋势、动量、均线、回撤；
- 风控 Agent：最大仓位、回撤控制、现金比例；
- 组合经理 Agent：综合信号后决定买入、卖出或持有；
- 复盘 Agent：解释每次交易原因。

第一版不依赖大模型，先用规则跑通。后续再接 OpenAI / DeepSeek / Kimi / Ollama。

## 与原 ai-hedge-fund 的对应关系

| 原项目模块 | 本项目对应改造 |
|---|---|
| `src/tools/api.py` | `backend/fund_data.py` 或后续 `backend/ai_backtester/data_adapter.py` |
| `technical_analyst` | `backend/ai_backtester/signals.py` |
| `risk_manager` | 后续 `backend/ai_backtester/risk.py` |
| `portfolio_manager` | 后续 `backend/ai_backtester/portfolio_manager.py` |
| `backtesting/engine.py` | `backend/ai_backtester/engine.py` |
| 股票 OHLCV | 基金净值 NAV |
| buy/sell/short/cover/hold | buy/sell/hold |

## 当前分支说明

分支名：

```text
feature/ai-fund-backtester
```

该分支只新增文件，不修改现有主功能。确认可用后，再逐步接入 FastAPI 路由和前端页面。
