const TradingView = require('@mathieuc/tradingview');
const fs = require('fs');
const out = { inicio: new Date().toISOString(), quotes: {}, velas: {}, erros: [] };
const syms = ['BMFBOVESPA:PETR4', 'BMFBOVESPA:NVDC34', 'BMFBOVESPA:M2ST34', 'BMFBOVESPA:ANTH34', 'BMFBOVESPA:IVVB11', 'NASDAQ:NVDA', 'NASDAQ:ANT', 'BINANCE:BTCUSDT'];
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function quotes() {
  const client = new TradingView.Client();
  const qs = new client.Session.Quote({ fields: ['lp', 'lp_time', 'volume', 'update_mode', 'update_mode_seconds', 'delay', 'currency_code', 'short_name', 'rtc', 'type'] });
  for (const s of syms) {
    const m = new qs.Market(s);
    m.onData(d => { out.quotes[s] = Object.assign(out.quotes[s] || {}, d); });
    m.onError((...e) => { out.quotes[s] = { erro: e.join(' ').slice(0, 200) }; });
  }
  await sleep(12000);
  client.end();
}
async function velas() {
  for (const s of ['BMFBOVESPA:PETR4', 'BMFBOVESPA:NVDC34', 'BMFBOVESPA:M2ST34', 'BMFBOVESPA:ANTH34', 'NASDAQ:NVDA']) {
    for (const tf of ['1', '15', '30', '60', '1D']) {
      const client = new TradingView.Client();
      const chart = new client.Session.Chart();
      let erro = null;
      chart.onError((...e) => { erro = e.join(' ').slice(0, 200); });
      chart.setMarket(s, { timeframe: tf, range: 2000 });
      await sleep(5000);
      const p = chart.periods || [];
      const f = t => new Date(t * 1000).toISOString();
      out.velas[s + '|' + tf] = { n: p.length, primeira: p.length ? f(p[p.length - 1].time) : null, ultima: p.length ? f(p[0].time) : null, ult_close: p.length ? p[0].close : null, vol: p.length ? p[0].volume : null, erro };
      client.end();
    }
  }
}
(async () => {
  try { await quotes(); } catch (e) { out.erros.push('quotes ' + String(e).slice(0, 200)); }
  try { await velas(); } catch (e) { out.erros.push('velas ' + String(e).slice(0, 200)); }
  out.fim = new Date().toISOString();
  fs.writeFileSync('analise/probe.json', JSON.stringify(out, null, 1));
  console.log('ok');
  process.exit(0);
})();
