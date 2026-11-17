// Cloudflare Worker: cizgi-sakatlik-tetik
//
// Eskiden her cron'da (15 dk) kosulsuz GitHub'daki nba-official-sync.yml tetikleniyordu.
// NBA yeni PDF yayinlasa bile icerik cogu zaman AYNI (yalniz ust bilgideki saat degisiyor),
// ve GitHub her kisa job'i 1 dakika faturaladigi icin bu bos yere Actions kotasi yiyordu.
//
// Simdi: Worker once PDF'in "icerik parmak izini" hesaplar (sayfa metni, saat damgasi silinerek).
// Yalniz icerik DEGISTIYSE (veya emin olunamiyorsa) GitHub tetiklenir. Okuma, D1'e yazma ve resmi
// kaynak onceligi degismedi; hepsi yine nba-official-sync.yml icinde.
//
// Guvenlik ilkeleri (hepsi "emin degilsen tetikle" yonunde):
//   - Herhangi bir hata (sayfa, PDF, sifre cozme, KV, API) => GitHub tetiklenir.
//   - Parmak izi ayniysa bile, D1'deki rapor onceki tetiklenen rapordan eskiyse (import basarisiz) => tetiklenir.
//   - D1'deki rapor, en yeni PDF'ten STALE_DK dakikadan eskiyse => tetiklenir (varsayilan 60; 0 = kapali).
//
// Gerekli baglamalar: GITHUB_TOKEN (secret, mevcut), SAKATLIK_KV (KV namespace, yeni), TEST_KEY (mevcut).
// Istege bagli: STALE_DK, API_URL.

const REPO = 'kmelihsari-jpg/cizgi-masasi-updater';
const NBA_PAGE = 'https://official.nba.com/nba-injury-report-2026-27-season/';
const PDF_RE = /https:\/\/ak-static\.cms\.nba\.com\/referee\/injury\/Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{1,2})_(\d{2})(AM|PM)\.pdf/gi;
const DEFAULT_API = 'https://cizgi-masasi-api.k-melihsari.workers.dev';

async function tetikle(env, workflow, inputs) {
  const body = { ref: 'main' };
  if (inputs) body.inputs = inputs;
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + env.GITHUB_TOKEN,
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'cizgi-sakatlik-tetik',
    },
    body: JSON.stringify(body),
  });
  console.log('GitHub dispatch', workflow, r.status); // basarili: 204
  return r.status;
}

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- NBA PDF icerik parmak izi ------------------------------------------------------------
async function inflate(bytes) {
  const ds = new DecompressionStream('deflate');
  const w = ds.writable.getWriter();
  w.write(bytes).catch(() => {});
  w.close().catch(() => {});
  return new Uint8Array(await new Response(ds.readable).arrayBuffer());
}

export async function parmakIzi(buf) {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const text = new TextDecoder('latin1').decode(bytes); // 1 bayt = 1 karakter, ofsetler tutar
  const parts = [];
  let i = 0;
  for (;;) {
    const s = text.indexOf('stream', i);
    if (s < 0) break;
    if (text.startsWith('endstream', s - 3)) { i = s + 6; continue; }
    let start = s + 6;
    if (text[start] === '\r') start++;
    if (text[start] === '\n') start++;
    const e = text.indexOf('endstream', start);
    if (e < 0) break;
    const dict = text.slice(Math.max(0, text.lastIndexOf('obj', s)), s); // yalniz bu nesnenin sozlugu
    // Font/gorsel akislari rastgele adli ve buyuk: atla. Sayfa icerigi akislarini al.
    if (!/\/Length1|\/Image/.test(dict)) {
      try {
        // DecompressionStream "Trailing junk" hatasi verir: akisi /Length ile (yoksa sondaki satir sonlari atilarak) kes.
        const L = /\/Length (\d+)/.exec(dict);
        let end = L ? Math.min(start + parseInt(L[1], 10), e) : e;
        while (!L && end > start && (bytes[end - 1] === 10 || bytes[end - 1] === 13)) end--;
        const out = new TextDecoder('latin1').decode(await inflate(bytes.subarray(start, end)));
        if (/\bBT\b/.test(out) && /\bT[jJ]\b/.test(out)) {
          parts.push(out.replace(/\(\d\d:\d\d\) Tj/g, '(HH:MM) Tj')); // ust bilgideki saat damgasi
        }
      } catch { /* sikistirilmis baska veri: atla */ }
    }
    i = e + 9;
  }
  if (parts.length < 2) return null; // beklenen yapi yok: cagiran taraf tetikler
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(parts.join('\n--\n')));
  return [...new Uint8Array(digest)].slice(0, 8).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function enYeniRapor(html) {
  const bulunan = new Map();
  for (const m of html.matchAll(PDF_RE)) {
    const [url, gun, saat, dk, ap] = m;
    let h = parseInt(saat, 10) % 12;
    if (ap.toUpperCase() === 'PM') h += 12;
    bulunan.set(`${gun}_${String(h).padStart(2, '0')}${dk}`, url);
  }
  const anahtarlar = [...bulunan.keys()].sort();
  if (!anahtarlar.length) return null;
  const key = anahtarlar[anahtarlar.length - 1];
  return { key, url: bulunan.get(key) };
}

