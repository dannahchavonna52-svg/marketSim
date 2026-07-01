const finalPageGroups = {
  home: ["dashboard", "indices"],
  funds: ["fundSearch", "fundDetail", "addWatch"],
  recommend: ["recommendations"],
  mine: ["watchlist", "positions", "myAnalysis", "myFundNews", "performance"],
  news: ["marketNews"],
  trade: ["trades", "settings"],
  auto: ["dailyOps"],
  advisor: ["advisorSim"],
};

let finalRecommendationPayload = null;
let advisorChart = null;
let fundNavChart = null;
let activeFundHistory = [];
let activeFundRange = "6m";
const finalRecTabs = [
  ["today", "今日"],
  ["week", "本周"],
  ["undervalued", "低估"],
  ["stable", "稳健"],
  ["growth", "成长"],
  ["beginner", "新手"],
  ["avoid_chasing", "别追高"],
];

function showPage(page = "home") {
  Object.values(finalPageGroups).flat().forEach((id) => document.querySelector(`#${id}`)?.classList.add("page-hidden"));
  (finalPageGroups[page] || finalPageGroups.home).forEach((id) => document.querySelector(`#${id}`)?.classList.remove("page-hidden"));
  document.querySelectorAll("#bottomNav button").forEach((btn) => btn.classList.toggle("active", btn.dataset.page === page));
  setTimeout(() => {
    fundNavChart?.resize();
    advisorChart?.resize();
    performanceChart?.resize();
  }, 60);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function sparklineSvg(points) {
  const rows = (points || []).filter((item) => !Number.isNaN(Number(item.nav))).slice(-45);
  if (rows.length < 2) return `<div class="sparkline empty">暂无走势</div>`;
  const values = rows.map((item) => Number(item.nav));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const d = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = 34 - ((value - min) / range) * 28;
      return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const first = values[0];
  const last = values[values.length - 1];
  const trendClass = last >= first ? "up" : "down";
  const change = ((last / first - 1) * 100).toFixed(2);
  return `
    <div class="sparkline ${trendClass}">
      <svg viewBox="0 0 100 38" preserveAspectRatio="none" aria-hidden="true">
        <path class="area" d="${d} L100,38 L0,38 Z"></path>
        <path class="line" d="${d}"></path>
      </svg>
      <span>近45点 ${change}%</span>
    </div>
  `;
}

function historyByRange(history, range = "6m") {
  const rows = (history || []).filter((item) => !Number.isNaN(Number(item.nav)) && Number(item.nav) > 0);
  const sizeMap = { "1m": 22, "3m": 66, "6m": 132, "1y": 252, all: rows.length };
  const size = sizeMap[range] || sizeMap["6m"];
  return rows.slice(-size);
}

function rangeReturn(history) {
  const rows = (history || []).filter((item) => Number(item.nav) > 0);
  if (rows.length < 2) return "--";
  const first = Number(rows[0].nav);
  const last = Number(rows[rows.length - 1].nav);
  return `${((last / first - 1) * 100).toFixed(2)}%`;
}

function rangeDrawdown(history) {
  let peak = 0;
  let drawdown = 0;
  for (const row of history || []) {
    const nav = Number(row.nav || 0);
    if (!nav) continue;
    peak = Math.max(peak, nav);
    if (peak) drawdown = Math.min(drawdown, (nav / peak - 1) * 100);
  }
  return `${drawdown.toFixed(2)}%`;
}

function renderFundNavChart(history = activeFundHistory, range = activeFundRange) {
  const el = document.querySelector("#fundNavChart");
  if (!el) return;
  activeFundHistory = history || [];
  activeFundRange = range || "6m";
  const rows = historyByRange(activeFundHistory, activeFundRange);
  document.querySelectorAll("[data-fund-range]").forEach((btn) => btn.classList.toggle("active", btn.dataset.fundRange === activeFundRange));
  const stats = document.querySelector("#fundChartStats");
  if (stats) {
    stats.textContent = rows.length >= 2 ? `区间收益 ${rangeReturn(rows)} · 区间最大回撤 ${rangeDrawdown(rows)} · ${rows[0].date} 至 ${rows[rows.length - 1].date}` : "暂无足够走势数据";
  }
  if (!window.echarts) {
    el.innerHTML = `<div class="muted" style="padding:16px;">走势图组件未加载</div>`;
    return;
  }
  if (rows.length < 2) {
    el.innerHTML = `<div class="muted" style="padding:16px;">暂无足够净值走势数据</div>`;
    return;
  }
  if (!fundNavChart) {
    fundNavChart = echarts.init(el);
    window.addEventListener("resize", () => fundNavChart?.resize());
  }
  const navs = rows.map((item) => Number(item.nav || 0));
  const changes = rows.map((item) => Number(item.change_percent || 0));
  const last = rows[rows.length - 1];
  fundNavChart.setOption(
    {
      animation: false,
      tooltip: {
        trigger: "axis",
        formatter(params) {
          const nav = params.find((item) => item.seriesName === "单位净值");
          const change = params.find((item) => item.seriesName === "日涨跌幅");
          return `${params[0].axisValue}<br/>单位净值：${Number(nav?.value ?? 0).toFixed(4)}<br/>日涨跌幅：${Number(change?.value ?? 0).toFixed(2)}%`;
        },
      },
      legend: { top: 8, right: 10, data: ["单位净值", "日涨跌幅"] },
      grid: { left: 48, right: 46, top: 48, bottom: 58 },
      dataZoom: [
        { type: "inside", xAxisIndex: [0], filterMode: "none" },
        { type: "slider", height: 20, bottom: 20 },
      ],
      xAxis: { type: "category", data: rows.map((item) => item.date), boundaryGap: false },
      yAxis: [
        { type: "value", scale: true, name: "净值" },
        { type: "value", scale: true, name: "%", splitLine: { show: false } },
      ],
      series: [
        {
          name: "单位净值",
          type: "line",
          smooth: true,
          symbol: "none",
          data: navs,
          lineStyle: { width: 2.4, color: "#2563eb" },
          areaStyle: { color: "rgba(37, 99, 235, 0.10)" },
          markPoint: {
            symbolSize: 44,
            data: [{ name: "最新", coord: [last.date, Number(last.nav || 0)], value: Number(last.nav || 0).toFixed(4) }],
          },
        },
        {
          name: "日涨跌幅",
          type: "bar",
          yAxisIndex: 1,
          data: changes,
          itemStyle: { color: (params) => (Number(params.value) >= 0 ? "#dc2626" : "#16a34a") },
          opacity: 0.36,
        },
      ],
    },
    true
  );
  setTimeout(() => fundNavChart?.resize(), 40);
}

function compactAdvice(advice) {
  if (!advice) return "";
  return `
    <div class="decision-card">
      <div>
        <span>当前结论</span>
        <strong>${escapeHtml(advice.action || "观察")}</strong>
      </div>
      <p>${escapeHtml(advice.reason_sentence || advice.plain_explanation || "")}</p>
      <div class="mini-index">
        <b class="buy">买 ${numberText(advice.buy_index, 1)}</b>
        <b class="hold">持 ${numberText(advice.hold_index, 1)}</b>
        <b class="sell">卖 ${numberText(advice.sell_index, 1)}</b>
      </div>
    </div>
  `;
}

function cleanFundText(value, fallback = "资料待补全") {
  const text = String(value || "").trim();
  if (!text || ["公开数据暂缺", "暂无数据", "null", "undefined"].includes(text)) return fallback;
  return text;
}

function adviceBars(advice) {
  return compactAdvice(advice);
}

function renderRecommendationTab(key = "today") {
  const buckets = finalRecommendationPayload?.recommendations || {};
  const rows = buckets[key] || [];
  const recTabs = [
    ["today", "今日"],
    ["week", "本周"],
    ["undervalued", "低位关注"],
    ["stable", "稳健"],
    ["growth", "成长"],
    ["beginner", "新手"],
    ["avoid_chasing", "别追高"],
  ];
  document.querySelector("#recommendationBody").innerHTML = `
    <div class="rec-tabs">
      ${recTabs.map(([tab, label]) => `<button type="button" data-rec-tab="${tab}" class="${tab === key ? "active" : ""}">${label}</button>`).join("")}
    </div>
    <div class="fund-grid">
      ${
        rows.length
          ? rows
              .map(
                (item) => `
                  <article class="fund-card">
                    <h3>${escapeHtml(item.name)} <span class="tag score-pill">${item.score} 分</span></h3>
                    <p>${escapeHtml(item.symbol)} · ${escapeHtml(item.grade)} · 净值 ${numberText(item.latest_nav, 4)} · 日涨跌 ${pct(item.daily_change)}</p>
                    ${sparklineSvg(item.trend)}
                    ${compactAdvice(item)}
                    <p>${escapeHtml(item.reason)}</p>
                    <button class="secondary-btn" data-fund-detail="${escapeHtml(item.symbol)}">查看详情</button>
                  </article>
                `
              )
              .join("")
          : `<article class="fund-card"><p>暂无数据</p></article>`
      }
    </div>
  `;
}

function renderRecommendations(data) {
  finalRecommendationPayload = data;
  renderRecommendationTab("today");
}

function renderFundDetail(payload) {
  const fund = payload.detail.fund;
  const score = payload.score;
  const advice = payload.advice;
  document.querySelector("#fundDetailBody").innerHTML = `
    <article class="score-card wide-card">
      <h3>${escapeHtml(fund.name)} <span class="tag score-pill">${score.total_score} 分 · ${escapeHtml(score.grade)}</span></h3>
      <p>${escapeHtml(fund.symbol)} · ${escapeHtml(cleanFundText(fund.fund_type, "公募基金"))} · ${escapeHtml(cleanFundText(fund.company))}</p>
      ${sparklineSvg(fund.history)}
      ${compactAdvice(advice)}
      ${cardTags([`最新净值 ${numberText(fund.latest_nav, 4)}`, `日涨跌 ${pct(fund.daily_change)}`, `近1月 ${pct(fund.month_return)}`, `最大回撤 ${pct(fund.max_drawdown)}`, `经理 ${cleanFundText(fund.manager)}`])}
      <p><b>买入理由：</b>${escapeHtml(advice?.reason_sentence || score.buy_reason)}</p>
      <p><b>风险提示：</b>${escapeHtml(score.risk_note)}</p>
      <p class="disclaimer">${escapeHtml(score.disclaimer)}</p>
    </article>
  `;
  renderFundNavChart(fund.history || []);
  showPage("funds");
  document.querySelector("#fundDetail").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderMyAnalysis(data) {
  const box = document.querySelector("#myAnalysisList");
  const hint = document.querySelector("#myAnalysisHint");
  if (!box) return;
  const rows = data?.items || [];
  hint.textContent = `更新于 ${data?.updated_at || "--"}`;
  if (!rows.length) {
    box.innerHTML = `<article class="fund-card"><p>还没有基金。先搜索并加入自选，或模拟买入后这里会自动分析。</p></article>`;
    return;
  }
  box.innerHTML = rows
    .map((item) => {
      const fund = item.fund || {};
      const pos = item.position;
      const profit = pos ? `<p>持仓收益：<b class="${tone(pos.profit)}">${money(pos.profit)}</b> · ${pct(pos.profit_rate)}</p>` : `<p class="muted">自选基金，暂未买入</p>`;
      return `
        <article class="fund-card">
          <h3>${escapeHtml(fund.name)} <span class="tag">${item.relation === "position" ? "已买入" : "自选"}</span></h3>
          <p>${escapeHtml(fund.symbol)} · 最新净值 ${numberText(fund.latest_nav, 4)} · 日涨跌 ${pct(fund.daily_change)}</p>
          ${sparklineSvg(fund.history)}
          ${profit}
          ${compactAdvice(item.advice)}
          <button class="secondary-btn" data-fund-detail="${escapeHtml(fund.symbol)}">查看详情</button>
        </article>
      `;
    })
    .join("");
}

async function loadFundHome(refresh = false) {
  try {
    const [recommendations, news, myNews, performance, myAnalysis] = await Promise.all([
      pageApi(`/api/funds/recommendations${refresh ? "?refresh=true" : ""}`),
      pageApi(`/api/news/market${refresh ? "?refresh=true&limit=50" : "?limit=50"}`),
      pageApi("/api/news/my-funds"),
      pageApi("/api/sim/performance"),
      pageApi(`/api/funds/my-analysis${refresh ? "?refresh=true" : ""}`),
    ]);
    renderRecommendations(recommendations);
    renderNews(news.news || [], "#newsList");
    renderNews(myNews.matched || [], "#myNewsList");
    renderMyAnalysis(myAnalysis);
    renderPerformance(performance);
    document.querySelector("#newsHint").textContent = `共 ${news.count || (news.news || []).length} 条，更新于 ${news.updated_at || "--"}`;
    document.querySelector("#recommendationHint").textContent = `带近期走势图，更新于 ${recommendations.updated_at || "--"}`;
  } catch (error) {
    pageToast(error.message);
  }
}

function ensureFinalTools() {
  const analysisTitle = document.querySelector("#myAnalysis .section-title");
  if (analysisTitle && !document.querySelector("#refreshMyAnalysisBtn")) {
    analysisTitle.insertAdjacentHTML("beforeend", `<button id="refreshMyAnalysisBtn" class="secondary-btn" type="button">刷新分析</button>`);
  }
}

ensureFinalTools();
showPage("home");

function renderDailyOpsLogs(logs) {
  const box = document.querySelector("#dailyOpsLogs");
  if (!box) return;
  if (!logs.length) {
    box.innerHTML = `<article class="news-card"><p>暂无每日操作记录。可以点“立即执行一次”先生成一条。</p></article>`;
    return;
  }
  box.innerHTML = logs
    .map((log) => {
      const decisions = log.detail?.decisions || [];
      const statusText = {
        disabled: "已保存到本地",
        sent: "已保存到本地",
        failed: "已保存到本地",
        not_configured: "已保存到本地",
        skipped: "已保存到本地",
      }[log.email_status] || "已保存到本地";
      return `
        <article class="news-card">
          <h3>${escapeHtml(log.run_date)} 模拟操作记录</h3>
          <p>${escapeHtml(log.summary)}</p>
          <p class="muted">${escapeHtml(statusText)}</p>
          <div class="daily-decision-list">
            ${decisions
              .slice(0, 8)
              .map(
                (item) => `
                  <div>
                    <b>${escapeHtml(item.name)} ${escapeHtml(item.symbol)}</b>
                    <span>${escapeHtml(item.action)} · 买 ${numberText(item.buy_index, 1)} / 持 ${numberText(item.hold_index, 1)} / 卖 ${numberText(item.sell_index, 1)}</span>
                    <p>${escapeHtml(item.reason || "")}</p>
                    ${
                      (item.evidence || []).length
                        ? `<div class="evidence-list compact"><b>依据</b>${item.evidence.slice(0, 3).map((ev) => `<span>${escapeHtml(ev)}</span>`).join("")}</div>`
                        : ""
                    }
                    ${
                      (item.risk_flags || []).length
                        ? `<div class="risk-list compact"><b>风险</b>${item.risk_flags.slice(0, 2).map((ev) => `<span>${escapeHtml(ev)}</span>`).join("")}</div>`
                        : ""
                    }
                  </div>
                `
              )
              .join("")}
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadDailyOps() {
  try {
    const [settings, logs] = await Promise.all([pageApi("/api/daily-ops/settings"), pageApi("/api/daily-ops/logs")]);
    document.querySelector("#dailyOpsEnabled").checked = Boolean(settings.enabled);
    document.querySelector("#dailyOpsTime").value = settings.run_time || "02:55";
    document.querySelector("#dailyOpsHint").textContent = settings.enabled
      ? `已开启，每天 ${settings.run_time || "02:55"} 执行`
      : "未开启自动执行";
    renderDailyOpsLogs(logs.logs || []);
  } catch (error) {
    pageToast(error.message);
  }
}

document.addEventListener("click", async (event) => {
  const pageBtn = event.target.closest("#bottomNav button[data-page]");
  if (pageBtn) {
    const page = pageBtn.dataset.page;
    showPage(page);
    if (page === "advisor") await loadAdvisorSim();
    if (page === "auto") await loadDailyOps();
    if (["recommend", "mine", "news"].includes(page)) await loadFundHome(false);
  }
  const recBtn = event.target.closest("[data-rec-tab]");
  if (recBtn) renderRecommendationTab(recBtn.dataset.recTab);
  const rangeBtn = event.target.closest("[data-fund-range]");
  if (rangeBtn) {
    renderFundNavChart(activeFundHistory, rangeBtn.dataset.fundRange);
  }
  if (event.target.closest("#refreshMyAnalysisBtn")) {
    pageToast("正在刷新我的基金分析...");
    const data = await pageApi("/api/funds/my-analysis?refresh=true");
    renderMyAnalysis(data);
  }
  if (event.target.closest("#runDailyOpsBtn")) {
    pageToast("正在生成每日模拟操作记录...");
    showPage("auto");
    await pageApi("/api/daily-ops/run", { method: "POST" });
    await loadDailyOps();
  }
  if (event.target.closest("#refreshAdvisorSimBtn")) {
    pageToast("正在刷新系统模拟结果...");
    showPage("advisor");
    await loadAdvisorSim();
  }
  if (event.target.closest("#runAdvisorSimBtn")) {
    pageToast("系统正在根据最新数据执行模拟操作...");
    showPage("advisor");
    const result = await pageApi("/api/advisor-sim/run", { method: "POST" });
    pageToast(result.message || "系统模拟操作已完成");
    await loadAdvisorSim();
  }
});

document.querySelector("#dailyOpsForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await pageApi("/api/daily-ops/settings", {
      method: "POST",
      body: JSON.stringify({
        enabled: document.querySelector("#dailyOpsEnabled").checked,
        run_time: document.querySelector("#dailyOpsTime").value || "02:55",
        email: "",
      }),
    });
    pageToast("每日操作设置已保存");
    await loadDailyOps();
  } catch (error) {
    pageToast(error.message);
  }
});

document.addEventListener("marketsim:login", () => {
  showPage("home");
  loadDailyOps();
  loadAdvisorSim();
});

setTimeout(() => {
  if (typeof pageToken === "function" && pageToken()) {
    loadDailyOps();
    loadAdvisorSim();
  }
}, 600);

function renderAdvisorCurve(rows) {
  const el = document.querySelector("#advisorCurve");
  if (!el || !window.echarts) return;
  const dataRows = rows || [];
  if (!dataRows.length) {
    el.innerHTML = `<div class="muted" style="padding:16px;">暂无收益曲线，先执行一次系统模拟操作。</div>`;
    return;
  }
  if (!advisorChart) {
    advisorChart = echarts.init(el);
    window.addEventListener("resize", () => advisorChart?.resize());
  }
  advisorChart.setOption(
    {
      animation: false,
      title: { text: "系统模拟收益曲线", left: 14, top: 12, textStyle: { fontSize: 14, fontWeight: 700 } },
      tooltip: {
        trigger: "axis",
        formatter(params) {
          const asset = params.find((item) => item.seriesName === "总资产");
          const rate = params.find((item) => item.seriesName === "收益率");
          return `${params[0].axisValue}<br/>总资产：${money(asset?.value)}<br/>收益率：${pct(rate?.value)}`;
        },
      },
      legend: { top: 12, right: 12, data: ["总资产", "收益率"] },
      grid: { left: 52, right: 54, top: 54, bottom: 36 },
      xAxis: { type: "category", data: dataRows.map((item) => String(item.time || "").slice(5, 16)) },
      yAxis: [
        { type: "value", scale: true, name: "资产" },
        { type: "value", scale: true, name: "%", splitLine: { show: false } },
      ],
      series: [
        {
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 5,
          name: "总资产",
          data: dataRows.map((item) => Number(item.total_asset || 0)),
          lineStyle: { color: "#2563eb", width: 2.4 },
          areaStyle: { color: "rgba(37,99,235,.10)" },
        },
        {
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          symbol: "none",
          name: "收益率",
          data: dataRows.map((item) => Number(item.profit_rate || 0)),
          lineStyle: { color: "#dc2626", width: 2 },
        },
      ],
    },
    true
  );
  setTimeout(() => advisorChart?.resize(), 40);
}

function renderSmartMoneySignals(signals) {
  const box = document.querySelector("#smartMoneySignals");
  if (!box) return;
  const flows = signals?.flows || [];
  const dynamics = signals?.dynamics || [];
  box.innerHTML = `
    <article class="news-card">
      <h3>行业资金流观察</h3>
      ${
        flows.length
          ? flows
              .slice(0, 8)
              .map((item) => `<p><b>${escapeHtml(item.name)}</b> · 热度 ${escapeHtml(item.heat || "--")} · 涨跌 ${pct(item.change_percent)} · ${escapeHtml(item.hint || "")}</p>`)
              .join("")
          : "<p>暂无行业资金流数据</p>"
      }
    </article>
    <article class="news-card">
      <h3>行业动态</h3>
      ${
        dynamics.length
          ? dynamics
              .slice(0, 6)
              .map((item) => `<p><b>${escapeHtml(item.direction || "观察")}</b> · ${escapeHtml(item.title || "")}</p>`)
              .join("")
          : "<p>暂无行业动态</p>"
      }
    </article>
  `;
}

function renderAdvisorSim(data) {
  const summary = data.summary || {};
  document.querySelector("#advisorTotalAsset").textContent = money(summary.total_asset);
  document.querySelector("#advisorProfit").textContent = money(summary.profit);
  document.querySelector("#advisorProfit").className = tone(summary.profit);
  document.querySelector("#advisorProfitRate").textContent = pct(summary.profit_rate);
  document.querySelector("#advisorProfitRate").className = tone(summary.profit_rate);
  document.querySelector("#advisorCash").textContent = money(summary.cash);
  document.querySelector("#advisorSimHint").textContent = `更新于 ${summary.updated_at || "--"}，系统持仓 ${summary.position_count || 0} 只`;

  renderAdvisorCurve(data.curve || []);
  renderSmartMoneySignals(data.signals || {});

  const posBox = document.querySelector("#advisorPositions");
  const positions = data.positions || [];
  posBox.innerHTML = positions.length
    ? positions
        .map(
          (item) => `
            <article class="fund-card">
              <h3>${escapeHtml(item.name)} <span class="tag">${escapeHtml(item.symbol)}</span></h3>
              <p>市值 ${money(item.market_value)} · 收益 <b class="${tone(item.profit)}">${money(item.profit)}</b> · ${pct(item.profit_rate)}</p>
              ${cardTags([`成本 ${numberText(item.avg_cost, 4)}`, `现净值 ${numberText(item.current_nav, 4)}`, item.last_action || "观察"])}
            </article>
          `
        )
        .join("")
    : `<article class="fund-card"><p>系统暂未持仓。点“执行一次系统模拟操作”后，如果信号达到阈值，会自动生成模拟买入。</p></article>`;

  const tradeBox = document.querySelector("#advisorTrades");
  const trades = data.trades || [];
  tradeBox.innerHTML = trades.length
    ? trades
        .map(
          (item) => `
            <article class="news-card">
              <h3>${escapeHtml(item.side === "buy" ? "系统模拟买入" : "系统模拟减仓")} · ${escapeHtml(item.name)}</h3>
              <p>${escapeHtml(item.symbol)} · 金额 ${money(item.amount)} · 净值 ${numberText(item.price, 4)} · ${String(item.created_at || "").replace("T", " ").slice(0, 19)}</p>
              <p>${escapeHtml(item.reason)}</p>
              ${
                (item.evidence || []).length
                  ? `<div class="evidence-list"><b>依据</b>${item.evidence.slice(0, 5).map((ev) => `<span>${escapeHtml(ev)}</span>`).join("")}</div>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : `<article class="news-card"><p>暂无系统操作记录。</p></article>`;
}

let performanceChart = null;

function renderPerformance(data) {
  const el = document.querySelector("#performanceChart");
  if (!el || !window.echarts) return;
  const rows = data?.curve || [];
  if (!rows.length) {
    el.innerHTML = `<div class="muted" style="padding:16px;">暂无收益曲线，先完成一笔模拟买入。</div>`;
    return;
  }
  if (!performanceChart) {
    performanceChart = echarts.init(el);
    window.addEventListener("resize", () => performanceChart?.resize());
  }
  performanceChart.setOption(
    {
      animation: false,
      title: { text: "我的模拟收益曲线", left: 14, top: 12, textStyle: { fontSize: 14, fontWeight: 700 } },
      tooltip: {
        trigger: "axis",
        formatter(params) {
          const asset = params.find((item) => item.seriesName === "总资产");
          const rate = params.find((item) => item.seriesName === "收益率");
          return `${params[0].axisValue}<br/>总资产：${money(asset?.value)}<br/>收益率：${pct(rate?.value)}`;
        },
      },
      legend: { top: 12, right: 12, data: ["总资产", "收益率"] },
      grid: { left: 52, right: 54, top: 54, bottom: 36 },
      xAxis: { type: "category", data: rows.map((item) => item.label) },
      yAxis: [
        { type: "value", scale: true, name: "资产" },
        { type: "value", scale: true, name: "%", splitLine: { show: false } },
      ],
      series: [
        {
          name: "总资产",
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 5,
          data: rows.map((item) => Number(item.asset || 0)),
          lineStyle: { color: "#2563eb", width: 2.4 },
          areaStyle: { color: "rgba(37,99,235,.10)" },
        },
        {
          name: "收益率",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          symbol: "none",
          data: rows.map((item) => Number(item.return_rate || 0)),
          lineStyle: { color: "#dc2626", width: 2 },
        },
      ],
    },
    true
  );
  setTimeout(() => performanceChart?.resize(), 40);
}

async function loadAdvisorSim() {
  try {
    const data = await pageApi("/api/advisor-sim");
    renderAdvisorSim(data);
  } catch (error) {
    pageToast(error.message);
  }
}

window.MarketSimFinal = {
  loadAdvisorSim,
  loadDailyOps,
  loadFundHome,
  renderFundNavChart,
};

function renderIndices(data) {
  const rows = data.indices || [];
  const lastText = data.last_success_at ? `上次成功：${data.last_success_at}` : "";
  els.indexHint.textContent = data.errors?.length ? `${lastText || "实时获取失败"}，显示可用缓存` : lastText;
  els.indicesBody.innerHTML = rows
    .map((item) => {
      const timeText = item.is_stale ? `上次：${escapeHtml(item.update_time || data.last_success_at || "--")}` : escapeHtml(item.update_time || "--");
      const note = item.is_stale ? `<div class="warn">${escapeHtml(item.error || "非实时数据")}</div>` : "";
      return `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.symbol)}</td>
          <td>${numberText(item.price, 3)}</td>
          <td class="${tone(item.change_percent)}">${pct(item.change_percent)}</td>
          <td class="${item.is_stale ? "warn" : "muted"}">${timeText}${note}</td>
        </tr>
      `;
    })
    .join("");
}

// Data-first UI overrides. These are loaded last and keep the interface focused
// on evidence: data freshness, buy/hold/sell indices, reasons and risk flags.
function compactAdvice(advice) {
  if (!advice) return "";
  const evidence = (advice.evidence || advice.reasons || []).slice(0, 3);
  const risks = (advice.risk_flags || []).slice(0, 3);
  return `
    <div class="decision-card data-decision">
      <div>
        <span>当前结论</span>
        <strong>${escapeHtml(advice.action || "观察")}</strong>
      </div>
      <p>${escapeHtml(advice.reason_sentence || advice.plain_explanation || "")}</p>
      <div class="mini-index">
        <b class="buy">买 ${numberText(advice.buy_index, 1)}</b>
        <b class="hold">持 ${numberText(advice.hold_index, 1)}</b>
        <b class="sell">卖 ${numberText(advice.sell_index, 1)}</b>
      </div>
      ${
        evidence.length
          ? `<div class="evidence-list"><b>依据</b>${evidence.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`
          : ""
      }
      ${
        risks.length
          ? `<div class="risk-list"><b>风险</b>${risks.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`
          : ""
      }
    </div>
  `;
}

function renderRecommendationTab(key = "today") {
  const buckets = finalRecommendationPayload?.recommendations || {};
  const rows = buckets[key] || [];
  document.querySelector("#recommendationBody").innerHTML = `
    <div class="rec-tabs">
      ${finalRecTabs.map(([tab, label]) => `<button type="button" data-rec-tab="${tab}" class="${tab === key ? "active" : ""}">${label}</button>`).join("")}
    </div>
    <div class="fund-grid">
      ${
        rows.length
          ? rows
              .map(
                (item) => `
                  <article class="fund-card">
                    <h3>${escapeHtml(item.name)} <span class="tag score-pill">${numberText(item.score, 1)} 分</span></h3>
                    <p>${escapeHtml(item.symbol)} · ${escapeHtml(item.grade)} · 净值 ${numberText(item.latest_nav, 4)} · 日涨跌 ${pct(item.daily_change)}</p>
                    ${sparklineSvg(item.trend)}
                    ${cardTags([`近1月 ${pct(item.month_return)}`, `买入 ${numberText(item.buy_index, 1)}`, `持有 ${numberText(item.hold_index, 1)}`, `减仓 ${numberText(item.sell_index, 1)}`])}
                    ${compactAdvice(item)}
                    <p><b>推荐理由：</b>${escapeHtml(item.reason || "公开数据不足，先观察。")}</p>
                    <p><b>主要风险：</b>${escapeHtml(item.risk || "暂无明确风险信号，但不代表没有波动。")}</p>
                    <button class="secondary-btn" data-fund-detail="${escapeHtml(item.symbol)}">查看详情</button>
                  </article>
                `
              )
              .join("")
          : `<article class="fund-card"><p>暂无数据，点刷新后再试。</p></article>`
      }
    </div>
  `;
}

function renderFundDetail(payload) {
  const fund = payload.detail.fund;
  const score = payload.score;
  const advice = payload.advice;
  const errors = payload.detail.errors || [];
  document.querySelector("#fundDetailBody").innerHTML = `
    <article class="score-card wide-card">
      <h3>${escapeHtml(fund.name)} <span class="tag score-pill">${numberText(score.total_score, 1)} 分 · ${escapeHtml(score.grade)}</span></h3>
      <p>${escapeHtml(fund.symbol)} · ${escapeHtml(cleanFundText(fund.fund_type, "公募基金"))} · ${escapeHtml(cleanFundText(fund.company))}</p>
      ${sparklineSvg(fund.history)}
      ${compactAdvice(advice)}
      ${cardTags([
        `最新净值 ${numberText(fund.latest_nav, 4)}`,
        `估算净值 ${numberText(fund.estimated_nav, 4)}`,
        `日涨跌 ${pct(fund.daily_change)}`,
        `近1月 ${pct(fund.month_return)}`,
        `近1年 ${pct(fund.year_return)}`,
        `最大回撤 ${pct(fund.max_drawdown)}`,
        `经理 ${cleanFundText(fund.manager)}`,
      ])}
      <p><b>行业线索：</b>${escapeHtml(cleanFundText(fund.industries))}</p>
      <p><b>买入判断：</b>${escapeHtml(advice?.reason_sentence || score.buy_reason)}</p>
      <p><b>风险提示：</b>${escapeHtml(score.risk_note)}</p>
      <div class="chart-toolbar">
        <div class="range-tabs">
          <button type="button" data-fund-range="1m">1月</button>
          <button type="button" data-fund-range="3m">3月</button>
          <button type="button" data-fund-range="6m" class="active">6月</button>
          <button type="button" data-fund-range="1y">1年</button>
          <button type="button" data-fund-range="all">全部</button>
        </div>
        <span id="fundChartStats" class="muted">正在加载走势...</span>
      </div>
      ${errors.length ? `<p class="warn">部分字段暂缺：${escapeHtml(errors.slice(0, 2).join("；"))}</p>` : ""}
      <p class="muted">数据来源：${escapeHtml(fund.data_source || payload.detail.source || "公开基金数据")} · 更新于 ${escapeHtml(fund.updated_at || payload.detail.updated_at || "--")}</p>
      <p class="disclaimer">${escapeHtml(score.disclaimer)}</p>
    </article>
  `;
  showPage("funds");
  renderFundNavChart(fund.history || [], "6m");
  document.querySelector("#fundDetail").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderMyAnalysis(data) {
  const box = document.querySelector("#myAnalysisList");
  const hint = document.querySelector("#myAnalysisHint");
  if (!box) return;
  const rows = data?.items || [];
  hint.textContent = `净值和资讯更新于 ${data?.updated_at || "--"}`;
  if (!rows.length) {
    box.innerHTML = `<article class="fund-card"><p>还没有基金。先搜索并加入自选，或模拟买入后这里会自动分析。</p></article>`;
    return;
  }
  box.innerHTML = rows
    .map((item) => {
      const fund = item.fund || {};
      const pos = item.position;
      const profit = pos
        ? `<p>持仓收益：<b class="${tone(pos.profit)}">${money(pos.profit)}</b> · ${pct(pos.profit_rate)}</p>`
        : `<p class="muted">自选基金，暂未买入</p>`;
      return `
        <article class="fund-card">
          <h3>${escapeHtml(fund.name)} <span class="tag">${item.relation === "position" ? "已买入" : "自选"}</span></h3>
          <p>${escapeHtml(fund.symbol)} · 最新净值 ${numberText(fund.latest_nav, 4)} · 日涨跌 ${pct(fund.daily_change)}</p>
          ${sparklineSvg(fund.history)}
          ${profit}
          ${compactAdvice(item.advice)}
          <p class="muted">关联资讯：${item.related_news_count || 0} 条 · 更新于 ${escapeHtml(item.updated_at || "--")}</p>
          <button class="secondary-btn" data-fund-detail="${escapeHtml(fund.symbol)}">查看详情</button>
        </article>
      `;
    })
    .join("");
}
