# AI 基金回测模块改造计划

本分支用于把现有 `marketSim` 项目扩展为“中国基金分析 + 模拟回测 + 内容演示”应用。

当前不直接搬运 `virattt/ai-hedge-fund` 的整套代码，而是吸收其核心思想：

- 分析模块解耦；
- 风控模块；
- 组合决策；
- 回测引擎；
- 前后端分离展示；
- 后续可增加 Agent 和大模型复盘。

## 当前完成状态

已经完成第一阶段可试用版本：

- `backend/ai_backtester/models.py`：数据模型；
- `backend/ai_backtester/signals.py`：20/60 日均线、动量与回撤信号；
- `backend/ai_backtester/engine.py`：回测引擎和最大仓位精确控制；
- `backend/ai_backtester/service.py`：接入现有 `rich_fund_data` 历史净值；
- `backend/ai_backtester/routes.py`：`POST /api/ai-backtest/run`；
- `backend/ai_backtester/smoke_check.py`：本地冒烟检查；
- `backend/main_ai.py`：挂载 AI 回测 router 和新增静态资源；
- `frontend/ai-backtest.js`：前端“回测”页面与浏览器端 fallback；
- `frontend/demo-mode.js`、`frontend/demo-mode.css`：视频演示模式；
- `start.bat`：普通启动；
- `start-demo.bat`：一键启动竖屏演示；
- `docs/CODEX_REMAINING_TASKS.md`：Codex 最后联调清单；
- `docs/VIDEO_DEMO_PLAN.md`：小红书 / 抖音内容方向。

前端优先请求：

```text
POST /api/ai-backtest/run
```

如果后端接口异常，会自动使用现有：

```text
GET /api/funds/{symbol}
```

并在浏览器中使用同款规则完成 fallback 回测，避免演示时直接白屏。

## 为什么不直接 Fork 原项目

`virattt/ai-hedge-fund` 默认面向美股股票，依赖：

- Financial Datasets API；
- 美股 ticker；
- 股票 OHLCV；
- 公司财报、公司新闻和内部人交易；
- 做多、做空、平空等动作。

中国基金模拟交易更需要：

- 6 位基金代码；
- 基金历史净值；
- 场外基金申购 / 赎回；
- T+1 确认；
- 申购费、赎回费；
- 定投、调仓、最大回撤、收益曲线。

因此采用轻量重构路线，而不是复制原项目。

## 第一阶段：规则回测（已完成骨架）

```text
backend/ai_backtester/
├── __init__.py
├── models.py
├── signals.py
├── engine.py
├── service.py
├── routes.py
├── smoke_check.py
└── README.md
```

已实现：

1. 接收和清洗基金净值；
2. 校验基金代码和日期；
3. 生成买入 / 卖出 / 持有信号；
4. 执行简化回测；
5. 精确限制买入后的最大仓位；
6. 输出每日资产曲线、交易记录、总收益率和最大回撤；
7. 前端展示结果；
8. 后端异常时提供前端 fallback；
9. 提供不依赖真实数据源的冒烟检查。

暂时不做：

- 真实交易；
- 券商接口；
- 自动下单；
- 绕过任何平台接口；
- 收益承诺；
- 投资建议。

## 当前接口

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
  "trade_amount": 10000,
  "max_position_ratio": 0.8,
  "buy_fee_rate": 0.001,
  "sell_fee_rate": 0.005
}
```

响应主要包含：

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

示例中的收益数字只是结构说明，不是实际或保证收益。

## 视频演示方向（已预留）

普通地址：

```text
http://127.0.0.1:8000
```

视频演示地址：

```text
http://127.0.0.1:8000/?demo=1&fund=014855&focus=1
```

演示模式会：

- 遮挡真实用户名；
- 聚焦 AI 回测页面；
- 优化 9:16 竖屏录制；
- 隐藏无关导航和详细表格；
- 保留“演示模式 · 非投资建议”提示；
- 不制造虚假回测数据。

后续内容产品化优先级：

```text
结果分享卡 > 买卖点标记 > 多策略对比 > 回测动画 > 自动口播摘要
```

## 第二阶段：更接近真实基金规则

后续加入：

- T 日提交；
- T+1 确认份额；
- T+2 可赎回；
- 申购费；
- 持有天数赎回费；
- 节假日跳过；
- 定投模拟；
- 分批赎回。

## 第三阶段：多策略与内容输出

建议增加：

- 均线策略；
- 定投策略；
- 回撤加仓策略；
- 多策略对比；
- 曲线买卖点标记；
- 一键生成 PNG 分享卡；
- 一键生成视频口播摘要；
- 示例基金列表和演示数据状态。

## 第四阶段：AI Agent

引入：

- 技术面 Agent：趋势、动量、均线、回撤；
- 风控 Agent：最大仓位、回撤控制、现金比例；
- 组合经理 Agent：综合信号后决定买入、卖出或持有；
- 复盘 Agent：解释每次交易原因。

第一版不依赖大模型。规则回测稳定后，再接 OpenAI / DeepSeek / Kimi / Ollama 做解释和复盘，不把大模型当作价格预测器。

## 与原 ai-hedge-fund 的对应关系

| 原项目模块 | 本项目对应改造 |
|---|---|
| `src/tools/api.py` | `backend/rich_fund_data.py` + `backend/ai_backtester/service.py` |
| `technical_analyst` | `backend/ai_backtester/signals.py` |
| `risk_manager` | `backend/ai_backtester/engine.py` 当前风控 + 后续独立模块 |
| `portfolio_manager` | 后续 `backend/ai_backtester/portfolio_manager.py` |
| `backtesting/engine.py` | `backend/ai_backtester/engine.py` |
| 股票 OHLCV | 基金净值 NAV |
| buy/sell/short/cover/hold | buy/sell/hold |

## 当前分支

```text
feature/ai-fund-backtester
```

PR：

```text
#1 Add AI fund backtester trial version
```

当前分支相对 `main` 只新增模块和演示资源，并对 `frontend/index.html` 与 `start.bat` 做了最小接入。正式合并前必须由 Codex 在用户本地完成冒烟检查、真实数据源测试和手机竖屏测试。
