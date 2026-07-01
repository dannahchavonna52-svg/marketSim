# MarketSim Fund App

MarketSim Fund App 是一个本地运行的基金资讯分析 + 基金评分 + 模拟交易 Web/PWA 应用。它支持电脑和安卓手机浏览器访问，也可以添加到安卓桌面。系统只做学习、分析和模拟交易，不接券商账户，不做真实交易，不提供投资建议。

## 目录结构

```text
marketsim-web/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── market_data.py
│   ├── trading.py
│   ├── requirements.txt
│   └── data/
│       └── marketsim.db
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── README.md
└── start.bat
```

## 安装依赖

建议使用 Python 3.10 或更新版本。

```powershell
cd D:\桌面\基金\marketsim-web\backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 启动后端

方式一：双击项目根目录下的 `start.bat`。

方式二：命令行启动。

```powershell
cd D:\桌面\基金\marketsim-web\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

首次启动会自动创建 SQLite 数据库和默认模拟账户，默认初始资金为 100000 元。

## 打开前端

电脑浏览器访问：

```text
http://127.0.0.1:8000
```

手机访问：

1. 让手机和电脑连接同一个 Wi-Fi。
2. 启动 `start.bat`，窗口里会显示电脑的 IPv4 地址。
3. 在手机浏览器打开：

```text
http://电脑IPv4地址:8000
```

例如：

```text
http://192.168.1.8:8000
```

如果手机打不开，通常是 Windows 防火墙拦截了 Python 或端口 8000，需要允许当前网络访问。

## 账号登录

系统现在支持本地账号登录。

- 第一次使用时，在登录页点击“注册新账号”；
- 注册成功后会自动创建一个独立的模拟账户；
- 每个账号默认初始资金为 100000 元；
- 不同账号的自选、持仓、交易记录互相隔离；
- 电脑端和手机端登录同一个账号，可以看到同一份数据。

账号数据保存在本地 SQLite 数据库里，不会连接券商，也不会做真实交易。

## App / PWA

安卓手机访问 `http://电脑IPv4地址:8000` 后，可以在浏览器菜单里选择“添加到主屏幕”。项目已包含：

- `frontend/manifest.webmanifest`
- `frontend/service-worker.js`
- `frontend/icon.svg`
- 移动端底部导航
- 手机适配布局

## 基金功能

当前已实现：

- 基金搜索；
- 基金详情；
- 基金净值走势；
- 100 分基金评分；
- 潜力基金推荐；
- 市场资讯；
- 我的基金相关资讯；
- 模拟买入、卖出；
- 持仓、交易记录；
- 模拟收益统计。

评分和推荐都会显示“仅供学习和模拟研究，不构成投资建议”。

## 数据源说明

系统采用可替换数据源层：

- 优先使用 AKShare 能获取到的公开基金和资讯数据；
- AKShare 或上游公开接口失败时，自动显示本地示例数据；
- 不破解支付宝、养基宝或任何平台接口；
- 不绕过风控；
- 后续可以在 `backend/fund_data.py` 和 `backend/news_data.py` 中替换为正式授权 API。

## 主要新增接口

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/logout

GET  /api/funds/search?q=关键词
GET  /api/funds/{symbol}
GET  /api/funds/{symbol}/score
GET  /api/funds/recommendations

GET  /api/news/market
GET  /api/news/my-funds

POST /api/sim/account
GET  /api/sim/performance
```

## 添加自选

在“添加自选”区域填写：

- 代码：如 `600519`、`510300`、`000001`
- 名称：如 `贵州茅台`、`沪深300ETF`
- 类型：股票 / ETF / 场外基金 / 指数
- 备注：可选

点击“添加”后，自选列表会拉取 AKShare 行情。接口失败时页面会显示错误，不会白屏。

## 模拟买入

在自选列表或持仓列表点击“买入”，填写价格、数量/份额和手续费。当前手续费默认为 0，但数据表已保留 `fee` 字段。

买入规则：

- 买入金额 = 买入价格 × 数量
- 现金不足时禁止买入
- 已有持仓会自动重新计算平均成本
- 买入成功后扣减现金并写入交易记录

## 模拟卖出

在自选列表或持仓列表点击“卖出”，填写卖出价格和数量/份额。

卖出规则：

- 没有持仓时禁止卖出
- 卖出数量不能超过当前持仓
- 卖出成功后增加现金
- 持仓数量为 0 时自动清仓
- 写入交易记录并计算本次交易盈亏

## 行情刷新

- 页面每 30 秒自动刷新自选、账户、持仓和主要指数。
- 点击顶部“刷新行情”会手动刷新持仓价格和盈亏。
- AKShare 某个接口临时不可用时，系统会返回清晰错误信息。

## 常见报错处理

### `ModuleNotFoundError: No module named 'fastapi'`

说明依赖还没安装。进入 `backend` 目录后执行：

```powershell
pip install -r requirements.txt
```

### `AKShare 未安装或导入失败`

重新安装依赖：

```powershell
pip install -r requirements.txt
```

### 行情获取失败

AKShare 的上游数据源偶尔会限流、维护或调整字段。系统不会崩溃，会在页面显示失败原因。稍后刷新即可。

### 手机打不开页面

检查三点：

- 手机和电脑是否在同一个 Wi-Fi；
- 启动命令是否包含 `--host 0.0.0.0`；
- Windows 防火墙是否允许 Python 访问专用网络。

### 页面提示未登录

这是正常状态。先注册或登录账号，再进入仪表盘。

### 数据库写入提示 disk I/O error

某些受限 Windows 目录会阻止 SQLite 创建或删除 journal 临时文件。当前项目已自动启用本地兼容模式；如果旧的 `marketsim.db-journal` 无法删除，系统会自动使用 `backend/data/marketsim_runtime.db` 作为运行数据库。

## 测试方法

启动后按这个顺序测：

1. 打开 `http://127.0.0.1:8000`；
2. 注册一个新账号；
3. 刷新页面，确认仍保持登录；
4. 搜索基金，例如 `消费` 或 `000001`；
5. 打开基金详情评分；
6. 加入自选；
7. 模拟买入；
8. 查看持仓、交易记录和收益统计；
9. 打开市场资讯和我的基金相关资讯；
10. 手机访问 `http://电脑IPv4地址:8000`，登录同一账号确认数据一致。

### 端口 8000 被占用

换一个端口启动，例如：

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

然后浏览器访问 `http://127.0.0.1:8010`，手机访问 `http://电脑IPv4地址:8010`。

## 后续扩展预留

当前代码已经把数据库模型、行情获取、模拟交易和 API 路由拆开，后续可以继续扩展：

- AI 复盘；
- 策略提醒；
- 基金定投模拟；
- 历史净值和收益曲线；
- 更细的交易手续费规则。

## 每日自动模拟操作

系统有“每日操作”栏目，可以设置每天 `02:55` 自动生成模拟操作记录。它只会做学习和模拟研究记录，不会真实买卖基金。

邮件发送功能已移除，操作记录统一保存在本地系统里。进入网页底部的“自动”栏目，点击“立即执行一次”即可手动生成一条记录；开启自动执行后，服务运行期间会按设置时间生成记录。
