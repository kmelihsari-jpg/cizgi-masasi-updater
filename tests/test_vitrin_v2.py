#!/usr/bin/env python3
"""Vitrin V2: yama idempotent, node ile sozdizimi gecerli, rol kapisi / secim yolu / AST-STL esigi / market sinirli davranis dogru."""
import json, pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import vitrin_v2 as v2
import karne_returning as kr

SRC = ROOT / 'tests' / 'fixture-model-oran.js'

def main():
    src = SRC.read_text(encoding='utf-8')
    chained = kr.patch_site(src, [])
    assert chained.count(v2.MARK) == 1 and 'CM-ORAN-KADEME-V1' in chained and 'CM-SAGLAM-MERDIVEN-V1' in chained
    assert kr.patch_site(chained, []) == chained, 'patch_site tekrar uygulaninca degisiyor'
    assert v2.patch_model(chained) == chained
    import oran_kademe as ok
    canli = v2._patch_v2(ok.patch_model(kr.patch_text(src, [])))       # 27 Kasim 23:24 yayinindan sonraki canli model
    assert v2.MARK_D not in canli
    yeni = v2.patch_model(canli)
    assert yeni.count(v2.MARK_D) == 1 and yeni == chained and v2.patch_model(yeni) == yeni, 'canli modele donus kapisi eklenemedi'
    assert chained.count(v2.MARK_A) == 1 and chained.count(v2.MARK_P) == 1 and 'cmAdjE(e,P[S.pid],mk)' in chained
    assert 'r.adj.n<3&&!r.adj.pr' in chained
    # 23:37 yayinindan sonraki canli model (donus kapisi var, onkabul yok) -> yeni yamalar eklenir
    onceki = v2._patch_donus(v2._patch_v2(ok.patch_model(kr.patch_text(src, []))))
    assert v2.MARK_A not in onceki and v2.MARK_P not in onceki and v2.patch_model(onceki) == chained
    # oran kademesi olmadan uygulanmaz (yanlis sirada sessizce yarim yama olmasin)
    try:
        v2.patch_model(src); raise SystemExit('oran kademesi yokken yama uygulandi')
    except RuntimeError:
        pass
    # beklenen kod degisirse HATA verir, dosya yazilmaz
    broken = chained.replace('mpg(p.id)<22||cmRol(all))return null;', 'mpg(p.id)<22)return null;').replace(v2.MARK, '')
    try:
        v2.patch_model(broken); raise SystemExit('bozuk modelde hata vermedi')
    except RuntimeError:
        pass
    if not shutil.which('node'):
        print('SKIP: node yok, sentetik davranis testi atlandi (yama ve idempotentlik testleri gecti)');return
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / 'model.js'; f.write_text(chained, encoding='utf-8')
        subprocess.run(['node', '--check', str(f)], check=True)
        r = subprocess.run(['node', str(ROOT / 'tests' / 'vitrin_v2_harness.js'), str(f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        res = json.loads(r.stdout.strip().splitlines()[-1])
    assert res['rolDus']['pass'] == [], res['rolDus']            # son 2 mac 20 ve 18 dk
    assert res['rolOk']['pass'] == ['2|PTS|saglam'], res['rolOk']
    assert res['rolL3']['pass'] == [], res['rolL3']              # son 3 mac sezonun %85'inin altinda
    assert res['rolTek']['pass'] == ['4|PTS|saglam'], res['rolTek']  # tek kotu mac engellemez
    assert res['tagTara'].get('secim', 0) >= 1, res['tagTara']   # Saglam/Deger disinda secim yolu calisiyor
    assert res['astLo'][1] is False and res['astHi'][1] is True, (res['astLo'], res['astHi'])
    assert len(res['mkCap']['pass']) == 2 and res['mkCap']['cap'] == ['7|PTS|true'], res['mkCap']
    assert len(res['mkMix']['pass']) == 3 and res['mkMix']['cap'] == [], res['mkMix']
    assert res['donusAvail']['pass'] == [] and res['donusQ']['pass'] == [], (res['donusAvail'], res['donusQ'])   # donuyor / Q: elenir
    assert res['donusOut']['pass'] == ['2|PTS|saglam'] and res['donusD']['pass'] == ['2|PTS|saglam'], (res['donusOut'], res['donusD'])
    assert res['donusTek']['pass'] == ['2|PTS|saglam'] and res['donusYok']['pass'] == ['2|PTS|saglam']
    pr = res['prior']
    assert pr['pr0'] is True and pr['f0'] > 1.07 and pr['f0'] <= 1.12 and pr['mu0'] > 5 * 1.07, pr       # n=0: onkabul
    assert pr['pr1'] is False and pr['f1'] == 1.07, pr                                                    # n>0: eski hesap
    a, p_, z = res['priorCap']
    assert 1.07 < a <= 1.12 and p_ <= 1.12 and z == 1, res['priorCap']
    assert res['donusAd'] == ['Reaves', None] and res['donusAdOut'] is None, (res['donusAd'], res['donusAdOut'])
    print('OK: vitrin_v2')

if __name__ == '__main__':
    main()
