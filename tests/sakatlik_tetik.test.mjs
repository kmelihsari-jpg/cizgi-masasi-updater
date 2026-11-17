// worker/sakatlik-tetik.js karar mantigi testi. Ag yok, GitHub Actions yok: fetch ve KV taklit edilir.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import worker, { sakatlikKarari, parmakIzi, sakatlikSlotu, iddaaZamani, karneZamani, SAKATLIK_SLOTLARI } from '../worker/sakatlik-tetik.js';

const fx = (n) => readFileSync(new URL('./fixtures/' + n, import.meta.url));
const PDF = {
  '0600': fx('Injury-Report_2026-11-17_06_00AM.pdf'),
  '0630': fx('Injury-Report_2026-11-17_06_30AM.pdf'),
  degisik: fx('Injury-Report_2026-11-17_06_45AM-degisik-durum.pdf'), // tek oyuncunun durumu degistirilmis
};
const URL_ = (hhmm) => `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_${hhmm}AM.pdf`;

function ortam({ sayfaPdfler, pdfBody, d1Key, kv, pdfDurum = 200, stale }) {
  const store = new Map(kv ? [['son', JSON.stringify(kv)]] : []);
  const env = {
    STALE_DK: stale,
    SAKATLIK_KV: {
      async get(k, tip) { const v = store.get(k); return v == null ? null : (tip === 'json' ? JSON.parse(v) : v); },
      async put(k, v) { store.set(k, v); },
    },
  };
  globalThis.fetch = async (url) => {
    url = String(url);
    if (url.startsWith('https://official.nba.com/')) return new Response(sayfaPdfler.map((u) => `<a href="${u}">x</a>`).join(''));
    if (url.includes('ak-static.cms.nba.com')) return new Response(pdfDurum === 200 ? pdfBody : 'hata', { status: pdfDurum });
    if (url.endsWith('/api/nba-injuries')) return new Response(JSON.stringify({ success: true, report: d1Key ? { report_key: d1Key } : null }));
    throw new Error('beklenmeyen istek: ' + url);
  };
  return env;
}

// 1) Parmak izi: ayni icerik (saat farkli) ayni iz, degisen durum farkli iz
const a = await parmakIzi(PDF['0600']), b = await parmakIzi(PDF['0630']), c = await parmakIzi(PDF.degisik);
assert.ok(a && a.length === 16);
assert.equal(a, b, 'ayni icerikli iki rapor ayni parmak izini vermeli');
assert.notEqual(a, c, 'bir oyuncunun durumu degisince parmak izi degismeli');
assert.equal(await parmakIzi(new TextEncoder().encode('%PDF-1.4 bozuk')), null);

const liste = [URL_('06_00'), URL_('06_30')];
const onceki = { fp: a, key: '2026-11-17_0600', t: 1 };

// 2) Ilk calisma -> tetikle
let k = await sakatlikKarari(ortam({ sayfaPdfler: liste, pdfBody: PDF['0630'], d1Key: null }));
assert.equal(k.tetikle, true); assert.equal(k.neden, 'ilk calisma'); assert.equal(k.state.key, '2026-11-17_0630');

// 3) Icerik ayni, D1 onceki tetiklemeyi islemis, geride degil -> ATLA
k = await sakatlikKarari(ortam({ sayfaPdfler: liste, pdfBody: PDF['0630'], d1Key: '2026-11-17_0600', kv: onceki, stale: 60 }));
assert.equal(k.tetikle, false, k.neden);

// 4) Icerik degisti -> tetikle
k = await sakatlikKarari(ortam({ sayfaPdfler: [...liste, URL_('06_45')], pdfBody: PDF.degisik, d1Key: '2026-11-17_0600', kv: onceki }));
assert.equal(k.tetikle, true); assert.equal(k.neden, 'icerik degisti');

// 5) Icerik ayni ama onceki import D1'e islenmemis -> tekrar dene
k = await sakatlikKarari(ortam({ sayfaPdfler: liste, pdfBody: PDF['0630'], d1Key: '2026-11-16_2345', kv: onceki }));
assert.equal(k.tetikle, true); assert.match(k.neden, /islenmemis/);

// 6) PDF indirilemedi -> tetikle (fail-open)
k = await sakatlikKarari(ortam({ sayfaPdfler: liste, pdfBody: '', d1Key: '2026-11-17_0600', kv: onceki, pdfDurum: 500 }));
assert.equal(k.tetikle, true); assert.match(k.neden, /PDF HTTP 500/);

// 7) NBA sayfasinda PDF yok / PDF bozuk -> tetikle
k = await sakatlikKarari(ortam({ sayfaPdfler: [], pdfBody: PDF['0630'], d1Key: '2026-11-17_0600', kv: onceki }));
assert.equal(k.tetikle, true);
k = await sakatlikKarari(ortam({ sayfaPdfler: liste, pdfBody: 'bu pdf degil', d1Key: '2026-11-17_0600', kv: onceki }));
assert.equal(k.tetikle, true); assert.match(k.neden, /parmak izi/);

