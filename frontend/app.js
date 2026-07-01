const API_BASE = location.protocol.startsWith("http") ? location.origin : "http://127.0.0.1:8000";

const state = {
  quotes: [],
  positions: [],
  chart: null,
  toastTimer: null,
};

const els = {
  apiStatus: document.querySelector("#apiStatus"),
  refreshBtn: document.querySelector("#refreshBtn"),
  totalAsset: document.querySelector("#totalAsset"),
  cash: document.querySelector("#cash"),
  holdingValue: document.querySelector("#holdingValue"),
  totalProfit: document.querySelector("#totalProfit"),
  totalProfitRate: document.querySelector("#totalProfitRate"),
  indicesBody: document.querySelector("#indicesBody"),
  indexHint: document.querySelector("#indexHint"),
  watchForm: document.querySelector("#watchForm"),
  watchlistBody: document.querySelector("#watchlistBody"),
  positionsBody: document.querySelector("#positionsBody"),
  tradesBody: document.querySelector("#tradesBody"),
  toast: document.querySelector("#toast"),
  tradeModal: document.querySelector("#tradeModal"),
  closeModalBtn: document.querySelector("#closeModalBtn"),
  tradeForm: document.querySelector("#tradeForm"),
  tradeTitle: document.querySelector("#tradeTitle"),
  tradeSide: document.querySelector("#tradeSide"),
  tradeSymbol: document.querySelector("#tradeSymbol"),
  tradeName: document.querySelector("#tradeName"),
  tradeNameLabel: document.querySelector("#tradeNameLabel"),
  tradeType: document.querySelector("#tradeType"),
  tradePrice: document.querySelector("#tradePrice"),
  tradeQuantity: document.querySelector("#tradeQuantity"),
  tradeFee: document.querySelector("#tradeFee"),
  submitTradeBtn: document.querySelector("#submitTradeBtn"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `¥${Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function numberText(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: digits });
}

function pct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `${Number(value).toFixed(2)}%`;
}

function tone(value) {
  const num = Number(value);
  if (Number.isNaN(num) || num === 0) return "";
  return num > 0 ? "up" : "down";
}

function typeName(type) {
  return { stock: "股票", etf: "ETF", fund: "场外基金", index: "指数" }[type] || type;
}

function sideName(side) {
  return side === "buy" ? "买入" : "卖出";
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function setStatus(text, className = "") {
  els.apiStatus.textContent = text;
  els.apiStatus.className = `status-dot ${className}`.trim();
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const result = await response.json().catch(() => null);
  if (!response.ok || !result?.success) {
    throw new Error(result?.message || `请求失败：${response.status}`);
  }
  return result.data;
}

function renderAccount(data) {
  els.totalAsset.textContent = money(data.total_asset);
  els.cash.textContent = money(data.cash);
  els.holdingValue.textContent = money(data.holding_market_value);
  els.totalProfit.textContent = money(data.total_profit);
  els.totalProfit.className = tone(data.total_profit);
  els.totalProfitRate.textContent = pct(data.total_profit_rate);
  els.totalProfitRate.className = tone(data.total_profit_rate);
}

function renderIndices(data) {
  const rows = data.indices || [];
  els.indexHint.textContent = data.errors?.length ? `部分失败 ${data.errors.length} 项` : "";
  els.indicesBody.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.symbol)}</td>
          <td>${numberText(item.price, 3)}</td>
          <td class="${tone(item.change_percent)}">${pct(item.change_percent)}</td>
          <td class="${item.error ? "warn" : "muted"}">${escapeHtml(item.error || item.update_time || "--")}</td>
        </tr>
      `
    )
    .join("");
}

