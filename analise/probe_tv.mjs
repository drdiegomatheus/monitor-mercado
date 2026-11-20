import { getQuotes, getCandles } from '@mathieuc/tradingview';
import fs from 'fs';
const out = { inicio: new Date().toISOString(), quotes: {}, velas: {}, erros: [] };
const syms = ['BMFBOVESPA:PETR4', 'BMFBOVESPA:NVDC34', 'BMFBOVESPA:M2ST34', 'BMFBOVESPA:ANTH34', 'BMFBOVESPA:IVVB11', 'NASDAQ:NVDA', 'NASDAQ:ANT', 'BINANCE:BTCUSDT'];
try {
  const q = await getQuotes({ symbols: syms, timeoutMs: 20000 });
  out.quotes = JSON.parse(JSON.stringify(q));
} catch (e) { out.erros.push('quotes ' + String(e).slice(0, 300)); }
const f = t => new Date(t * 1000).toISOString();
for (const s of ['BMFBOVESPA:PETR4', 'BMFBOVESPA:NVDC34', 'BMFBOVESPA:M2ST34', 'BMFBOVESPA:ANTH34', 'NASDAQ:NVDA']) {
  for (const tf of ['1', '15', '30', '60', '1D']) {
    try {
      const c = await getCandles({ symbol: s, timeframe: tf, count: 3000, timeoutMs: 20000 });
      out.velas[s + '|' + tf] = { n: c.length, primeira: c.length ? f(c[0].time) : null, ultima: c.length ? f(c[c.length - 1].time) : null, ult_close: c.length ? c[c.length - 1].close : null, vol: c.length ? c[c.length - 1].volume : null };
    } catch (e) { out.velas[s + '|' + tf] = { erro: String(e).slice(0, 200) }; }
  }
}
out.fim = new Date().toISOString();
fs.writeFileSync('analise/probe.json', JSON.stringify(out, null, 1));
console.log('ok');
process.exit(0);