function dakika(key) { // 'YYYY-MM-DD_HHMM' -> dakika (ET, iki deger de ayni saat diliminde)
  const m = /^(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})$/.exec(key || '');
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) / 60000 : null;
}

// Donus: { tetikle: bool, neden: string, state?: {...} }
export async function sakatlikKarari(env) {
  const staleDk = Number(env.STALE_DK ?? 60);
  const api = (env.API_URL || DEFAULT_API).replace(/\/$/, '');
  try {
    const sayfa = await fetch(NBA_PAGE + '?_c=' + Date.now(), {
      headers: { 'Cache-Control': 'no-cache', 'User-Agent': 'Mozilla/5.0' },
    });
    if (!sayfa.ok) return { tetikle: true, neden: 'NBA sayfasi HTTP ' + sayfa.status };
    const rapor = enYeniRapor(await sayfa.text());
    if (!rapor) return { tetikle: true, neden: 'NBA sayfasinda PDF bulunamadi' };

    const pdf = await fetch(rapor.url, { headers: { 'Cache-Control': 'no-cache', 'User-Agent': 'Mozilla/5.0' } });
    if (!pdf.ok) return { tetikle: true, neden: 'PDF HTTP ' + pdf.status };
    const iz = await parmakIzi(await pdf.arrayBuffer());
    if (!iz) return { tetikle: true, neden: 'PDF parmak izi cikarilamadi' };

    const state = await env.SAKATLIK_KV.get('son', 'json');
    const yeni = { fp: iz, key: rapor.key, t: Date.now() };
    if (!state || state.fp !== iz) return { tetikle: true, neden: state ? 'icerik degisti' : 'ilk calisma', state: yeni };

    // Icerik ayni. D1'e onceki tetikleme gercekten islendi mi, ve ne kadar geride?
    const cevap = await fetch(api + '/api/nba-injuries');
    if (!cevap.ok) return { tetikle: true, neden: 'API HTTP ' + cevap.status, state: yeni };
    const d1Key = (await cevap.json())?.report?.report_key;
    if (!d1Key || d1Key < state.key) return { tetikle: true, neden: 'onceki import D1\'e islenmemis', state: yeni };
    const fark = dakika(rapor.key) - dakika(d1Key);
    if (staleDk > 0 && fark >= staleDk) return { tetikle: true, neden: `D1 raporu ${fark} dk geride (esik ${staleDk})`, state: yeni };
    return { tetikle: false, neden: 'icerik ayni, D1 guncel' };
  } catch (e) {
    return { tetikle: true, neden: 'hata: ' + (e && e.message) };
  }
}

async function sakatlikIsle(env, sadeceKarar) {
  const k = await sakatlikKarari(env);
  console.log('sakatlik karari:', JSON.stringify({ tetikle: k.tetikle, neden: k.neden }));
  if (sadeceKarar || !k.tetikle) return k.tetikle ? 'TETIKLENIRDI: ' + k.neden : 'ATLANDI: ' + k.neden;
  const durum = await tetikle(env, 'nba-official-sync.yml');
  if (durum === 204 && k.state) {
    try { await env.SAKATLIK_KV.put('son', JSON.stringify(k.state)); } catch (e) { console.log('KV yazma hatasi', e && e.message); }
  }
  return 'TETIKLENDI (' + durum + '): ' + k.neden;
}

