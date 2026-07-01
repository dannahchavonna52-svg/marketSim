const PAGE_TOKEN_KEY = "marketsim_token";

function pageToken() {
  return localStorage.getItem(PAGE_TOKEN_KEY) || "";
}

async function pageApi(path, options = {}) {
  const { headers = {}, ...requestOptions } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${pageToken()}`,
      ...headers,
    },
  });
  const result = await response.json().catch(() => null);
  if (!response.ok || !result?.success) {
    throw new Error(result?.message || `请求失败：${response.status}`);
  }
  return result.data;
}

function pageToast(message) {
  if (typeof showToast === "function") showToast(message);
}

function cardTags(items) {
  return `<div class="tag-row">${items.filter(Boolean).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>`;
}

function renderFundResults(funds) {
  const box = document.querySelector("#fundResults");
  if (!funds.length) {
    box.innerHTML = `<div class="fund-card"><p>暂无数据，换个关键词试试。</p></div>`;
    return;
  }
  box.innerHTML = funds
    .map(
      (fund) => `
        <article class="fund-card">
          <h3>${escapeHtml(fund.name)}</h3>
          <p>${escapeHtml(fund.symbol)} · ${escapeHtml(fund.fund_type || "公募基金")}</p>
          ${cardTags([`净值 ${numberText(fund.latest_nav, 4)}`, `日涨跌 ${pct(fund.daily_change)}`, fund.risk_level])}
          <p>来源：${escapeHtml(fund.data_source || "公开数据")}</p>
          <div class="actions">
            <button class="secondary-btn" data-fund-detail="${escapeHtml(fund.symbol)}">详情评分</button>
            <button class="secondary-btn" data-fund-watch="${escapeHtml(fund.symbol)}" data-name="${escapeHtml(fund.name)}">加自选</button>
            <button class="primary-btn" data-fund-buy="${escapeHtml(fund.symbol)}" data-name="${escapeHtml(fund.name)}" data-nav="${fund.latest_nav || 1}">模拟买入</button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderFundDetail(payload) {
  const fund = payload.detail.fund;
  const score = payload.score;
  const box = document.querySelector("#fundDetailBody");
  box.innerHTML = `
    <article class="score-card">
      <h3>${escapeHtml(fund.name)} <span class="tag score-pill">${score.total_score} 分 · ${escapeHtml(score.grade)}</span></h3>
      <p>${escapeHtml(fund.symbol)} · ${escapeHtml(fund.fund_type)} · ${escapeHtml(fund.company || "暂无基金公司")}</p>
      ${cardTags([`最新净值 ${numberText(fund.latest_nav, 4)}`, `近1月 ${pct(fund.month_return)}`, `近1年 ${pct(fund.year_return)}`, `最大回撤 ${pct(fund.max_drawdown)}`])}
      <p><b>操作参考：</b>${escapeHtml(score.action)}</p>
      <p><b>适合人群：</b>${escapeHtml(score.suitability)}</p>
      <p><b>买入理由：</b>${escapeHtml(score.buy_reason)}</p>
      <p><b>风险提示：</b>${escapeHtml(score.risk_note)}</p>
      <p><b>买入区间：</b>${escapeHtml(score.buy_range)}　<b>止盈：</b>${escapeHtml(score.take_profit_range)}　<b>止损：</b>${escapeHtml(score.stop_loss_range)}</p>
      <p>${escapeHtml(score.disclaimer)}</p>
    </article>
    ${score.dimensions
      .map(
        (item) => `
          <article class="score-card">
            <h3>${escapeHtml(item.name)}：${item.score}/${item.max}</h3>
            <p>${escapeHtml(item.explain)}</p>
          </article>
        `
      )
      .join("")}
  `;
  renderFundNavChart(fund.history || []);
  document.querySelector("#fundDetail").scrollIntoView({ behavior: "smooth", block: "start" });
}

function historyByRange(history, range = "6m") {
  const rows = (history || []).filter((item) => !Number.isNaN(Number(item.nav)) && Number(item.nav) > 0);
  const sizeMap = { "1m": 22, "3m": 66, "6m": 132, "1y": 252, all: rows.length };
  return rows.slice(-(sizeMap[range] || sizeMap["6m"]));
}

function rangeReturn(history) {
  const rows = (history || []).filter((item) => Number(item.nav) > 0);
  if (rows.length < 2) return "--";
  return `${((Number(rows[rows.length - 1].nav) / Number(rows[0].nav) - 1) * 100).toFixed(2)}%`;
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

function renderFundNavChart(history, range = "6m") {
  const el = document.querySelector("#fundNavChart");
  const rows = historyByRange(history || [], range);
  document.querySelectorAll("[data-fund-range]").forEach((btn) => btn.classList.toggle("active", btn.dataset.fundRange === range));
  const stats = document.querySelector("#fundChartStats");
  if (stats) {
    stats.textContent = rows.length >= 2 ? `区间收益 ${rangeReturn(rows)} · 区间最大回撤 ${rangeDrawdown(rows)} · ${rows[0].date} 至 ${rows[rows.length - 1].date}` : "暂无足够走势数据";
  }
  if (!window.echarts) {
    el.innerHTML = `<div class="muted" style="padding:16px;">ECharts 未加载</div>`;
    return;
  }
  if (rows.length < 2) {
    el.innerHTML = `<div class="muted" style="padding:16px;">暂无足够净值走势数据</div>`;
    return;
  }
  const chart = echarts.init(el);
  chart.setOption({
    animation: false,
    title: { text: "净值走势", left: 12, top: 10, textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { top: 10, right: 10, data: ["单位净值", "日涨跌幅"] },
    grid: { left: 48, right: 46, bottom: 44, top: 54 },
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
        data: rows.map((item) => item.nav),
        lineStyle: { color: "#2563eb", width: 2.4 },
        areaStyle: { color: "rgba(37,99,235,.10)" },
      },
      {
        name: "日涨跌幅",
        type: "bar",
        yAxisIndex: 1,
        data: rows.map((item) => Number(item.change_percent || 0)),
        itemStyle: { color: (params) => (Number(params.value) >= 0 ? "#dc2626" : "#16a34a") },
      },
    ],
  });
}

function renderRecommendations(data) {
  const buckets = data.recommendations || {};
  const names = {
    today: "今日推荐基金",
    week: "本周潜力基金",
    undervalued: "低估值关注基金",
    growth: "高成长关注基金",
    stable: "稳健型基金",
    aggressive: "激进型基金",
    beginner: "适合新手的基金",
    avoid_chasing: "不建议追高的基金",
  };
  document.querySelector("#recommendationBody").innerHTML = Object.entries(names)
    .map(([key, title]) => {
      const rows = buckets[key] || [];
      return `
        <article class="score-card">
          <h3>${title}</h3>
          ${
            rows.length
              ? rows
                  .map(
                    (item) => `
                    <div class="fund-card">
                      <h3>${escapeHtml(item.name)} <span class="tag score-pill">${item.score} 分</span></h3>
                      <p>${escapeHtml(item.symbol)} · ${escapeHtml(item.grade)} · ${escapeHtml(item.action)}</p>
                      <p>${escapeHtml(item.reason)}</p>
                      <p>风险：${escapeHtml(item.risk)}</p>
                    </div>
                  `
                  )
                  .join("")
              : `<p>暂无数据</p>`
          }
        </article>
      `;
    })
    .join("");
}

function renderNews(list, selector) {
  const box = document.querySelector(selector);
  if (!list.length) {
    box.innerHTML = `<article class="news-card"><p>暂无数据</p></article>`;
    return;
  }
  box.innerHTML = list
    .map((item) => {
      const news = item.news || item;
      const fundLine = item.fund ? `<p><b>关联基金：</b>${escapeHtml(item.fund.name)} · ${escapeHtml(item.effect)}</p>` : "";
      const reason = item.reason ? `<p><b>关联原因：</b>${escapeHtml(item.reason)}</p>` : "";
      return `
        <article class="news-card">
          <h3>${escapeHtml(news.title)}</h3>
          <p>${escapeHtml(news.source)} · ${escapeHtml(news.published_at)} · 影响程度：${escapeHtml(news.impact_level)}</p>
          ${cardTags([news.impact_direction, `利好 ${news.positive_types}`, `利空 ${news.negative_types}`])}
          <p>${escapeHtml(news.plain_explanation)}</p>
          <p><b>操作参考：</b>${escapeHtml(news.operation_reference)}</p>
          ${fundLine}${reason}
        </article>
      `;
    })
    .join("");
}

function renderPerformance(data) {
  const el = document.querySelector("#performanceChart");
  if (!window.echarts) {
    el.innerHTML = `<div class="muted" style="padding:16px;">ECharts 未加载</div>`;
    return;
  }
  const chart = echarts.init(el);
  chart.setOption({
    title: { text: "模拟收益曲线", left: 12, top: 10, textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 16, bottom: 34, top: 54 },
    xAxis: { type: "category", data: data.curve.map((item) => item.label) },
    yAxis: { type: "value", scale: true },
    series: [{ type: "line", smooth: true, data: data.curve.map((item) => item.asset) }],
  });
}

async function loadFundHome() {
  try {
    const [recommendations, news, myNews, performance] = await Promise.all([
      pageApi("/api/funds/recommendations"),
      pageApi("/api/news/market"),
      pageApi("/api/news/my-funds"),
      pageApi("/api/sim/performance"),
    ]);
    renderRecommendations(recommendations);
    renderNews(news.news || [], "#newsList");
    renderNews(myNews.matched || [], "#myNewsList");
    renderPerformance(performance);
  } catch (error) {
    pageToast(error.message);
  }
}

document.querySelector("#fundSearchForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const keyword = document.querySelector("#fundKeyword").value.trim();
    const data = await pageApi(`/api/funds/search?q=${encodeURIComponent(keyword)}`);
    renderFundResults(data.funds || []);
    document.querySelector("#fundSearchHint").textContent = data.errors?.length ? "部分数据源异常，已显示可用数据" : `更新于 ${data.updated_at}`;
  } catch (error) {
    pageToast(error.message);
  }
});


