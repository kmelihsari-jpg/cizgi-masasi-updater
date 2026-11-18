"""slate_guncelle.py testi (ağ kullanmaz)."""
import json, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import slate_guncelle as sg

def mac(gid, utc, a, h, st=1):
    return {'gameId': gid, 'gameStatus': st, 'gameDateTimeUTC': utc,
            'awayTeam': {'teamTricode': a}, 'homeTeam': {'teamTricode': h}}

fik = {'leagueSchedule': {'gameDates': [
    {'gameDate': 'x', 'games': [
        mac('0022600200', '2026-11-19T00:00:00Z', 'CLE', 'MEM', 3),   # bu gece (ET 18 Kas)
        mac('0022600300', '2026-11-20T00:30:00Z', 'BOS', 'NYK'),      # yarın
        mac('0022600301', '2026-11-21T03:00:00Z', 'LAL', 'POR'),      # öbür gün
        mac('0012600001', '2026-11-20T00:00:00Z', 'AAA', 'BBB'),      # hazırlık: alınmaz
        mac('0022600999', '2026-12-10T00:00:00Z', 'MIA', 'ORL'),      # 7 günden ileri: alınmaz
        mac('0022600400', 'TBD', 'CHI', 'DET'),                       # saat yok: alınmaz
    ]}]}}

tmp = Path(tempfile.mkdtemp())
try:
    data = {'slate': [['2026-11-01T00:00:00Z', 'OLD', 'GON'],            # 10 günden eski: atılır
                      ['2026-11-14T00:00:00Z', 'NYK', 'IND'],            # korunur
                      ['2026-11-19T00:00:00Z', 'CLE', 'MEM']],           # yinelenmez
            'rows': [1]}
    (tmp / 'data.json').write_text(json.dumps(data), encoding='utf-8')
    (tmp / 'f.json').write_text(json.dumps(fik), encoding='utf-8')
    assert sg.main(['--data', str(tmp / 'data.json'), '--fikstur', str(tmp / 'f.json'), '--simdi', '2026-11-18T18:00:00Z']) == 0
    yeni = json.loads((tmp / 'data.json').read_text(encoding='utf-8'))
    assert yeni['rows'] == [1], 'diğer alanlar korunmalı'
    assert yeni['slate'] == [['2026-11-14T00:00:00Z', 'NYK', 'IND'], ['2026-11-19T00:00:00Z', 'CLE', 'MEM'],
                             ['2026-11-20T00:30:00Z', 'BOS', 'NYK'], ['2026-11-21T03:00:00Z', 'LAL', 'POR']], yeni['slate']
    # Fikstür boş/bozuksa dosyaya dokunulmaz
    once = (tmp / 'data.json').read_bytes()
    (tmp / 'f.json').write_text('{"leagueSchedule":{"gameDates":[]}}', encoding='utf-8')
    assert sg.main(['--data', str(tmp / 'data.json'), '--fikstur', str(tmp / 'f.json'), '--simdi', '2026-11-18T18:00:00Z']) == 0
    assert (tmp / 'data.json').read_bytes() == once
    (tmp / 'f.json').write_text('bozuk', encoding='utf-8')
    assert sg.main(['--data', str(tmp / 'data.json'), '--fikstur', str(tmp / 'f.json'), '--simdi', '2026-11-18T18:00:00Z']) == 0
    assert (tmp / 'data.json').read_bytes() == once
    # Gerçek seed/data.json biçimi: aynı takvim tekrar yazılınca dosya değişmez
    gercek = ROOT / 'seed' / 'data.json'
    if gercek.exists():
        shutil.copyfile(gercek, tmp / 'g.json')
        d = json.loads((tmp / 'g.json').read_text(encoding='utf-8'))
        assert all(isinstance(s, list) and len(s) == 3 and sg._utc(s[0]) for s in d['slate'])
    print('PASS: slate_guncelle (ekleme, eskileri ayıklama, hazırlık/uzak/saatsiz maç, bozuk fikstür)')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