// 8) D1 raporu esikten fazla geride (60 dk) -> tetikle; esik 0 ise atla
const eski = { fp: a, key: '2026-11-17_0500', t: 1 };
k = await sakatlikKarari(ortam({ sayfaPdfler: [URL_('06_00'), URL_('07_00')], pdfBody: PDF['0600'], d1Key: '2026-11-17_0500', kv: eski, stale: 60 }));
assert.equal(k.tetikle, true); assert.match(k.neden, /geride/);
k = await sakatlikKarari(ortam({ sayfaPdfler: [URL_('06_00'), URL_('07_00')], pdfBody: PDF['0600'], d1Key: '2026-11-17_0500', kv: eski, stale: 0 }));
assert.equal(k.tetikle, false);

// 9) KV hatasi -> tetikle
const bozukKv = ortam({ sayfaPdfler: liste, pdfBody: PDF['0630'], d1Key: '2026-11-17_0600' });
bozukKv.SAKATLIK_KV.get = async () => { throw new Error('kv down'); };
k = await sakatlikKarari(bozukKv);
assert.equal(k.tetikle, true); assert.match(k.neden, /hata/);

// 10) Zamanlama: tek cron (:05/:20/:35/:50 UTC), Istanbul = UTC+3
const ist = (hh, mm) => Date.UTC(2026, 10, 17, hh - 3 + 24, mm) ; // Istanbul saatini UTC ms'ye cevir
const tikler = [];
for (let h = 0; h < 24; h++) for (const m of [5, 20, 35, 50]) tikler.push([h, m]);
const calisan = tikler.filter(([h, m]) => sakatlikSlotu(ist(h, m))).map(([h, m]) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
assert.equal(calisan.length, 19);
assert.deepEqual(calisan, ['00:05','00:35','01:05','01:35','02:05','02:35','03:05','03:35','04:05','04:35','17:05','18:05','19:05','20:05','21:05','22:05','22:35','23:05','23:35']);
// 17-22 saatte 1 (:35 yok), 22-05 yarim saatte bir (:20/:50 yok), 05-17 hic
assert.ok(!sakatlikSlotu(ist(20, 35)) && !sakatlikSlotu(ist(21, 35)) && !sakatlikSlotu(ist(22, 20)) && !sakatlikSlotu(ist(23, 50)) && !sakatlikSlotu(ist(1, 20)) && !sakatlikSlotu(ist(4, 50)) && !sakatlikSlotu(ist(5, 5)) && !sakatlikSlotu(ist(12, 5)));
// Iddaa/karne saatleri degismedi: yalniz :05 tikleri (karne Worker'da 10 dk bekleyip tetikler)
assert.deepEqual(tikler.filter(([h, m]) => iddaaZamani(ist(h, m))).map(([h, m]) => h + ':' + m), ['17:5', '18:5', '19:5', '20:5']);
assert.deepEqual(tikler.filter(([h, m]) => karneZamani(ist(h, m))).map(([h, m]) => h + ':' + m), ['18:5', '19:5', '20:5']);

// 12) Varsayilan (PARMAK_IZI yok): slotlarda kosulsuz tetikler, slot disinda tetiklemez, KV/PDF'e dokunmaz
{
  const cagrilar = [];
  globalThis.fetch = async (url, init) => { cagrilar.push(String(url).split('/workflows/')[1]?.split('/')[0] || String(url)); return new Response(null, { status: 204 }); };
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(p) };
  const env = { GITHUB_TOKEN: 'x' }; // KV bile yok: kullanilmamali
  const kos = async (hh, mm) => { cagrilar.length = 0; bekleyen.length = 0; await worker.scheduled({ scheduledTime: ist(hh, mm) }, env, ctx); await Promise.all(bekleyen); return [...cagrilar]; };
  assert.deepEqual(await kos(23, 35), ['nba-official-sync.yml']);
  assert.deepEqual(await kos(22, 20), []);   // slot disi
  assert.deepEqual(await kos(12, 5), []);    // gunduz kapali
  assert.deepEqual(await kos(17, 5), ['nba-official-sync.yml', 'iddaa-lines-sync.yml']); // sakatlik + iddaa
  assert.deepEqual(await kos(21, 35), []);   // 17-22 saatte 1: :35 yok
  assert.match(await (async () => { globalThis.fetch = async () => { throw new Error('ag yok'); }; return worker.fetch(new Request('https://x/?k=a&is=kontrol'), { TEST_KEY: 'a' }).then((r) => r.text()); })(), /parmak izi kapali/);
}

// 11) CPU: 3 ardisik parmak izi (Workers ucretsiz plani 10 ms/cagri)
const t0 = process.cpuUsage();
for (const p of [PDF['0600'], PDF['0630'], PDF.degisik]) await parmakIzi(p);
const ms = (process.cpuUsage(t0).user + process.cpuUsage(t0).system) / 3000;
console.log(`PASS: 10 senaryo; parmak izi ortalama CPU ~${ms.toFixed(1)} ms/PDF`);