// Final UX layer: real pages, concise fund recommendations, and live analysis.
const PAGE_GROUPS = {
  home: ["dashboard", "indices"],
  funds: ["fundSearch", "fundDetail", "addWatch"],
  recommend: ["recommendations"],
  mine: ["watchlist", "positions", "myAnalysis", "myFundNews", "performance"],
  news: ["marketNews"],
  trade: ["trades", "settings"],
  auto: ["dailyOps"],
  advisor: ["advisorSim"],
};

function showPage(page = "home") {
  const all = Object.values(PAGE_GROUPS).flat();
  all.forEach((id) => document.querySelector(`#${id}`)?.classList.add("page-hidden"));
  (PAGE_GROUPS[page] || PAGE_GROUPS.home).forEach((id) => document.querySelector(`#${id}`)?.classList.remove("page-hidden"));
  document.querySelectorAll("#bottomNav button").forEach((btn) => btn.classList.toggle("active", btn.dataset.page === page));
  window.scrollTo({ top: 0, behavior: "smooth" });
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

function adviceBars(advice) {
  return compactAdvice(advice);
}

function cleanFundText(value, fallback = "资料待补全") {
  const text = String(value || "").trim();
  if (!text || ["公开数据暂缺", "暂无数据", "null", "undefined"].includes(text)) return fallback;
  return text;
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

function renderFundDetail(payload) {
  const fund = payload.detail.fund;
  const score = payload.score;
  const advice = payload.advice;
  const box = document.querySelector("#fundDetailBody");
  box.innerHTML = `
    <article class="score-card wide-card">
      <h3>${escapeHtml(fund.name)} <span class="tag score-pill">${score.total_score} 分 · ${escapeHtml(score.grade)}</span></h3>
      <p>${escapeHtml(fund.symbol)} · ${escapeHtml(fund.fund_type)} · ${escapeHtml(fund.company || "暂无基金公司")}</p>
      ${compactAdvice(advice)}
      ${cardTags([`最新净值 ${numberText(fund.latest_nav, 4)}`, `日涨跌 ${pct(fund.daily_change)}`, `近1月 ${pct(fund.month_return)}`, `最大回撤 ${pct(fund.max_drawdown)}`])}
      <p><b>买入理由：</b>${escapeHtml(advice?.reason_sentence || score.buy_reason)}</p>
      <p><b>风险提示：</b>${escapeHtml(score.risk_note)}</p>
      <p><b>参考区间：</b>买入 ${escapeHtml(score.buy_range)}　止盈 ${escapeHtml(score.take_profit_range)}　止损 ${escapeHtml(score.stop_loss_range)}</p>
      <p class="disclaimer">${escapeHtml(score.disclaimer)}</p>
    </article>
  `;
  renderFundNavChart(fund.history || []);
  showPage("funds");
  document.querySelector("#fundDetail").scrollIntoView({ behavior: "smooth", block: "start" });
}

let recommendationPayload = null;
const REC_TABS = [
  ["today", "今日"],
  ["week", "本周"],
  ["undervalued", "低估"],
  ["stable", "稳健"],
  ["growth", "成长"],
  ["beginner", "新手"],
  ["avoid_chasing", "别追高"],
];

function renderRecommendationTab(key = "today") {
  const buckets = recommendationPayload?.recommendations || {};
  const rows = buckets[key] || [];
  const body = document.querySelector("#recommendationBody");
  body.innerHTML = `
    <div class="rec-tabs">
      ${REC_TABS.map(([tab, label]) => `<button type="button" data-rec-tab="${tab}" class="${tab === key ? "active" : ""}">${label}</button>`).join("")}
    </div>
    <div class="fund-grid">
      ${
        rows.length
          ? rows
              .map(
                (item) => `
                  <article class="fund-card">
                    <h3>${escapeHtml(item.name)} <span class="tag score-pill">${item.score} 分</span></h3>
                    <p>${escapeHtml(item.symbol)} · ${escapeHtml(item.grade)}</p>
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
  recommendationPayload = data;
  renderRecommendationTab("today");
}

function renderMyAnalysis(data) {
  const box = document.querySelector("#myAnalysisList");
  const hint = document.querySelector("#myAnalysisHint");
  if (!box) return;
  const rows = data?.items || [];
  hint.textContent = `更新于 ${data?.updated_at || "--"}`;
  if (!rows.length) {
    box.innerHTML = `<article class="fund-card"><p>还没有基金。先在“基金”页搜索并加入自选，或模拟买入后这里会自动分析。</p></article>`;
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
          ${profit}
          ${compactAdvice(item.advice)}
          <p>关联资讯：${item.related_news_count || 0} 条</p>
          <button class="secondary-btn" data-fund-detail="${escapeHtml(fund.symbol)}">查看详情</button>
        </article>
      `;
    })
    .join("");
}

async function loadFundHome(refresh = false) {
  try {
    const [recommendations, news, myNews, performance, myAnalysis] = await Promise.all([
      pageApi("/api/funds/recommendations"),
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
    document.querySelector("#recommendationHint").textContent = `精简分页，更新于 ${recommendations.updated_at || "--"}`;
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

document.addEventListener("click", async (event) => {
  const pageBtn = event.target.closest("#bottomNav button[data-page]");
  if (pageBtn) {
    const page = pageBtn.dataset.page;
    showPage(page);
    if (page === "advisor" && window.MarketSimFinal?.loadAdvisorSim) await window.MarketSimFinal.loadAdvisorSim();
    if (page === "auto" && window.MarketSimFinal?.loadDailyOps) await window.MarketSimFinal.loadDailyOps();
    if (["recommend", "mine", "news"].includes(page) && window.MarketSimFinal?.loadFundHome) await window.MarketSimFinal.loadFundHome(false);
  }

  const recBtn = event.target.closest("[data-rec-tab]");
  if (recBtn) renderRecommendationTab(recBtn.dataset.recTab);

  if (event.target.closest("#refreshMyAnalysisBtn")) {
    pageToast("正在刷新我的基金分析...");
    const data = await pageApi("/api/funds/my-analysis?refresh=true");
    renderMyAnalysis(data);
  }
});

document.addEventListener("marketsim:login", () => showPage("home"));

document.addEventListener("click", async (event) => {
  const detailBtn = event.target.closest("[data-fund-detail]");
  const watchBtn = event.target.closest("[data-fund-watch]");
  const buyBtn = event.target.closest("[data-fund-buy]");
  const navBtn = event.target.closest("#bottomNav button[data-target]");

  if (navBtn) {
    document.querySelectorAll("#bottomNav button").forEach((btn) => btn.classList.remove("active"));
    navBtn.classList.add("active");
    document.querySelector(`#${navBtn.dataset.target}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (detailBtn) {
    try {
      const payload = await pageApi(`/api/funds/${encodeURIComponent(detailBtn.dataset.fundDetail)}`);
      renderFundDetail(payload);
    } catch (error) {
      pageToast(error.message);
    }
  }

  if (watchBtn) {
    try {
      await pageApi("/api/watchlist", {
        method: "POST",
        body: JSON.stringify({ symbol: watchBtn.dataset.fundWatch, name: watchBtn.dataset.name, asset_type: "fund", note: "基金关注" }),
      });
      pageToast("已加入自选");
      if (typeof loadAll === "function") await loadAll();
    } catch (error) {
      pageToast(error.message);
    }
  }

  if (buyBtn && typeof openTradeModal === "function") {
    openTradeModal("buy", {
      symbol: buyBtn.dataset.fundBuy,
      name: buyBtn.dataset.name,
      asset_type: "fund",
      price: Number(buyBtn.dataset.nav || 1),
    });
  }
});

document.querySelector("#simAccountForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const initialCash = Number(document.querySelector("#initialCashInput").value);
    await pageApi("/api/sim/account", { method: "POST", body: JSON.stringify({ initial_cash: initialCash }) });
    pageToast("初始资金已设置");
    if (typeof loadAll === "function") await loadAll(true);
    const performance = await pageApi("/api/sim/performance");
    renderPerformance(performance);
  } catch (error) {
    pageToast(error.message);
  }
});

