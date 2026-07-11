(() => {
  const PANEL_ID = "aiBacktest";
  let aiBacktestChart = null;

  function safeNumber(value, fallback = 0) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
  }

  function dateValue(value) {
    const text = String(value || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return null;
    const time = new Date(`${text}T00:00:00`).getTime();
    return Number.isFinite(time) ? time : null;
  }

  function normalizeHistory(history, startDate, endDate) {
    const start = dateValue(startDate);
    const end = dateValue(endDate);
    return (history || [])
      .map((item) => {
        const date = String(item.date || item.trade_date || item.nav_date || "").slice(0, 10);
        const nav = safeNumber(item.nav ?? item.unit_nav ?? item.close, NaN);
        const time = dateValue(date);
        if (!time || !Number.isFinite(nav) || nav <= 0) return null;
        if (start && time < start) return null;
        if (end && time > end) return null;
        return {
          date,
          nav,
          change_percent: safeNumber(item.change_percent ?? item.daily_return, 0),
        };
      })
      .filter(Boolean)
      .sort((a, b) => dateValue(a.date) - dateValue(b.date));
  }

  function avg(values) {
    if (!values.length) return 0;
    return values.reduce((sum, value) => sum + Number(value || 0), 0) / values.length;
  }

  function pctChange(current, previous) {
    if (!previous) return 0;
    return (current - previous) / previous;
  }

  function maxBuyAmountByPosition(cash, units, nav, maxPositionRatio, buyFeeRate) {
    const totalValue = cash + units * nav;
    const currentMarketValue = units * nav;
    const remainingTargetValue = maxPositionRatio * totalValue - currentMarketValue;
    const denominator = 1 - buyFeeRate * (1 - maxPositionRatio);
    if (remainingTargetValue <= 0 || denominator <= 0) return 0;
    return Math.max(0, remainingTargetValue / denominator);
  }

  function sellUnitsToPositionCap(cash, units, nav, maxPositionRatio, sellFeeRate) {
    const marketValue = units * nav;
    const totalValue = cash + marketValue;
    const excessValue = marketValue - maxPositionRatio * totalValue;
    const denominator = nav * (1 - maxPositionRatio * sellFeeRate);
    if (excessValue <= 0 || denominator <= 0) return 0;
    return Math.min(units, Math.max(0, excessValue / denominator));
  }

  function signalFor(history, shortWindow = 20, longWindow = 60, stopLossDrawdown = -0.08) {
    if (history.length < longWindow + 1) {
      return { action: "hold", confidence: 30, reasoning: "净值历史不足，暂时观望" };
    }
    const navs = history.map((item) => item.nav);
    const latestNav = navs[navs.length - 1];
    const shortMa = avg(navs.slice(-shortWindow));
    const longMa = avg(navs.slice(-longWindow));
    const previousShortMa = avg(navs.slice(-shortWindow - 1, -1));
    const previousLongMa = avg(navs.slice(-longWindow - 1, -1));
    const recentHigh = Math.max(...navs.slice(-longWindow));
    const drawdown = pctChange(latestNav, recentHigh);
    const oneMonthReturn = pctChange(latestNav, navs[navs.length - shortWindow]);
    const crossedUp = previousShortMa <= previousLongMa && shortMa > longMa;
    const crossedDown = previousShortMa >= previousLongMa && shortMa < longMa;

    if (drawdown <= stopLossDrawdown) {
      return { action: "sell", confidence: 85, reasoning: `近${longWindow}日回撤${(drawdown * 100).toFixed(2)}%，触发风控` };
    }
    if (crossedUp && oneMonthReturn > 0) {
      return { action: "buy", confidence: 75, reasoning: `${shortWindow}日均线上穿${longWindow}日均线，动量转强` };
    }
    if (crossedDown) {
      return { action: "sell", confidence: 70, reasoning: `${shortWindow}日均线下穿${longWindow}日均线，趋势转弱` };
    }
    if (shortMa > longMa && oneMonthReturn > 0.03) {
      return { action: "buy", confidence: 65, reasoning: `短期均线在长期均线上方，近${shortWindow}日收益${(oneMonthReturn * 100).toFixed(2)}%` };
    }
    return { action: "hold", confidence: 55, reasoning: "趋势信号不明确，维持观望" };
  }

  function runClientBacktest(history, params, fund) {
    if (history.length < 80) {
      throw new Error("有效历史净值不足，至少建议 80 个交易日以上；请换一只基金或稍后刷新数据源。 ");
    }

    let cash = safeNumber(params.initial_cash, 100000);
    let units = 0;
    let lastBuyIndex = null;
    const trades = [];
    const equityCurve = [];
    const totalValues = [];

    const tradeAmount = safeNumber(params.trade_amount, 10000);
    const maxPositionRatio = Math.max(0.05, Math.min(1, safeNumber(params.max_position_ratio, 0.8)));
    const buyFeeRate = Math.max(0, safeNumber(params.buy_fee_rate, 0.001));
    const sellFeeRate = Math.max(0, safeNumber(params.sell_fee_rate, 0.005));

    history.forEach((point, index) => {
      let signal = signalFor(history.slice(0, index + 1));
      const nav = point.nav;

      const rebalanceUnits = sellUnitsToPositionCap(
        cash,
        units,
        nav,
        maxPositionRatio,
        sellFeeRate
      );
      if (rebalanceUnits > 1e-12) {
        const grossAmount = rebalanceUnits * nav;
        const fee = grossAmount * sellFeeRate;
        const netAmount = grossAmount - fee;
        cash += netAmount;
        units -= rebalanceUnits;
        if (units <= 1e-12) {
          units = 0;
          lastBuyIndex = null;
        }
        signal = {
          action: "sell",
          confidence: 90,
          reasoning: "净值上涨使仓位超过上限，自动减持超额份额",
        };
        trades.push({
          trade_date: point.date,
          fund_code: params.fund_code,
          action: "sell",
          nav,
          amount: netAmount,
          units: rebalanceUnits,
          fee,
          cash_after: cash,
          units_after: units,
          reasoning: signal.reasoning,
        });
      } else if (signal.action === "buy") {
        const total = cash + units * nav;
        const positionRatio = total > 0 ? (units * nav) / total : 0;
        if (positionRatio >= maxPositionRatio) {
          signal = { action: "hold", confidence: 80, reasoning: "已达到最大仓位限制，暂停买入" };
        } else if (cash <= 0) {
          signal = { action: "hold", confidence: 80, reasoning: "现金不足，无法买入" };
        } else {
          const positionLimitAmount = maxBuyAmountByPosition(
            cash,
            units,
            nav,
            maxPositionRatio,
            buyFeeRate
          );
          const amount = Math.min(tradeAmount, cash, positionLimitAmount);
          const fee = amount * buyFeeRate;
          const netAmount = Math.max(0, amount - fee);
          const boughtUnits = netAmount / nav;
          if (boughtUnits > 0) {
            cash -= amount;
            units += boughtUnits;
            lastBuyIndex = index;
            trades.push({
              trade_date: point.date,
              fund_code: params.fund_code,
              action: "buy",
              nav,
              amount,
              units: boughtUnits,
              fee,
              cash_after: cash,
              units_after: units,
              reasoning: signal.reasoning,
            });
          }
        }
      } else if (signal.action === "sell") {
        if (units <= 0) {
          signal = { action: "hold", confidence: 80, reasoning: "当前无持仓，无法卖出" };
        } else if (lastBuyIndex !== null && index - lastBuyIndex < safeNumber(params.min_hold_days, 0)) {
          signal = { action: "hold", confidence: 80, reasoning: "持有时间不足，暂不卖出" };
        } else {
          const sellUnits = units;
          const grossAmount = sellUnits * nav;
          const fee = grossAmount * sellFeeRate;
          const netAmount = Math.max(0, grossAmount - fee);
          cash += netAmount;
          units = 0;
          trades.push({
            trade_date: point.date,
            fund_code: params.fund_code,
            action: "sell",
            nav,
            amount: netAmount,
            units: sellUnits,
            fee,
            cash_after: cash,
            units_after: units,
            reasoning: signal.reasoning,
          });
        }
      }

      const marketValue = units * nav;
      const totalValue = cash + marketValue;
      totalValues.push(totalValue);
      const peak = Math.max(...totalValues);
      const drawdownPct = peak > 0 ? ((totalValue - peak) / peak) * 100 : 0;
      equityCurve.push({
        trade_date: point.date,
        nav,
        cash,
        units,
        market_value: marketValue,
        total_value: totalValue,
        drawdown_pct: drawdownPct,
        signal: signal.action,
        reasoning: signal.reasoning,
      });
    });

    const finalValue = equityCurve[equityCurve.length - 1].total_value;
    const maxDrawdownPct = Math.min(...equityCurve.map((item) => item.drawdown_pct));
    return {
      fund_code: params.fund_code,
      fund,
      summary: {
        initial_cash: safeNumber(params.initial_cash, 100000),
        final_value: finalValue,
        total_return_pct: (finalValue / safeNumber(params.initial_cash, 100000) - 1) * 100,
        max_drawdown_pct: maxDrawdownPct,
      },
      trades,
      equity_curve: equityCurve,
      params,
      disclaimer: "仅供学习和模拟研究，不构成投资建议；系统不会连接券商或执行真实交易。",
      client_side: true,
    };
  }

  function actionText(action) {
    return { buy: "买入", sell: "卖出", hold: "持有" }[action] || action || "--";
  }

  function renderBacktestChart(result) {
    const el = document.querySelector("#aiBacktestChart");
    if (!el) return;
    const rows = result.equity_curve || [];
    if (!window.echarts) {
      el.innerHTML = `<div class="muted" style="padding:16px;">走势图组件未加载</div>`;
      return;
    }
    if (rows.length < 2) {
      el.innerHTML = `<div class="muted" style="padding:16px;">暂无足够回测数据</div>`;
      return;
    }
    if (!aiBacktestChart) {
      aiBacktestChart = echarts.init(el);
      window.addEventListener("resize", () => aiBacktestChart?.resize());
    }
    aiBacktestChart.setOption(
      {
        animation: false,
        title: { text: "AI 基金回测资产曲线", left: 12, top: 10, textStyle: { fontSize: 14, fontWeight: 700 } },
        tooltip: {
          trigger: "axis",
          formatter(params) {
            const asset = params.find((item) => item.seriesName === "总资产");
            const dd = params.find((item) => item.seriesName === "回撤");
            const nav = params.find((item) => item.seriesName === "单位净值");
            return `${params[0].axisValue}<br/>总资产：${money(asset?.value)}<br/>单位净值：${numberText(nav?.value, 4)}<br/>回撤：${pct(dd?.value)}`;
          },
        },
        legend: { top: 12, right: 12, data: ["总资产", "单位净值", "回撤"] },
        grid: { left: 54, right: 56, top: 56, bottom: 42 },
        xAxis: { type: "category", data: rows.map((item) => item.trade_date), boundaryGap: false },
        yAxis: [
          { type: "value", scale: true, name: "资产" },
          { type: "value", scale: true, name: "净值/%", splitLine: { show: false } },
        ],
        series: [
          {
            name: "总资产",
            type: "line",
            smooth: true,
            symbol: "none",
            data: rows.map((item) => Number(item.total_value || 0)),
            lineStyle: { color: "#2563eb", width: 2.4 },
            areaStyle: { color: "rgba(37,99,235,.10)" },
          },
          {
            name: "单位净值",
            type: "line",
            yAxisIndex: 1,
            smooth: true,
            symbol: "none",
            data: rows.map((item) => Number(item.nav || 0)),
            lineStyle: { color: "#7c3aed", width: 1.8 },
          },
          {
            name: "回撤",
            type: "line",
            yAxisIndex: 1,
            smooth: true,
            symbol: "none",
            data: rows.map((item) => Number(item.drawdown_pct || 0)),
            lineStyle: { color: "#16a34a", width: 1.8 },
          },
        ],
      },
      true
    );
    setTimeout(() => aiBacktestChart?.resize(), 40);
  }

  function renderAiBacktest(result) {
    const summary = result.summary || {};
    const fund = result.fund || {};
    const resultBox = document.querySelector("#aiBacktestResult");
    const tradeBox = document.querySelector("#aiBacktestTrades");
    const curveBox = document.querySelector("#aiBacktestCurveBody");
    const hint = document.querySelector("#aiBacktestHint");
    if (!resultBox || !tradeBox || !curveBox) return;

    const curve = result.equity_curve || [];
    const firstDate = curve[0]?.trade_date || "--";
    const lastDate = curve[curve.length - 1]?.trade_date || "--";
    const source = fund.data_source || (result.client_side ? "基金详情接口" : "公开基金数据");
    hint.textContent = `${fund.name || result.fund_code} · ${source} · ${curve.length} 条 · ${firstDate} 至 ${lastDate}`;
    resultBox.innerHTML = `
      <article class="metric-card"><span>最终资产</span><strong>${money(summary.final_value)}</strong></article>
      <article class="metric-card"><span>总收益率</span><strong class="${tone(summary.total_return_pct)}">${pct(summary.total_return_pct)}</strong></article>
      <article class="metric-card"><span>最大回撤</span><strong class="down">${pct(summary.max_drawdown_pct)}</strong></article>
      <article class="metric-card"><span>交易次数</span><strong>${(result.trades || []).length}</strong></article>
    `;

    renderBacktestChart(result);

    const trades = result.trades || [];
    tradeBox.innerHTML = trades.length
      ? trades
          .slice()
          .reverse()
          .slice(0, 30)
          .map(
            (item) => `
              <article class="news-card">
                <h3>${escapeHtml(item.trade_date)} · ${actionText(item.action)} · ${escapeHtml(result.fund_code)}</h3>
                <p>净值 ${numberText(item.nav, 4)} · 金额 ${money(item.amount)} · 份额 ${numberText(item.units, 4)} · 费用 ${money(item.fee)}</p>
                <p>${escapeHtml(item.reasoning || "")}</p>
              </article>
            `
          )
          .join("")
      : `<article class="news-card"><p>策略期间没有触发实际买卖，说明信号偏谨慎或数据周期较短。</p></article>`;

    const rows = (result.equity_curve || []).slice(-20).reverse();
    curveBox.innerHTML = rows
      .map(
        (item) => `
          <tr>
            <td>${escapeHtml(item.trade_date)}</td>
            <td>${numberText(item.nav, 4)}</td>
            <td>${money(item.total_value)}</td>
            <td>${money(item.cash)}</td>
            <td>${numberText(item.units, 4)}</td>
            <td class="${tone(item.drawdown_pct)}">${pct(item.drawdown_pct)}</td>
            <td>${actionText(item.signal)}</td>
            <td>${escapeHtml(item.reasoning || "")}</td>
          </tr>
        `
      )
      .join("");
  }

  async function fetchFundAndRunClient(params) {
    const query = params.refresh ? "?refresh=true" : "";
    const payload = await pageApi(`/api/funds/${encodeURIComponent(params.fund_code)}${query}`);
    const fund = payload?.detail?.fund || {};
    const history = normalizeHistory(fund.history || [], params.start_date, params.end_date);
    return runClientBacktest(history, params, {
      symbol: fund.symbol || params.fund_code,
      name: fund.name || `${params.fund_code} 基金`,
      fund_type: fund.fund_type || "公募基金",
      latest_nav: fund.latest_nav,
      daily_change: fund.daily_change,
      data_source: fund.data_source || "现有基金详情接口",
    });
  }

  async function runAiBacktest() {
    const form = document.querySelector("#aiBacktestForm");
    if (!form) return;
    const params = {
      fund_code: form.fund_code.value.replace(/\D/g, "").slice(0, 6),
      start_date: form.start_date.value || null,
      end_date: form.end_date.value || null,
      initial_cash: safeNumber(form.initial_cash.value, 100000),
      trade_amount: safeNumber(form.trade_amount.value, 10000),
      max_position_ratio: safeNumber(form.max_position_ratio.value, 80) / 100,
      buy_fee_rate: safeNumber(form.buy_fee_rate.value, 0.1) / 100,
      sell_fee_rate: safeNumber(form.sell_fee_rate.value, 0.5) / 100,
      refresh: form.refresh.checked,
    };
    if (!/^\d{6}$/.test(params.fund_code)) {
      pageToast("基金代码必须是 6 位数字");
      return;
    }

    const runBtn = document.querySelector("#runAiBacktestBtn");
    const errorBox = document.querySelector("#aiBacktestError");
    if (errorBox) {
      errorBox.textContent = "正在获取历史净值并执行回测……";
      errorBox.className = "ai-backtest-status loading";
    }
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.textContent = "回测中…";
    }
    try {
      pageToast("正在执行 AI 基金回测...");
      let result;
      try {
        result = await pageApi("/api/ai-backtest/run", {
          method: "POST",
          body: JSON.stringify(params),
        });
      } catch (backendError) {
        result = await fetchFundAndRunClient(params);
        result.fallback_notice = `后端回测接口暂未挂载，已使用前端同款规则完成回测：${backendError.message}`;
      }
      renderAiBacktest(result);
      if (errorBox) {
        const sourceErrors = (result.source_errors || []).map((item) =>
          typeof item === "string" ? item : item.message || item.error || JSON.stringify(item)
        );
        const sourceWarning = sourceErrors.length
          ? `部分数据源不可用：${sourceErrors.join("；")}`
          : "回测完成。历史回测不代表未来收益。";
        errorBox.textContent = sourceWarning;
        errorBox.className = `ai-backtest-status ${(result.source_errors || []).length ? "warning" : "success"}`;
      }
      if (result.fallback_notice) pageToast(result.fallback_notice);
      else pageToast("AI 基金回测完成");
    } catch (error) {
      if (errorBox) {
        errorBox.textContent = error.message || "当前基金历史净值暂时无法获取，请稍后重试或更换基金代码。";
        errorBox.className = "ai-backtest-status error";
      }
      pageToast(error.message);
    } finally {
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = "开始回测";
      }
    }
  }

  function installAiBacktestPanel() {
    const appView = document.querySelector("#appView");
    if (!appView) return;

    try {
      if (typeof PAGE_GROUPS !== "undefined") PAGE_GROUPS.aiBacktest = [PANEL_ID];
      if (typeof finalPageGroups !== "undefined") finalPageGroups.aiBacktest = [PANEL_ID];
    } catch (error) {
      console.warn("AI 回测页面组注册失败", error);
    }

    const nav = document.querySelector("#bottomNav");
    if (nav && !nav.querySelector('[data-page="aiBacktest"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.page = "aiBacktest";
      btn.textContent = "回测";
      nav.insertBefore(btn, nav.querySelector('[data-page="auto"]') || null);
    }

    if (!document.querySelector(`#${PANEL_ID}`)) {
      appView.insertAdjacentHTML(
        "beforeend",
        `
          <section id="${PANEL_ID}" class="panel page-hidden">
            <div class="section-title">
              <h2>AI 基金回测</h2>
              <span id="aiBacktestHint">20/60 日均线 + 回撤风控，仅供学习模拟</span>
            </div>
            <form id="aiBacktestForm" class="watch-form ai-backtest-form">
              <input name="fund_code" placeholder="基金代码，如 014855 / 000001" value="014855" required />
              <input name="start_date" type="date" title="开始日期，可选" />
              <input name="end_date" type="date" title="结束日期，可选" />
              <input name="initial_cash" type="number" min="1000" step="1000" value="100000" placeholder="初始资金" />
              <input name="trade_amount" type="number" min="100" step="100" value="10000" placeholder="单次金额" />
              <input name="max_position_ratio" type="number" min="5" max="100" step="5" value="80" placeholder="最大仓位%" />
              <input name="buy_fee_rate" type="number" min="0" step="0.01" value="0.10" placeholder="买入费率%" />
              <input name="sell_fee_rate" type="number" min="0" step="0.01" value="0.50" placeholder="卖出费率%" />
              <label class="inline-check"><input name="refresh" type="checkbox" /> 刷新数据</label>
              <button id="runAiBacktestBtn" class="primary-btn" type="submit">开始回测</button>
            </form>
            <div id="aiBacktestError" class="ai-backtest-status" role="status">填写 6 位基金代码后开始回测。</div>
            <p class="muted">当前不会修改你的模拟账户，也不会真实交易。策略先用规则跑通，后续可接 DeepSeek / Kimi / OpenAI Agent 做解释和复盘。</p>
            <div id="aiBacktestResult" class="metric-grid compact-metrics"></div>
            <div id="aiBacktestChart" class="chart"></div>
            <div id="aiBacktestTradesTitle" class="section-subtitle">回测交易记录</div>
            <div id="aiBacktestTrades" class="news-list"></div>
            <div id="aiBacktestCurveTitle" class="section-subtitle">最近 20 个交易日资产明细</div>
            <div class="table-wrap compact">
              <table>
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>净值</th>
                    <th>总资产</th>
                    <th>现金</th>
                    <th>份额</th>
                    <th>回撤</th>
                    <th>信号</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody id="aiBacktestCurveBody">
                  <tr><td colspan="8" class="muted">填写基金代码后点击“开始回测”。</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        `
      );
    }
  }

  document.addEventListener("submit", (event) => {
    if (event.target?.id === "aiBacktestForm") {
      event.preventDefault();
      runAiBacktest();
    }
  });

  document.addEventListener("click", (event) => {
    const pageBtn = event.target.closest('#bottomNav button[data-page="aiBacktest"]');
    if (pageBtn) {
      installAiBacktestPanel();
      setTimeout(() => aiBacktestChart?.resize(), 80);
    }
  });

  document.addEventListener("input", (event) => {
    if (event.target?.matches('#aiBacktestForm [name="fund_code"]')) {
      event.target.value = event.target.value.replace(/\D/g, "").slice(0, 6);
    }
  });

  document.addEventListener("marketsim:login", installAiBacktestPanel);
  installAiBacktestPanel();

  window.MarketSimAiBacktest = {
    runAiBacktest,
    runClientBacktest,
    normalizeHistory,
    maxBuyAmountByPosition,
    sellUnitsToPositionCap,
  };
})();