// Tek cron: '5,20,35,50 * * * *' (UTC). Hangi tikte GitHub'in tetilecegi asagidaki tablolarla Worker'da belirlenir
// (bos tikler bedava: Worker istegi GitHub dakikasi harcamaz). Saatler Istanbul (UTC+3), :05/:20/:35/:50 izgarasinda.
function saatIstanbul(t) {
  const d = new Date(t + 3 * 3600 * 1000);
  return { saat: d.getUTCHours(), dk: d.getUTCMinutes() };
}
const hhmm = (s, d) => String(s).padStart(2, '0') + ':' + String(d).padStart(2, '0');
function aralik(saatler, dakikalar) { return saatler.flatMap((s) => dakikalar.map((d) => hhmm(s, d))); }
export const SAKATLIK_SLOTLARI = new Set([
  ...aralik([17, 18, 19], [5]),            // 17-20: saatte 1
  ...aralik([20, 21], [5, 35]),            // 20-22: 30 dk
  '22:05', '22:50', '23:35', '00:20',      // 22-01: 45 dk
  ...aralik([1, 2, 3], [5, 35]),           // 01-04: 30 dk
  ...aralik([4, 5], [5, 20, 35, 50]),      // 04-06: 15 dk (son tip-off'lar ~05:30)
]);
export function sakatlikSlotu(t) { const { saat, dk } = saatIstanbul(t); return SAKATLIK_SLOTLARI.has(hhmm(saat, dk)); }
// Iddaa: Istanbul 17, 18, 19, 20 - saatin ilk tiki (:05)
export function iddaaZamani(t) { const { saat, dk } = saatIstanbul(t); return saat >= 17 && saat <= 20 && dk < 10; }
// Karne snapshot: Istanbul 18, 19, 20 - iddaa'dan 10 dk sonra (18:15, 19:15, 20:15)
export function karneZamani(t) { const { saat, dk } = saatIstanbul(t); return saat >= 18 && saat <= 20 && dk < 10; }

export default {
  async scheduled(event, env, ctx) {
    if (sakatlikSlotu(event.scheduledTime)) ctx.waitUntil(sakatlikIsle(env, false));
    if (iddaaZamani(event.scheduledTime)) ctx.waitUntil(tetikle(env, 'iddaa-lines-sync.yml'));
    if (karneZamani(event.scheduledTime)) {
      ctx.waitUntil((async () => {
        await bekle(10 * 60 * 1000); // iddaa bitsin diye 10 dk bekle
        await tetikle(env, 'karne-otomatik.yml', { mode: 'snapshot' });
      })());
    }
  },
  // Elle test: ?k=TEST_KEY
  //   (varsayilan)  &is=sakatlik  -> kararla birlikte gercek tetikleme (degisim yoksa atlar)
  //                 &is=kontrol   -> yalniz karari soyler, GitHub'a dokunmaz
  //                 &is=zorla     -> kosulsuz tetikler (eski davranis)
  //                 &is=iddaa | karne -> GERCEK run baslatir
  async fetch(req, env) {
    const u = new globalThis.URL(req.url);
    if (!env.TEST_KEY || u.searchParams.get('k') !== env.TEST_KEY) return new Response('yok', { status: 404 });
    const j = u.searchParams.get('is') || 'sakatlik';
    if (j === 'kontrol') return new Response(await sakatlikIsle(env, true));
    if (j === 'sakatlik') return new Response(await sakatlikIsle(env, false));
    const MAP = {
      zorla: ['nba-official-sync.yml'],
      iddaa: ['iddaa-lines-sync.yml'],
      karne: ['karne-otomatik.yml', { mode: 'snapshot' }],
    };
    if (!MAP[j]) return new Response('bilinmeyen is: ' + j, { status: 400 });
    return new Response(j + ': ' + (await tetikle(env, ...MAP[j])));
  },
};