document.addEventListener("marketsim:login", () => {
  loadFundHome();
});

document.addEventListener("marketsim:logout", () => {
  document.querySelector("#bottomNav")?.classList.add("hidden");
});

let advisorChartPages = null;

function renderAdvisorCurve(rows) {
  const el = document.querySelector("#advisorCurve");
  if (!el || !window.echarts) return;
  const dataRows = rows || [];
  if (!dataRows.length) {
    el.innerHTML = `<div class="muted" style="padding:16px;">暂无收益曲线，先执行一次系统模拟操作。</div>`;
    return;
  }
  if (!advisorChartPages) {
    advisorChartPages = echarts.init(el);
    window.addEventListener("resize", () => advisorChartPages?.resize());
  }
  advisorChartPages.setOption(
    {
      animation: false,
      title: { text: "系统模拟收益曲线", left: 14, top: 12, textStyle: { fontSize: 14, fontWeight: 700 } },
      tooltip: { trigger: "axis" },
      legend: { top: 12, right: 12, data: ["总资产", "收益率"] },
      grid: { left: 52, right: 54, top: 54, bottom: 36 },
      xAxis: { type: "category", data: dataRows.map((item) => String(item.time || "").slice(5, 16)) },
      yAxis: [
        { type: "value", scale: true, name: "资产" },
        { type: "value", scale: true, name: "%", splitLine: { show: false } },
      ],
      series: [
        {
          name: "总资产",
          type: "line",
          smooth: true,
          data: dataRows.map((item) => Number(item.total_asset || 0)),
          lineStyle: { color: "#2563eb", width: 2.4 },
          areaStyle: { color: "rgba(37,99,235,.10)" },
        },
        {
          name: "收益率",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          data: dataRows.map((item) => Number(item.profit_rate || 0)),
          lineStyle: { color: "#dc2626", width: 2 },
        },
      ],
    },
    true
  );
  setTimeout(() => advisorChartPages?.resize(), 40);
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
          ? flows.slice(0, 8).map((item) => `<p><b>${escapeHtml(item.name)}</b> · 热度 ${escapeHtml(item.heat || "--")} · 涨跌 ${pct(item.change_percent)} · ${escapeHtml(item.hint || "")}</p>`).join("")
          : "<p>暂无行业资金流数据</p>"
      }
    </article>
    <article class="news-card">
      <h3>行业动态</h3>
      ${
        dynamics.length
          ? dynamics.slice(0, 6).map((item) => `<p><b>${escapeHtml(item.direction || "观察")}</b> · ${escapeHtml(item.title || "")}</p>`).join("")
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

  const positions = data.positions || [];
  document.querySelector("#advisorPositions").innerHTML = positions.length
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

  const trades = data.trades || [];
  document.querySelector("#advisorTrades").innerHTML = trades.length
    ? trades
        .map(
          (item) => `
            <article class="news-card">
              <h3>${escapeHtml(item.side === "buy" ? "系统模拟买入" : "系统模拟减仓")} · ${escapeHtml(item.name)}</h3>
              <p>${escapeHtml(item.symbol)} · 金额 ${money(item.amount)} · 净值 ${numberText(item.price, 4)} · ${String(item.created_at || "").replace("T", " ").slice(0, 19)}</p>
              <p>${escapeHtml(item.reason)}</p>
              ${(item.evidence || []).length ? `<div class="evidence-list"><b>依据</b>${item.evidence.slice(0, 5).map((ev) => `<span>${escapeHtml(ev)}</span>`).join("")}</div>` : ""}
            </article>
          `
        )
        .join("")
    : `<article class="news-card"><p>暂无系统操作记录。</p></article>`;
}

