
import argparse
import io
import json
import os
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup

PAGE = 'https://official.nba.com/nba-injury-report-2026-27-season/'

PDF_PATTERN = re.compile(
    r'Injury-Report_(\d{4}-\d{2}-\d{2})_'
    r'(\d{1,2})_(\d{2})(AM|PM)\.pdf',
    re.I
)

TEAMS = '''
AtlantaHawks BostonCeltics BrooklynNets CharlotteHornets
ChicagoBulls ClevelandCavaliers DallasMavericks DenverNuggets
DetroitPistons GoldenStateWarriors HoustonRockets IndianaPacers
LAClippers LosAngelesLakers MemphisGrizzlies MiamiHeat
MilwaukeeBucks MinnesotaTimberwolves NewOrleansPelicans
NewYorkKnicks OklahomaCityThunder OrlandoMagic
Philadelphia76ers PhoenixSuns PortlandTrailBlazers
SacramentoKings SanAntonioSpurs TorontoRaptors
UtahJazz WashingtonWizards
'''.split()

TEAM_MAP = {
    team.upper(): team
    for team in TEAMS
}

STATUSES = {
    'OUT',
    'QUESTIONABLE',
    'DOUBTFUL',
    'PROBABLE',
    'AVAILABLE'
}

S = requests.Session()

S.headers.update({
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'text/html,application/pdf'
})


