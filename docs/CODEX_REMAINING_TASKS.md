# Codex 剩余细化任务

本分支已经完成了 AI 基金回测的大部分骨架、前端接入和可试用启动入口。Codex 主要只需要做本地联调和少量细化。

## 已完成

- 新增 `backend/ai_backtester/models.py`：基金净值、信号、交易记录、资产曲线、回测结果模型；
- 新增 `backend/ai_backtester/signals.py`：20/60 日均线 + 回撤风控规则；
- 新增 `backend/ai_backtester/engine.py`：简化基金回测引擎；
- 新增 `backend/ai_backtester/service.py`：复用 `rich_fund_data.get_fund_detail()` 获取历史净值并运行回测；
- 新增 `backend/ai_backtester/routes.py`：`POST /api/ai-backtest/run` 后端接口；
- 新增 `backend/main_ai.py`：AI 回测增强启动入口，导入原 `main.py` 后挂载 AI router；
- 更新 `start.bat`：默认启动 `main_ai:app`；
- 新增 `frontend/ai-backtest.js`：页面自动增加“回测”入口，并展示回测结果；
- 更新 `frontend/index.html`：加载 `ai-backtest.js`；
- 后端接口异常时，前端会自动 fallback 到浏览器端回测，不影响试用。

## 现在可以直接试用

启动方式：

```text
双击 start.bat
```

或者命令行：

```powershell
cd backend
python -m uvicorn main_ai:app --host 0.0.0.0 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

登录后点击底部导航“回测”。

## 本地测试页面

1. 启动后端；
2. 打开页面并登录；
3. 底部导航点击“回测”；
4. 输入基金代码，例如 `014855`；
5. 点击“开始回测”；
6. 确认出现：
   - 最终资产；
   - 总收益率；
   - 最大回撤；
   - 交易次数；
   - 资产曲线；
   - 交易记录；
   - 最近 20 个交易日资产明细。

## 可选 1：将 router 直接合入 main.py

当前为了降低风险，使用 `backend/main_ai.py` 包装原 app 并挂载 AI router。后续如果要彻底合并，可以打开：

```text
backend/main.py
```

在 import 区域增加：

```python
from ai_backtester.routes import router as ai_backtest_router
```

在 `app = FastAPI(...)`、CORS 配置之后增加：

```python
app.include_router(ai_backtest_router)
```

然后把 `start.bat` 里的 `main_ai:app` 改回 `main:app`。

## 可选 2：样式微调

如果表单在手机上太挤，可以在 `frontend/style.css` 增加：

```css
#aiBacktest .watch-form {
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

#aiBacktestChart {
  min-height: 360px;
}
```

## 可选 3：关闭前端 fallback

当前 `frontend/ai-backtest.js` 会先请求后端接口，失败后自动用前端规则回测。等后端接口稳定后，可以把 fallback 改成直接报错，保证所有回测都走后端。

## 可选 4：升级策略

后续可以把 `signals.py` 里的规则信号升级为：

- 技术面 Agent：均线、动量、回撤、波动率；
- 风控 Agent：最大仓位、止损、连续回撤控制；
- 组合经理 Agent：综合信号输出买入 / 卖出 / 持有；
- 复盘 Agent：用大模型解释每次交易原因。

## 安全边界

不要接真实券商，不要自动下单，不要绕过支付宝、天天基金、券商或任何平台风控。当前功能只用于学习和模拟研究。