async function loadAdvisorSim() {
  try {
    const data = await pageApi("/api/advisor-sim");
    renderAdvisorSim(data);
  } catch (error) {
    pageToast(error.message);
  }
}

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
      return `
        <article class="news-card">
          <h3>${escapeHtml(log.run_date)} 模拟操作记录</h3>
          <p>${escapeHtml(log.summary)}</p>
          <p class="muted">已保存到本地</p>
          <div class="daily-decision-list">
            ${decisions
              .slice(0, 12)
              .map(
                (item) => `
                  <div>
                    <b>${escapeHtml(item.name)} ${escapeHtml(item.symbol)}</b>
                    <span>${escapeHtml(item.action)} · 买 ${numberText(item.buy_index, 1)} / 持 ${numberText(item.hold_index, 1)} / 卖 ${numberText(item.sell_index, 1)}</span>
                    <p>${escapeHtml(item.reason || "")}</p>
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
    document.querySelector("#dailyOpsHint").textContent = settings.enabled ? `已开启，每天 ${settings.run_time || "02:55"} 执行` : "未开启自动执行";
    renderDailyOpsLogs(logs.logs || []);
  } catch (error) {
    pageToast(error.message);
  }
}

document.addEventListener("click", async (event) => {
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
  loadDailyOps();
  loadAdvisorSim();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js").catch(() => {});
}


// UTF-8 mobile fund/news UI overrides.  These functions intentionally keep the
// same names as the early prototype so existing listeners use the improved UI.
function adviceBars(advice) {
  if (!advice) return "";
  const bar = (label, value, className) => `
    <div class="advice-row">
      <span>${label}</span>
      <div class="advice-track"><i class="${className}" style="width:${Math.max(0, Math.min(100, Number(value || 0)))}%"></i></div>
      <b>${numberText(value, 1)}</b>
    </div>`;
  return `
    <div class="advice-box">
      ${bar("买入指数", advice.buy_index, "buy")}
      ${bar("持有指数", advice.hold_index, "hold")}
      ${bar("卖出指数", advice.sell_index, "sell")}
      <p><b>当前建议：</b>${escapeHtml(advice.action || "观察")}</p>
      <p>${escapeHtml(advice.plain_explanation || "")}</p>
      ${(advice.reasons || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}
    </div>
  `;
}

function renderFundResults(funds) {
  const box = document.querySelector("#fundResults");
  if (!funds.length) {
    box.innerHTML = `<div class="fund-card"><p>暂无数据，换个代码或名称试试。</p></div>`;
    return;
  }
  box.innerHTML = funds
    .map(
      (fund) => `
        <article class="fund-card">
          <h3>${escapeHtml(fund.name)}</h3>
          <p>${escapeHtml(fund.symbol)} · ${escapeHtml(fund.fund_type || "公募基金")}</p>
          ${cardTags([`净值 ${numberText(fund.latest_nav, 4)}`, `日涨跌 ${pct(fund.daily_change)}`, fund.risk_level])}
          <p>来源：${escapeHtml(fund.data_source || "公开数据")}</p>
          <div class="actions">
            <button class="secondary-btn" data-fund-detail="${escapeHtml(fund.symbol)}">详情评分</button>
            <button class="secondary-btn" data-fund-watch="${escapeHtml(fund.symbol)}" data-name="${escapeHtml(fund.name)}">加自选</button>
            <button class="primary-btn" data-fund-buy="${escapeHtml(fund.symbol)}" data-name="${escapeHtml(fund.name)}" data-nav="${fund.latest_nav || 1}">模拟买入</button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderFundDetail(payload) {
  const fund = payload.detail.fund;
  const score = payload.score;
  const advice = payload.advice;
  const errors = payload.detail.errors || [];
  const box = document.querySelector("#fundDetailBody");
  box.innerHTML = `
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

function renderRecommendations(data) {
  const buckets = data.recommendations || {};
  const names = {
    today: "今日推荐基金",
    week: "本周潜力基金",
    undervalued: "低估值关注基金",
    growth: "高成长关注基金",
    stable: "稳健型基金",
    aggressive: "激进型基金",
    beginner: "适合新手的基金",
    avoid_chasing: "不建议追高的基金",
  };
  document.querySelector("#recommendationBody").innerHTML = Object.entries(names)
    .map(([key, title]) => {
      const rows = buckets[key] || [];
      return `
        <article class="score-card">
          <h3>${title}</h3>
          ${
            rows.length
              ? rows
                  .map(
                    (item) => `
                    <div class="fund-card">
                      <h3>${escapeHtml(item.name)} <span class="tag score-pill">${item.score} 分</span></h3>
                      <p>${escapeHtml(item.symbol)} · ${escapeHtml(item.grade)} · ${escapeHtml(item.action)}</p>
                      ${adviceBars(item)}
                      <p>${escapeHtml(item.reason)}</p>
                      <p>风险：${escapeHtml(item.risk)}</p>
                    </div>
                  `
                  )
                  .join("")
              : `<p>暂无数据</p>`
          }
        </article>
      `;
    })
    .join("");
}

function renderNews(list, selector) {
  const box = document.querySelector(selector);
  if (!list.length) {
    box.innerHTML = `<article class="news-card"><p>暂无数据，点“刷新资讯”再试一次。</p></article>`;
    return;
  }
  box.innerHTML = list
    .map((item) => {
      const news = item.news || item;
      const fundLine = item.fund ? `<p><b>关联基金：</b>${escapeHtml(item.fund.name)} · ${escapeHtml(item.effect)}</p>` : "";
      const reason = item.reason ? `<p><b>关联原因：</b>${escapeHtml(item.reason)}</p>` : "";
      const url = news.original_url ? `<a class="text-link" href="${escapeHtml(news.original_url)}" target="_blank" rel="noreferrer">查看原文</a>` : "";
      return `
        <article class="news-card">
          <h3>${escapeHtml(news.title)}</h3>
          <p>${escapeHtml(news.source)} · ${escapeHtml(news.published_at)} · 影响程度：${escapeHtml(news.impact_level)}</p>
          ${cardTags([news.impact_direction, `利好 ${news.positive_types}`, `利空 ${news.negative_types}`])}
          <p><b>原文摘要：</b>${escapeHtml(news.summary || news.original_text || "")}</p>
          <p><b>通俗解读：</b>${escapeHtml(news.plain_explanation)}</p>
          <p><b>操作参考：</b>${escapeHtml(news.operation_reference)}</p>
          ${fundLine}${reason}
          ${item.nav_impact ? `<p><b>可能影响：</b>${escapeHtml(item.nav_impact)}</p>` : ""}
          ${item.decision_hint ? `<p><b>决策提示：</b>${escapeHtml(item.decision_hint)}</p>` : ""}
          ${url}
        </article>
      `;
    })
    .join("");
}

function renderMyAdvice(list) {
  const target = document.querySelector("#myFundAdviceList");
  if (!target) return;
  if (!list.length) {
    target.innerHTML = `<article class="news-card"><p>还没有自选或持仓基金。先搜索基金并加入自选，系统会给出对应指数。</p></article>`;
    return;
  }
  target.innerHTML = list
    .map(
      (item) => `
        <article class="fund-card">
          <h3>${escapeHtml(item.fund.name)} <span class="tag">${escapeHtml(item.advice.action)}</span></h3>
          <p>${escapeHtml(item.fund.symbol)} · ${escapeHtml(item.advice.grade)} · 综合 ${numberText(item.advice.score, 1)} 分</p>
          ${adviceBars(item.advice)}
        </article>
      `
    )
    .join("");
}

async function loadFundHome(refresh = false) {
  try {
    const suffix = refresh ? "?refresh=true" : "";
    const [recommendations, news, myNews, performance] = await Promise.all([
      pageApi("/api/funds/recommendations"),
      pageApi(`/api/news/market${refresh ? "?refresh=true&limit=50" : "?limit=50"}`),
      pageApi("/api/news/my-funds"),
      pageApi("/api/sim/performance"),
    ]);
    renderRecommendations(recommendations);
    renderNews(news.news || [], "#newsList");
    renderNews(myNews.matched || [], "#myNewsList");
    renderMyAdvice(myNews.advice || []);
    renderPerformance(performance);
    document.querySelector("#newsHint").textContent = `共 ${news.count || (news.news || []).length} 条，更新于 ${news.updated_at || "--"}`;
    document.querySelector("#recommendationHint").textContent = `更新于 ${recommendations.updated_at || "--"}`;
  } catch (error) {
    pageToast(error.message);
  }
}

function ensureFundTools() {
  const newsTitle = document.querySelector("#marketNews .section-title");
  const myTitle = document.querySelector("#myFundNews .section-title");
  const searchTitle = document.querySelector("#fundSearch .section-title");
  if (searchTitle && !document.querySelector("#refreshFundSearchBtn")) {
    searchTitle.insertAdjacentHTML("beforeend", `<button id="refreshFundSearchBtn" class="secondary-btn" type="button">刷新基金</button>`);
  }
  if (newsTitle && !document.querySelector("#refreshNewsBtn")) {
    newsTitle.insertAdjacentHTML("beforeend", `<button id="refreshNewsBtn" class="secondary-btn" type="button">刷新资讯</button>`);
  }
  if (myTitle && !document.querySelector("#myFundAdviceList")) {
    myTitle.insertAdjacentHTML("afterend", `<div id="myFundAdviceList" class="fund-grid"></div>`);
  }
}

ensureFundTools();

document.addEventListener("click", async (event) => {
  if (event.target.closest("#refreshNewsBtn")) {
    pageToast("正在刷新资讯...");
    await loadFundHome(true);
  }
  if (event.target.closest("#refreshFundSearchBtn")) {
    const keyword = document.querySelector("#fundKeyword")?.value.trim() || "";
    const data = await pageApi(`/api/funds/search?q=${encodeURIComponent(keyword)}&refresh=true`);
    renderFundResults(data.funds || []);
    document.querySelector("#fundSearchHint").textContent = data.errors?.length ? "部分数据源异常，已显示可用数据" : `更新于 ${data.updated_at}`;
  }
});