function renderWatchlist(items) {
  state.quotes = items;
  if (!items.length) {
    els.watchlistBody.innerHTML = `<tr><td colspan="7" class="muted">暂无自选标的</td></tr>`;
    return;
  }

  els.watchlistBody.innerHTML = items
    .map((item) => {
      const quote = item.data || {};
      const disabled = item.success ? "" : "disabled";
      const err = item.success ? "" : `<div class="warn">${escapeHtml(item.error)}</div>`;
      return `
        <tr>
          <td>${escapeHtml(quote.symbol)}</td>
          <td>${escapeHtml(quote.name)}${err}</td>
          <td>${typeName(quote.asset_type)}</td>
          <td>${numberText(quote.price, 4)}</td>
          <td class="${tone(quote.change_percent)}">${pct(quote.change_percent)}</td>
          <td class="muted">${escapeHtml(quote.update_time || "--")}</td>
          <td>
            <div class="actions">
              <button class="secondary-btn" ${disabled} data-action="buy-watch" data-id="${quote.watchlist_id}">买入</button>
              <button class="secondary-btn" ${disabled} data-action="sell-watch" data-id="${quote.watchlist_id}">卖出</button>
              <button class="danger-btn" data-action="delete-watch" data-id="${quote.watchlist_id}">删除</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderPositions(items) {
  state.positions = items;
  if (!items.length) {
    els.positionsBody.innerHTML = `<tr><td colspan="10" class="muted">暂无持仓</td></tr>`;
    renderChart([]);
    return;
  }

  els.positionsBody.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.symbol)}</td>
          <td>${escapeHtml(item.name)}</td>
          <td>${typeName(item.asset_type)}</td>
          <td>${numberText(item.quantity, 4)}</td>
          <td>${numberText(item.avg_cost, 4)}</td>
          <td>${numberText(item.current_price, 4)}</td>
          <td>${money(item.market_value)}</td>
          <td class="${tone(item.profit)}">${money(item.profit)}</td>
          <td class="${tone(item.profit_rate)}">${pct(item.profit_rate)}</td>
          <td>
            <div class="actions">
              <button class="secondary-btn" data-action="buy-position" data-id="${item.id}">买入</button>
              <button class="secondary-btn" data-action="sell-position" data-id="${item.id}">卖出</button>
            </div>
          </td>
        </tr>
      `
    )
    .join("");
  renderChart(items);
}

function renderTrades(items) {
  if (!items.length) {
    els.tradesBody.innerHTML = `<tr><td colspan="10" class="muted">暂无交易记录</td></tr>`;
    return;
  }
  els.tradesBody.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td class="muted">${escapeHtml(String(item.created_at).replace("T", " ").slice(0, 19))}</td>
          <td class="${item.side === "buy" ? "up" : "down"}">${sideName(item.side)}</td>
          <td>${escapeHtml(item.symbol)}</td>
          <td>${escapeHtml(item.name)}</td>
          <td>${typeName(item.asset_type)}</td>
          <td>${numberText(item.price, 4)}</td>
          <td>${numberText(item.quantity, 4)}</td>
          <td>${money(item.amount)}</td>
          <td>${money(item.fee)}</td>
          <td class="${tone(item.profit)}">${money(item.profit)}</td>
        </tr>
      `
    )
    .join("");
}

function renderChart(positions) {
  const chartEl = document.querySelector("#allocationChart");
  if (!window.echarts) {
    chartEl.innerHTML = `<div class="muted" style="padding:16px;">ECharts 未加载</div>`;
    return;
  }
  if (!state.chart) {
    state.chart = echarts.init(chartEl);
    window.addEventListener("resize", () => state.chart?.resize());
  }
  const data = positions.map((item) => ({ name: `${item.name} ${item.symbol}`, value: item.market_value }));
  state.chart.setOption({
    title: { text: "持仓分布", left: 14, top: 12, textStyle: { fontSize: 14, fontWeight: 600 } },
    tooltip: { trigger: "item", formatter: "{b}<br/>{c} ({d}%)" },
    legend: { bottom: 8, type: "scroll" },
    series: [
      {
        type: "pie",
        radius: ["42%", "66%"],
        center: ["50%", "47%"],
        data,
        label: { formatter: "{b}" },
      },
    ],
  });
}

async function loadAll(showSuccess = false) {
  try {
    setStatus("连接中");
    const [account, quotes, positions, trades, indices] = await Promise.all([
      api("/api/account"),
      api("/api/quotes"),
      api("/api/positions"),
      api("/api/trades"),
      api("/api/market/indices"),
    ]);
    renderAccount(account);
    renderWatchlist(quotes);
    renderPositions(positions);
    renderTrades(trades);
    renderIndices(indices);
    setStatus("已连接", "ok");
    if (showSuccess) showToast("刷新完成");
  } catch (error) {
    setStatus("连接失败", "error");
    showToast(error.message);
  }
}

async function refreshMarket() {
  try {
    els.refreshBtn.disabled = true;
    await api("/api/refresh", { method: "POST" });
    await loadAll(true);
  } catch (error) {
    showToast(error.message);
    await loadAll(false);
  } finally {
    els.refreshBtn.disabled = false;
  }
}

function openTradeModal(side, source) {
  els.tradeSide.value = side;
  els.tradeTitle.textContent = side === "buy" ? "模拟买入" : "模拟卖出";
  els.submitTradeBtn.textContent = side === "buy" ? "确认买入" : "确认卖出";
  els.tradeSymbol.value = source.symbol || "";
  els.tradeName.value = source.name || "";
  els.tradeType.value = source.asset_type || "stock";
  els.tradePrice.value = source.price || source.current_price || "";
  els.tradeQuantity.value = "";
  els.tradeFee.value = 0;
  els.tradeNameLabel.style.display = side === "sell" ? "none" : "grid";
  els.tradeName.required = side === "buy";
  els.tradeModal.classList.add("show");
  els.tradeModal.setAttribute("aria-hidden", "false");
  setTimeout(() => els.tradeQuantity.focus(), 30);
}

function closeTradeModal() {
  els.tradeModal.classList.remove("show");
  els.tradeModal.setAttribute("aria-hidden", "true");
}

function findQuoteByWatchId(id) {
  const item = state.quotes.find((row) => Number(row.data?.watchlist_id) === Number(id));
  return item?.data;
}

function findPositionById(id) {
  return state.positions.find((row) => Number(row.id) === Number(id));
}

async function deleteWatch(id) {
  if (!confirm("确认删除这个自选标的吗？")) return;
  try {
    await api(`/api/watchlist/${id}`, { method: "DELETE" });
    showToast("删除成功");
    await loadAll();
  } catch (error) {
    showToast(error.message);
  }
}

els.watchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.watchForm);
  const payload = Object.fromEntries(form.entries());
  try {
    await api("/api/watchlist", { method: "POST", body: JSON.stringify(payload) });
    els.watchForm.reset();
    showToast("添加成功");
    await loadAll();
  } catch (error) {
    showToast(error.message);
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const id = button.dataset.id;
  if (action === "delete-watch") {
    deleteWatch(id);
    return;
  }
  if (action === "buy-watch" || action === "sell-watch") {
    const quote = findQuoteByWatchId(id);
    if (quote) openTradeModal(action === "buy-watch" ? "buy" : "sell", quote);
  }
  if (action === "buy-position" || action === "sell-position") {
    const position = findPositionById(id);
    if (position) openTradeModal(action === "buy-position" ? "buy" : "sell", position);
  }
});

els.tradeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const side = els.tradeSide.value;
  const payload = {
    symbol: els.tradeSymbol.value.trim(),
    asset_type: els.tradeType.value,
    price: Number(els.tradePrice.value),
    quantity: Number(els.tradeQuantity.value),
    fee: Number(els.tradeFee.value || 0),
  };
  if (side === "buy") {
    payload.name = els.tradeName.value.trim();
  }
  try {
    await api(`/api/trade/${side}`, { method: "POST", body: JSON.stringify(payload) });
    closeTradeModal();
    showToast(side === "buy" ? "买入成功" : "卖出成功");
    await loadAll();
  } catch (error) {
    showToast(error.message);
  }
});

els.refreshBtn.addEventListener("click", refreshMarket);
els.closeModalBtn.addEventListener("click", closeTradeModal);
els.tradeModal.addEventListener("click", (event) => {
  if (event.target === els.tradeModal) closeTradeModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeTradeModal();
});

loadAll();
setInterval(loadAll, 30000);

