# Codex 最后联调任务

本分支已经完成 AI 基金回测的核心代码、前端页面、启动入口、风险控制和视频演示模式。Codex 现在只需要在用户本地电脑上完成运行验证与少量兼容修复，不要重新设计整个项目。

## 已完成

- `backend/ai_backtester/models.py`：基金净值、信号、交易记录、资产曲线、回测结果模型；
- `backend/ai_backtester/signals.py`：20/60 日均线、动量和回撤风控；
- `backend/ai_backtester/engine.py`：回测引擎，已精确限制买入后的最大仓位；
- `backend/ai_backtester/service.py`：复用 `rich_fund_data.get_fund_detail()` 获取历史净值，校验基金代码和日期；
- `backend/ai_backtester/routes.py`：`POST /api/ai-backtest/run`；
- `backend/ai_backtester/smoke_check.py`：不依赖真实数据源的本地冒烟检查；
- `backend/main_ai.py`：导入原应用、挂载 AI router、提供新增静态资源，并注入可选演示模式；
- `frontend/ai-backtest.js`：回测页面、前端 fallback、收益曲线和交易记录；
- `frontend/demo-mode.js`、`frontend/demo-mode.css`：隐私遮挡和竖屏录制模式；
- `start.bat`：普通启动；
- `start-demo.bat`：视频演示启动；
- `docs/VIDEO_DEMO_PLAN.md`：小红书 / 抖音视频内容方向。

## 第一步：同步并确认分支

```powershell
git fetch origin
git checkout feature/ai-fund-backtester
git pull origin feature/ai-fund-backtester
git status
```

不要直接在 `main` 分支修改。

## 第二步：先运行冒烟检查

进入后端目录：

```powershell
cd backend
python -m ai_backtester.smoke_check
```

预期看到：

```text
AI backtester smoke check passed
video demo assets: ok
```

如果失败，只修复具体导入、语法、路径或版本兼容问题，不要重构原有 MarketSim。

## 第三步：启动普通模式

```powershell
python -m uvicorn main_ai:app --host 0.0.0.0 --port 8000
```

或者返回项目根目录双击：

```text
start.bat
```

打开：

```text
http://127.0.0.1:8000
```

检查：

1. 页面能正常打开；
2. 注册和登录正常；
3. 原有首页、基金、自选、模拟交易功能未被破坏；
4. 底部导航出现“回测”；
5. DevTools Network 中以下资源不报 404：
   - `/app-auth.js`
   - `/app-pages.js`
   - `/app-final.js`
   - `/ai-backtest.js`
6. `POST /api/ai-backtest/run` 能正常返回；
7. 输入 `014855` 后显示：
   - 最终资产；
   - 总收益率；
   - 最大回撤；
   - 交易次数；
   - 资产曲线；
   - 回测交易记录；
   - 最近 20 个交易日资产明细。

## 第四步：异常场景测试

至少检查：

- 非 6 位基金代码；
- 开始日期晚于结束日期；
- 日期格式错误；
- 历史净值不足 80 条；
- 数据源超时或暂不可用；
- 最大仓位设置为 20%、50%、80% 时，任何一天都不能超过对应上限；
- 后端接口失败时，前端 fallback 能给出清晰提示且不白屏。

建议测试基金代码：

```text
014855
000001
110022
161725
005827
```

不要因为某一只基金的数据源失败就改动整个数据层，优先在 `backend/ai_backtester/service.py` 做兼容。

## 第五步：测试视频演示模式

普通演示地址：

```text
http://127.0.0.1:8000/?demo=1&fund=014855
```

竖屏聚焦地址：

```text
http://127.0.0.1:8000/?demo=1&fund=014855&focus=1
```

自动回测地址：

```text
http://127.0.0.1:8000/?demo=1&fund=014855&focus=1&autorun=1
```

也可以双击：

```text
start-demo.bat
```

检查：

1. 普通地址不会加载演示模式；
2. `?demo=1` 会加载 `/demo-mode.css` 和 `/demo-mode.js`；
3. 用户名显示为“演示账号”，不泄露真实账号；
4. 页面标题变为“AI 基金回测实验室”；
5. 底部只保留“回测”入口；
6. `fund=xxxxxx` 会预填对应代码；
7. `focus=1` 会隐藏详细交易和资产明细，突出结果卡和曲线；
8. `autorun=1` 登录后只运行一次，不应重复请求；
9. 浏览器宽度 430px～520px 时，页面不横向溢出；
10. 页面始终保留“演示模式 · 非投资建议”提示。

## 允许 Codex 修改的范围

优先允许修改：

- `backend/ai_backtester/`；
- `backend/main_ai.py`；
- `frontend/ai-backtest.js`；
- `frontend/demo-mode.js`；
- `frontend/demo-mode.css`；
- `start.bat`；
- `start-demo.bat`；
- 相关说明文档。

除非确有兼容问题，不要大改：

- `backend/main.py`；
- 原有数据库结构；
- 登录系统；
- 原有交易逻辑；
- 原有基金详情和资讯功能。

## 最后需要 Codex 输出的报告

完成后请明确说明：

1. Python 版本和依赖是否安装成功；
2. 冒烟检查是否通过；
3. 项目是否正常启动；
4. 普通模式是否正常；
5. AI 回测后端接口是否正常；
6. 哪些基金代码测试成功；
7. 哪些数据源出现失败；
8. 演示模式是否正常；
9. 手机竖屏是否溢出；
10. 修改了哪些文件；
11. 是否仍存在未解决问题；
12. 是否建议把 `main_ai.py` 最终合入 `main.py`。

## 安全边界

不要接真实券商，不要自动下单，不要使用真实资金，不要绕过支付宝、天天基金、券商或任何平台风控。所有页面和公开内容都应明确说明：历史回测不代表未来收益，仅供学习和模拟研究，不构成投资建议。
