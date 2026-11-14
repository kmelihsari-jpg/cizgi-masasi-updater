import argparse
import io
import json
import os
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import pdfplumber
import requests
from bs4 import BeautifulSoup

PAGE = 'https://official.nba.com/nba-injury-report-2026-27-season/'
PDF_PATTERN = re.compile(r'Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{1,2})_(\d{2})(AM|PM)\.pdf', re.I)
TEAMS = '''AtlantaHawks BostonCeltics BrooklynNets CharlotteHornets ChicagoBulls ClevelandCavaliers DallasMavericks DenverNuggets DetroitPistons GoldenStateWarriors HoustonRockets IndianaPacers LAClippers LosAngelesLakers MemphisGrizzlies MiamiHeat MilwaukeeBucks MinnesotaTimberwolves NewOrleansPelicans NewYorkKnicks OklahomaCityThunder OrlandoMagic Philadelphia76ers PhoenixSuns PortlandTrailBlazers SacramentoKings SanAntonioSpurs TorontoRaptors UtahJazz WashingtonWizards'''.split()
TEAM_MAP = {t.upper(): t for t in TEAMS}
STATUSES = {'OUT', 'QUESTIONABLE', 'DOUBTFUL', 'PROBABLE', 'AVAILABLE'}
S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/pdf'})


def find_latest():
    # The public listing is frequently CDN-cached. Bypass shared caches so
    # GitHub does not repeatedly import an older PDF as the newest report.
    # Independent requests use unique URLs and request headers.
    cache_tag = uuid4().hex
    params = {'_cizgi_check': cache_tag}
    headers = {
        'Cache-Control': 'no-cache, no-store, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0',
    }
    r = S.get(PAGE, params=params, headers=headers, timeout=30)
    print('NBA sayfa HTTP:', r.status_code, flush=True)
    print('NBA sayfa son URL:', r.url, flush=True)
    print('NBA sayfa cache basliklari:', json.dumps({
        k: r.headers.get(k) for k in
        ('Date', 'Age', 'CF-Cache-Status', 'Cache-Control', 'Last-Modified', 'ETag')
    }, ensure_ascii=False), flush=True)
    r.raise_for_status()
    reports = []
    for a in BeautifulSoup(r.text, 'html.parser').find_all('a', href=True):
        url = urljoin(PAGE, a['href'])
        parsed = urlparse(url)
        m = PDF_PATTERN.search(parsed.path)
        if parsed.hostname != 'ak-static.cms.nba.com' or not m:
            continue
        day, hour, minute, ampm = m.groups()
        try:
            dt = datetime.strptime(f'{day} {hour}:{minute} {ampm}', '%Y-%m-%d %I:%M %p')
        except ValueError:
            continue
        reports.append((dt, url))
    if not reports:
        raise RuntimeError('NBA sayfasinda PDF bulunamadi')
    reports = sorted(set(reports), key=lambda item: item[0])
    print('Bulunan PDF:', len(reports), flush=True)
    print('En yeni 5 PDF:', flush=True)
    for stamp, link in reports[-5:]:
        print(' ', stamp.strftime('%Y-%m-%d %I:%M %p ET'), link, flush=True)
    return reports[-1]


def cell(page, left, top, right, bottom):
    if bottom - top < 3:
        return ''
    text = page.crop((left, top + 0.5, right, bottom - 0.5)).extract_text(
        x_tolerance=2, y_tolerance=3
    ) or ''
    return re.sub(r'\s+', ' ', text).strip()


def normalized_name(raw):
    items = [x.strip() for x in raw.split(',')]
    if len(items) < 2 or not items[-1]:
        raise RuntimeError('Oyuncu adi hatali: ' + raw)
    return re.sub(r'\s+', ' ', items[-1] + ' ' + ' '.join(items[:-1])).strip()


