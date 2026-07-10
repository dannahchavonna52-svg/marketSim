(() => {
  const params = new URLSearchParams(window.location.search);
  if (params.get("demo") !== "1") return;

  const demoFundCode = params.get("fund") || "014855";
  const shouldAutoRun = params.get("autorun") === "1";
  const focusMode = params.get("focus") === "1";
  let autoRunTriggered = false;

  document.body.classList.add("video-demo-mode");
  if (focusMode) document.body.classList.add("video-focus-mode");

  function installDemoBadge() {
    if (document.querySelector("#videoDemoBadge")) return;
    const badge = document.createElement("div");
    badge.id = "videoDemoBadge";
    badge.className = "video-demo-badge";
    badge.textContent = "演示模式 · 非投资建议";
    document.body.appendChild(badge);
  }

  function maskPrivateUi() {
    const userBadge = document.querySelector("#userBadge");
    if (userBadge) userBadge.textContent = "演示账号";

    const title = document.querySelector(".app-header h1");
    if (title) title.textContent = "AI 基金回测实验室";

    const subtitle = document.querySelector(".app-header p");
    if (subtitle) subtitle.textContent = "输入基金代码，查看历史策略回测、收益曲线和回撤风险。";
  }

  function installDemoHero() {
    const panel = document.querySelector("#aiBacktest");
    const form = document.querySelector("#aiBacktestForm");
    if (!panel || !form || document.querySelector("#videoDemoHero")) return;

    form.insertAdjacentHTML(
      "beforebegin",
      `
        <div id="videoDemoHero" class="video-demo-hero">
          <strong>用历史净值测试一套基金策略</strong>
          <p>系统会根据均线趋势、动量和回撤风控，生成模拟买入、卖出和持有记录。结果仅用于学习研究。</p>
          <div class="video-demo-tags">
            <span>历史净值</span>
            <span>策略回测</span>
            <span>仓位控制</span>
            <span>最大回撤</span>
          </div>
        </div>
      `
    );
  }

  function configureDemoForm() {
    const form = document.querySelector("#aiBacktestForm");
    if (!form) return false;

    if (form.elements.fund_code) form.elements.fund_code.value = demoFundCode;
    if (form.elements.initial_cash) form.elements.initial_cash.value = "100000";
    if (form.elements.trade_amount) form.elements.trade_amount.value = "10000";
    if (form.elements.max_position_ratio) form.elements.max_position_ratio.value = "80";
    if (form.elements.buy_fee_rate) form.elements.buy_fee_rate.value = "0.10";
    if (form.elements.sell_fee_rate) form.elements.sell_fee_rate.value = "0.50";
    return true;
  }

  function activateDemoPage() {
    installDemoBadge();
    maskPrivateUi();
    installDemoHero();
    const formReady = configureDemoForm();

    if (typeof window.showPage === "function") {
      window.showPage("aiBacktest");
    } else if (typeof showPage === "function") {
      showPage("aiBacktest");
    }

    if (shouldAutoRun && formReady && !autoRunTriggered) {
      const appView = document.querySelector("#appView");
      if (appView && !appView.classList.contains("hidden")) {
        autoRunTriggered = true;
        setTimeout(() => {
          document.querySelector("#aiBacktestForm")?.requestSubmit();
        }, 350);
      }
    }
  }

  document.addEventListener("marketsim:login", () => {
    setTimeout(activateDemoPage, 120);
  });

  const observer = new MutationObserver(() => {
    if (document.querySelector("#aiBacktestForm")) {
      activateDemoPage();
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  installDemoBadge();
  maskPrivateUi();
  setTimeout(activateDemoPage, 250);
})();
