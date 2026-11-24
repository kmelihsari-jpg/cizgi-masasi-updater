// ana-v3.js takim kodu renkleri: tablo + ayni macta yakin renk korumasi. Node ile calisir (ag yok).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const src = readFileSync(new URL('../site-patches/ana-v3.js', import.meta.url), 'utf8');
const blok = src.slice(src.indexOf('/*TXT_BASLA*/'), src.indexOf('/*TXT_BITIR*/'));
assert.ok(blok.length > 500, 'TXT blogu bulunamadi');
const f = new Function('tcol', blok + '; return {TXT, pairColors, cdist, TXT_MIN};');
const { TXT, pairColors, cdist, TXT_MIN } = f((t) => '#777');
// WCAG goreli parlaklik; siyah (#000) zemine karsi kontrast orani
const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const kontrast = (h) => { const n = parseInt(h.slice(1), 16); const L = .2126 * lin(n >> 16 & 255) + .7152 * lin(n >> 8 & 255) + .0722 * lin(n & 255); return (L + 0.05) / 0.05; };
const takimlar = Object.keys(TXT);
assert.equal(takimlar.length, 30);
for (const t of takimlar) {
  assert.equal(TXT[t].length, 2, t);
  for (const c of TXT[t]) { assert.match(c, /^#[0-9A-F]{6}$/); assert.ok(kontrast(c) >= 5.5, `${t} ${c} siyah zeminde soluk (kontrast ${kontrast(c).toFixed(1)})`); }
  assert.notEqual(TXT[t][0].toLowerCase(), TXT[t][1].toLowerCase(), t + ' iki rengi ayni');
}
// 30x29 tum maclarda iki takimin rengi ayirt edilebilir olmali
let en = 1e9, enM = '', kotu = [];
for (const a of takimlar) for (const h of takimlar) {
  if (a === h) continue;
  const [x, y] = pairColors(a, h), d = cdist(x, y);
  if (d < en) { en = d; enM = a + '@' + h; }
  if (d < TXT_MIN) kotu.push(`${a}@${h}:${d.toFixed(0)}`);
}
assert.equal(kotu.length, 0, 'yakin renkli maclar: ' + kotu.join(' '));
// Birincil renk mumkun oldugunca korunur: farkli renk ailelerinde ikisi de birincil kalir
assert.deepEqual(pairColors('BOS', 'MIA'), [TXT.BOS[0], TXT.MIA[0]]);
// Iki mavi: ikinci renge gecer, biri hala birincil
const m = pairColors('DAL', 'PHI'); assert.ok(cdist(m[0], m[1]) >= TXT_MIN);
// Bilinmeyen kod: hata vermez
assert.equal(pairColors('XXX', 'BOS').length, 2);
console.log(`PASS: 30 takim, 870 mac, en yakin cift ${enM} d=${en.toFixed(0)} (esik ${TXT_MIN})`);
