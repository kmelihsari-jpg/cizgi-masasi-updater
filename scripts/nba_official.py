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
            edges = sorted({round(e['top'], 2) for e in page.edges
                if e.get('orientation') == 'h'
