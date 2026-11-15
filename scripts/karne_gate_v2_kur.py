#!/usr/bin/env python3
"""Karne kapisi V2 + otomatik yayin tetikleyicisi. Idempotent; yedek alir.
1) Karne sakatlik kapisi: eski LIVE (inj-live.json) yerine Worker/CMREMOTE tazeligi.
2) Barem yasi esigi 36 dk -> 75 dk.
3) Pages yayini site-patches/** vb. push ile de baslar.
Calistir: python scripts/karne_gate_v2_kur.py  (repo kokunde)
"""
import pathlib, re, shutil, sys, time

root = pathlib.Path(__file__).resolve().parents[1]
stamp = time.strftime('%Y%m%d-%H%M%S')

def backup(p):
    shutil.copyfile(p, p.with_name(p.name + '.backup-' + stamp))

def must(cond, msg):
    if not cond:
        print('HATA:', msg); sys.exit(1)

# ---------- 1+2: karne_automation.py ----------
k = root / 'scripts' / 'karne_automation.py'
s = k.read_text(encoding='utf-8')
orig = s

WORKER_FN = '''
WORKER_API = 'https://cizgi-masasi-api.k-melihsari.workers.dev/api/espn-injuries'

def worker_sakatlik_taze(max_hours=3):
    """Sakatlik Worker'inda en az bir basarili ESPN toplamasi max_hours icinde olmali.
    Ulasilamazsa/bayatsa False doner (yeni Karne yazilmaz)."""
    import urllib.request
    try:
        req = urllib.request.Request(WORKER_API, headers={'Accept': 'application/json', 'User-Agent': 'CizgiMasasiKarne/1.0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode('utf-8'))
        last = d.get('last_check')
        if not d.get('success') or not last or int(d.get('count', 0)) < 20:
            return False, 'Worker ESPN verisi yok/az'
        t = dt.datetime.fromisoformat(str(last).replace(' ', 'T')).replace(tzinfo=dt.timezone.utc)
        h = (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600
        if h < -0.05 or h > max_hours:
            return False, f'Worker ESPN toplamasi {h:.1f} saat once'
        return True, f'Worker ESPN toplamasi {h:.1f} saat once'
    except Exception as exc:
        return False, 'Worker okunamadi: ' + str(exc)[:120]

'''
if 'def worker_sakatlik_taze' not in s:
    must('\ndef snapshot(args):' in s, 'snapshot() bulunamadi')
    s = s.replace('\ndef snapshot(args):', WORKER_FN + 'def snapshot(args):', 1)

if 'age>1.25' not in s:
    must('age>0.6' in s, 'age>0.6 bulunamadi')
    s = s.replace('age>0.6', 'age>1.25', 1)
    s = s.replace('# Barem akisi 18:30/19:30/20:30, snapshot 15 dakika sonra.',
                  '# Barem akisi 18:30/19:30/20:30, snapshot ~15 dk sonra; GitHub cron gecikmesi icin 75 dk tolerans.', 1)

CHECK = '''    wok, wmsg = worker_sakatlik_taze()
    if not wok:
        print('SKIP: sakatlik dogrulanamadi -', wmsg);return False
    print('Sakatlik kaynagi:', wmsg)
'''
if 'worker_sakatlik_taze()' not in s.split('def snapshot(args):',1)[1]:
    anchor = "    if not odds.get('rows'):print('SKIP: iddaa baremi yok');return False\n"
    must(anchor in s, 'barem satiri bulunamadi')
    s = s.replace(anchor, anchor + CHECK, 1)

OLD_LIVE = re.compile(r"typeof LIVE!=='undefined' && LIVE && Number\.isFinite\(Number\(LIVE\.ts\)\) && Number\(LIVE\.ts\)>1e12 && Date\.now\(\)-Number\(LIVE\.ts\)>=0 && Date\.now\(\)-Number\(LIVE\.ts\)<=3\*3600\*1000")
if OLD_LIVE.search(s):
    s = OLD_LIVE.sub("typeof window.CMREMOTE!=='undefined' && window.CMREMOTE && (window.CMREMOTE.espn || (window.CMREMOTE.list && Object.keys(window.CMREMOTE.list).length>0))", s, 1)
    s = s.replace("# LIVE.ts milisaniye epoch degilse veya 3 saatten eskiyse fail closed.",
                  "# Sakatlik: sayfanin kullandigi Worker verisi (window.CMREMOTE) yuklenmeden ve Worker 3 saatten eskiyse fail closed.", 1)
    s = s.replace("Sayfa/model/sakatlik LIVE hazir veya guncel degil; yeni Karne yazilmadi",
                  "Sayfa/model/sakatlik (CMREMOTE) hazir degil; yeni Karne yazilmadi", 1)
must('CMREMOTE' in s and 'LIVE.ts' not in s.split('def snapshot(args):',1)[1].split('result=page.evaluate',1)[0], 'LIVE kapisi degistirilemedi')

if s != orig:
    backup(k); k.write_text(s, encoding='utf-8'); print('GUNCELLENDI scripts/karne_automation.py')
else:
    print('ZATEN GUNCEL scripts/karne_automation.py')

# ---------- 3: Pages workflow push tetikleyicisi ----------
w = root / '.github' / 'workflows' / 'cizgi-masasi-otomatik-pages.yml'
t = w.read_text(encoding='utf-8'); o = t
PUSH = """  push:
    branches: [main]
    paths:
      - 'site-patches/**'
      - 'scripts/site_update_status.py'
      - 'scripts/dvp_position_patch.py'
      - 'scripts/karne_returning.py'
      - 'seed/confirmed-active.json'
"""
if "  push:\n" not in t.split('permissions:',1)[0]:
    must('\n  workflow_run:\n' in t, 'workflow_run blogu bulunamadi')
    t = t.replace('\n  workflow_run:\n', '\n' + PUSH + '  workflow_run:\n', 1)
IF_OLD = "if: github.event_name == 'workflow_dispatch' || (github.event_name == 'workflow_run' && github.event.workflow_run.conclusion == 'success')"
IF_NEW = "if: github.event_name == 'workflow_dispatch' || github.event_name == 'push' || (github.event_name == 'workflow_run' && github.event.workflow_run.conclusion == 'success')"
if IF_NEW not in t:
    must(IF_OLD in t, 'job if satiri bulunamadi'); t = t.replace(IF_OLD, IF_NEW, 1)
DEP_OLD = "if: github.event_name == 'workflow_run' || (github.event_name == 'workflow_dispatch' && inputs.yayinla == true)"
DEP_NEW = "if: github.event_name == 'workflow_run' || github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.yayinla == true)"
if DEP_NEW not in t:
    must(DEP_OLD in t, 'deploy if satiri bulunamadi'); t = t.replace(DEP_OLD, DEP_NEW, 1)
if t != o:
    backup(w); w.write_text(t, encoding='utf-8'); print('GUNCELLENDI Pages workflow')
else:
    print('ZATEN GUNCEL Pages workflow')
print('TAMAM')