def parse_pdf(content):
    players = []
    missing = set()
    active_team = None
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        print('PDF sayfalari:', len(pdf.pages), flush=True)
        for number, page in enumerate(pdf.pages, start=1):
            scale = page.width / 841.95
            if abs(page.height / page.width - 595.35 / 841.95) > 0.025:
                raise RuntimeError(f'Sayfa {number}: beklenmeyen PDF boyutu')
            coords = [260.2 * scale, 421.0 * scale, 581.7 * scale,
                      662.1 * scale, 822.8 * scale]
            # Cizgiler ayrik parcalar: sadece oyuncu sutunundaki parca kullanilir.
            horizontal_edges = set()
            for edge in page.edges:
                if (edge.get('orientation') == 'h'
                        and abs(edge['x0'] - coords[1]) < 2 * scale
                        and abs(edge['x1'] - coords[2]) < 2 * scale
                        and 70 * scale < edge['top'] < page.height - 45 * scale):
                    horizontal_edges.add(round(edge['top'], 2))
            edges = sorted(horizontal_edges)
            if not edges:
                raise RuntimeError(f'Sayfa {number}: oyuncu satir cizgileri yok')
            start = (120 if number == 1 else 76) * scale
            bounds = [start] + [y for y in edges if y > start + 2 * scale]
            end = page.height - 65 * scale
            if bounds[-1] < end - 5 * scale:
                bounds.append(end)
            count_before = len(players)
            for top, bottom in zip(bounds, bounds[1:]):
                team_text = cell(page, coords[0], top, coords[1], bottom)
                name = cell(page, coords[1], top, coords[2], bottom)
                status = cell(page, coords[2], top, coords[3], bottom).upper()
                reason = cell(page, coords[3], top, coords[4], bottom)
                team_key = re.sub(r'[^A-Z0-9]', '', team_text.upper())
                if team_key in TEAM_MAP:
                    active_team = TEAM_MAP[team_key]
                if 'NOT YET SUBMITTED' in reason.upper():
                    if not active_team:
                        raise RuntimeError(f'Sayfa {number}: rapor vermeyen takim bilinmiyor')
                    missing.add(active_team)
                    continue
                # Savunmaci baslik atlama: baslik oyuncu olarak islenmez.
                if name.upper() in ('PLAYER NAME', 'PLAYERNAME') or status in ('CURRENT STATUS', 'CURRENTSTATUS'):
                    continue
                if status in STATUSES:
                    if not active_team or ',' not in name:
                        raise RuntimeError(f'Sayfa {number}: oyuncu/takim eksik: {name} | {status}')
                    if not reason:
                        raise RuntimeError(f'Sayfa {number}: sakatlik nedeni bos: {name}')
                    players.append({'player_name': normalized_name(name),
                                    'team': active_team, 'status': status,
                                    'reason': reason})
                elif not name and not status and reason:
                    # Bir onceki oyuncunun aciklamasi sayfa degisiminde de devam edebilir.
                    if not players:
                        raise RuntimeError('Ilk oyuncudan once aciklama bulundu: ' + reason)
                    players[-1]['reason'] += ' ' + reason
                elif name or status:
                    raise RuntimeError(f'Sayfa {number}: beklenmeyen hucre: {name} | {status}')
            print(f'Sayfa {number}: yeni oyuncu={len(players)-count_before}, cizgi={len(edges)}', flush=True)
    if len(players) < 10:
        raise RuntimeError('Supheli dusuk oyuncu sayisi')
    seen = set()
    for p in players:
        key = (p['team'], p['player_name'])
        if key in seen or not p['reason'] or len(p['reason']) > 500:
            raise RuntimeError('Hatali oyuncu: ' + str(p))
        seen.add(key)
    return players, sorted(missing)


def check_examples(players):
    lookup = {p['player_name']: p for p in players}
    cases = [
        ('Bryce McGowens', 'Left Elbow', 'Left Knee'),
        ('Yves Missi', 'Left Knee', 'Left Elbow'),
        ('Ben Saraf', 'On Assignment', 'Right Calf'),
        ('Nolan Traore', 'Right Calf', 'On Assignment')
    ]
    for name, must, must_not in cases:
        p = lookup.get(name)
        print('KONTROL:', json.dumps(p, ensure_ascii=False), flush=True)
        if p and (must.lower() not in p['reason'].lower()
                  or must_not.lower() in p['reason'].lower()):
            raise RuntimeError('Karisik aciklama: ' + name)
    print('KONTROL:', json.dumps(lookup.get('Jarrett Allen'), ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print('=== CIZGI MASASI NBA READER V7 CACHE CONTROL ===', flush=True)
    stamp, url = find_latest()
    print('PDF:', url, flush=True)
    r = S.get(url, headers={'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}, timeout=45)
    print('PDF HTTP:', r.status_code, flush=True)
    r.raise_for_status()
    if not r.content.startswith(b'%PDF-'):
        raise RuntimeError('Gelen dosya PDF degil')
    players, missing = parse_pdf(r.content)
    check_examples(players)
    print('Oyuncular:', len(players), flush=True)
    print('Durumlar:', dict(Counter(p['status'] for p in players)), flush=True)
    print('Rapor vermeyen takimlar:', len(missing), flush=True)
    if args.dry_run:
        print('TEST TAMAMLANDI - VERITABANINA YAZILMADI', flush=True)
        return
    token = os.environ.get('NBA_IMPORT_TOKEN')
    if not token:
        raise RuntimeError('NBA_IMPORT_TOKEN eksik')
    worker = os.environ.get('WORKER_URL', 'https://cizgi-masasi-api.k-melihsari.workers.dev').rstrip('/')
    if not worker.startswith('https://'):
        raise RuntimeError('Worker HTTPS olmali')
    payload = {'report_url': url, 'report_key': stamp.strftime('%Y-%m-%d_%H%M'),
               'report_date': stamp.strftime('%Y-%m-%d %H:%M ET'),
               'players': players, 'not_submitted_teams': missing}
    res = S.post(worker + '/api/import-nba', json=payload,
                 headers={'Authorization': 'Bearer ' + token}, timeout=45)
    print('D1 HTTP:', res.status_code, flush=True)
    print('D1 yaniti:', res.text[:1000], flush=True)
    res.raise_for_status()
    answer = res.json()
    if not answer.get('success'):
        raise RuntimeError('D1 aktarimi basarisiz')
    if not answer.get('skipped') and answer.get('stored') != len(players):
        raise RuntimeError('D1 oyuncu sayisi eslesmedi')
    print('NBA D1 AKTARIMI BASARILI', flush=True)


if __name__ == '__main__':
    main()
