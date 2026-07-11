const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const windowMock = { addEventListener() {} };
const documentMock = {
  addEventListener() {},
  querySelector() { return null; },
};
const context = vm.createContext({
  console,
  Date,
  Math,
  Number,
  String,
  setTimeout,
  window: windowMock,
  document: documentMock,
});

const scriptPath = path.join(__dirname, "ai-backtest.js");
vm.runInContext(fs.readFileSync(scriptPath, "utf8"), context, { filename: scriptPath });

const api = windowMock.MarketSimAiBacktest;
assert.ok(api, "MarketSimAiBacktest should be exported");

const history = [];
const start = new Date("2025-01-01T00:00:00Z");
for (let index = 0; index < 220; index += 1) {
  const date = new Date(start);
  date.setUTCDate(date.getUTCDate() + index);
  const trend = 1 + index * 0.0012;
  const cycle = Math.sin(index / 9) * 0.035;
  const correction = index >= 125 && index <= 140 ? -0.1 : 0;
  history.push({
    date: date.toISOString().slice(0, 10),
    nav: Math.max(0.2, trend + cycle + correction),
  });
}

for (const cap of [0.2, 0.5, 0.8, 1]) {
  const result = api.runClientBacktest(
    history,
    {
      fund_code: "014855",
      initial_cash: 100000,
      trade_amount: 10000,
      max_position_ratio: cap,
      buy_fee_rate: 0.001,
      sell_fee_rate: 0.005,
      min_hold_days: 0,
    },
    { name: "frontend smoke fund" }
  );
  assert.ok(Number.isFinite(result.summary.final_value));
  for (const point of result.equity_curve) {
    const expectedTotal = point.cash + point.market_value;
    assert.ok(Math.abs(expectedTotal - point.total_value) <= 1e-7);
    const ratio = point.total_value > 0 ? point.market_value / point.total_value : 0;
    assert.ok(ratio <= cap + 1e-9, `frontend position cap ${cap} was exceeded`);
  }
}

console.log("Frontend AI backtester smoke check passed (20%, 50%, 80%, 100%)");