def find_latest():
    response = S.get(PAGE, timeout=30)

    print(
        'NBA sayfa HTTP:',
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    reports = []

    soup = BeautifulSoup(
        response.text,
        'html.parser'
    )

    for anchor in soup.find_all('a', href=True):
        url = urljoin(PAGE, anchor['href'])
        parsed = urlparse(url)

        match = PDF_PATTERN.search(parsed.path)

        if (
            parsed.hostname != 'ak-static.cms.nba.com'
            or not match
        ):
            continue

        day, hour, minute, ampm = match.groups()

        try:
            stamp = datetime.strptime(
                f'{day} {hour}:{minute} {ampm}',
                '%Y-%m-%d %I:%M %p'
            )
        except ValueError:
            continue

        reports.append((stamp, url))

    if not reports:
        raise RuntimeError(
            'NBA sayfasinda PDF bulunamadi'
        )

    print(
        'Bulunan PDF:',
        len(reports),
        flush=True
    )

    return max(
        reports,
        key=lambda item: item[0]
    )


def cell(page, left, top, right, bottom):
    if bottom - top < 3:
        return ''

    cropped = page.crop((
        left,
        top + 0.5,
        right,
        bottom - 0.5
    ))

    text = cropped.extract_text(
        x_tolerance=2,
        y_tolerance=3
    ) or ''

    return re.sub(
        r'\s+',
        ' ',
        text
    ).strip()


def normalized_name(raw):
    parts = [
        part.strip()
        for part in raw.split(',')
    ]

    if len(parts) < 2 or not parts[-1]:
        raise RuntimeError(
            'Oyuncu adi hatali: ' + raw
        )

    first = parts[-1]
    last = ' '.join(parts[:-1])

    return re.sub(
        r'\s+',
        ' ',
        first + ' ' + last
    ).strip()


def parse_pdf(content):
    players = []
    missing = set()
    active_team = None

    with pdfplumber.open(
        io.BytesIO(content)
    ) as pdf:

        print(
            'PDF sayfalari:',
            len(pdf.pages),
            flush=True
        )

        for number, page in enumerate(
            pdf.pages,
            start=1
        ):
            scale = page.width / 841.95

            ratio = page.height / page.width
            expected = 595.35 / 841.95

            if abs(ratio - expected) > 0.025:
                raise RuntimeError(
                    f'Sayfa {number}: '
                    'beklenmeyen PDF boyutu'
                )

            coords = [
                260.2 * scale,
                421.0 * scale,
                581.7 * scale,
                662.1 * scale,
                822.8 * scale
            ]

            # Oyuncu sutunundaki yatay
            # sinir cizgilerini bul.
            edges = sorted({
                round(edge['top'], 2)
                for edge in page.edges
                if (
                    edge.get('orientation') == 'h'
                    and abs(
                        edge['x0'] - coords[1]
                    ) < 2 * scale
                    and abs(
                        edge['x1'] - coords[2]
                    ) < 2 * scale
                    and 70 * scale
                    < edge['top']
                    < page.height - 45 * scale
                )
            })

            if not edges:
                raise RuntimeError(
                    f'Sayfa {number}: '
                    'oyuncu satir cizgileri yok'
                )

            # Ilk sayfada basliklari gec.
            start = (
                120 if number == 1 else 76
            ) * scale

            bounds = [start] + [
                y for y in edges
                if y > start + 2 * scale
            ]

            end = page.height - 65 * scale

            if bounds[-1] < end - 5 * scale:
                bounds.append(end)

            before = len(players)

            for top, bottom in zip(
                bounds,
                bounds[1:]
            ):
                team_text = cell(
                    page,
                    coords[0],
                    top,
                    coords[1],
                    bottom
                )

                name = cell(
                    page,
                    coords[1],
                    top,
                    coords[2],
                    bottom
                )

                status = cell(
                    page,
                    coords[2],
                    top,
                    coords[3],
                    bottom
                ).upper()

                reason = cell(
                    page,
                    coords[3],
                    top,
                    coords[4],
                    bottom
                )

                team_key = re.sub(
                    r'[^A-Z0-9]',
                    '',
                    team_text.upper()
                )

                if team_key in TEAM_MAP:
                    active_team = TEAM_MAP[team_key]

                if (
                    'NOT YET SUBMITTED'
                    in reason.upper()
                ):
                    if not active_team:
                        raise RuntimeError(
                            'Rapor vermeyen takim bilinmiyor'
                        )

                    missing.add(active_team)
                    continue

                # PDF sutun basliklarini atla.
                if (
                    name.upper() in (
                        'PLAYER NAME',
                        'PLAYERNAME'
                    )
                    or status in (
                        'CURRENT STATUS',
                        'CURRENTSTATUS'
                    )
                ):
                    continue

                if status in STATUSES:
                    if (
                        not active_team
                        or ',' not in name
                    ):
                        raise RuntimeError(
                            'Oyuncu veya takim eksik: '
                            + name
                            + ' | '
                            + status
                        )

                    if not reason:
                        raise RuntimeError(
                            'Sakatlik aciklamasi bos: '
                            + name
                        )

                    players.append({
                        'player_name':
                            normalized_name(name),
                        'team': active_team,
                        'status': status,
                        'reason': reason
                    })

                elif (
                    not name
                    and not status
                    and reason
                ):
                    # Aciklama bir sonraki
                    # satirda devam edebilir.
                    if not players:
                        raise RuntimeError(
                            'Ilk oyuncudan once '
                            'aciklama bulundu'
                        )

                    players[-1]['reason'] += (
                        ' ' + reason
                    )

                elif name or status:
                    raise RuntimeError(
                        'Beklenmeyen hucre: '
                        + name
                        + ' | '
                        + status
                    )

            print(
                f'Sayfa {number}: '
                f'yeni oyuncu={len(players)-before}, '
                f'cizgi={len(edges)}',
                flush=True
            )

    if len(players) < 10:
        raise RuntimeError(
            'Supheli dusuk oyuncu sayisi'
        )

    seen = set()

    for player in players:
        key = (
            player['team'],
            player['player_name']
        )

        if (
            key in seen
            or not player['reason']
            or len(player['reason']) > 500
        ):
            raise RuntimeError(
                'Hatali oyuncu: '
                + str(player)
            )

        seen.add(key)

    return players, sorted(missing)


def check_examples(players):
    lookup = {
        player['player_name']: player
        for player in players
    }

    cases = [
        (
            'Bryce McGowens',
            'Left Elbow',
            'Left Knee'
        ),
        (
            'Yves Missi',
            'Left Knee',
            'Left Elbow'
        ),
        (
            'Ben Saraf',
            'On Assignment',
            'Right Calf'
        ),
        (
            'Nolan Traore',
            'Right Calf',
            'On Assignment'
        )
    ]

    for name, required, forbidden in cases:
        player = lookup.get(name)

        print(
            'KONTROL:',
            json.dumps(
                player,
                ensure_ascii=False
            ),
            flush=True
        )

        if player:
            reason = player['reason'].lower()

            if (
                required.lower() not in reason
                or forbidden.lower() in reason
            ):
                raise RuntimeError(
                    'Karisik aciklama: ' + name
                )

    print(
        'KONTROL:',
        json.dumps(
            lookup.get('Jarrett Allen'),
            ensure_ascii=False
        ),
        flush=True
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--dry-run',
        action='store_true'
    )

    args = parser.parse_args()

    print(
        '=== CIZGI MASASI NBA READER V6 ===',
        flush=True
    )

    stamp, url = find_latest()

    print(
        'PDF:',
        url,
        flush=True
    )

    response = S.get(
        url,
        timeout=45
    )

    print(
        'PDF HTTP:',
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    if not response.content.startswith(b'%PDF-'):
        raise RuntimeError(
            'Gelen dosya PDF degil'
        )

    players, missing = parse_pdf(
        response.content
    )

    check_examples(players)

    print(
        'Oyuncular:',
        len(players),
        flush=True
    )

    print(
        'Durumlar:',
        dict(Counter(
            player['status']
            for player in players
        )),
        flush=True
    )

    print(
        'Rapor vermeyen takimlar:',
        len(missing),
        flush=True
    )

    if args.dry_run:
        print(
            'TEST TAMAMLANDI - '
            'VERITABANINA YAZILMADI',
            flush=True
        )
        return

    token = os.environ.get(
        'NBA_IMPORT_TOKEN'
    )

    if not token:
        raise RuntimeError(
            'NBA_IMPORT_TOKEN eksik'
        )

    worker = os.environ.get(
        'WORKER_URL',
        'https://cizgi-masasi-api.k-melihsari.workers.dev'
    ).rstrip('/')

    if not worker.startswith('https://'):
        raise RuntimeError(
            'Worker HTTPS olmali'
        )

    payload = {
        'report_url': url,
        'report_key': stamp.strftime(
            '%Y-%m-%d_%H%M'
        ),
        'report_date': stamp.strftime(
            '%Y-%m-%d %H:%M ET'
        ),
        'players': players,
        'not_submitted_teams': missing
    }

    result = S.post(
        worker + '/api/import-nba',
        json=payload,
        headers={
            'Authorization': 'Bearer ' + token
        },
        timeout=45
    )

    print(
        'D1 HTTP:',
        result.status_code,
        flush=True
    )

    print(
        'D1 yaniti:',
        result.text[:1000],
        flush=True
    )

    result.raise_for_status()

    output = result.json()

    if not output.get('success'):
        raise RuntimeError(
            'D1 aktarimi basarisiz'
        )

    if (
        not output.get('skipped')
        and output.get('stored') != len(players)
    ):
        raise RuntimeError(
            'D1 oyuncu sayisi eslesmedi'
        )

    print(
        'NBA D1 AKTARIMI BASARILI',
        flush=True
    )


if __name__ == '__main__':
    main()
