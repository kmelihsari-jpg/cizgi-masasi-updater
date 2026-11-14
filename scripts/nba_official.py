
import io
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup


# CIZGI MASASI - NBA OFFICIAL INJURY READER

PAGE = (
    "https://official.nba.com/"
    "nba-injury-report-2026-27-season/"
)

PDF_RX = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_"
    r"(\d{1,2})_(\d{2})(AM|PM)\.pdf",
    re.I
)

STATUSES = (
    "Questionable|Available|Doubtful|Probable|Out"
)

PLAYER_RX = re.compile(
    r"(?P<last>[A-Za-zÀ-ÿ.'’-]+),"
    r"(?P<first>[A-Za-zÀ-ÿ.'’-]+)"
    r"\s+(?P<status>" + STATUSES + r")\b",
    re.I
)

HEADER_RX = re.compile(
    r"^Injury Report:|^GameDate\s|^Page\d+of\d+",
    re.I
)

TEAMS = [
    "AtlantaHawks",
    "BostonCeltics",
    "BrooklynNets",
    "CharlotteHornets",
    "ChicagoBulls",
    "ClevelandCavaliers",
    "DallasMavericks",
    "DenverNuggets",
    "DetroitPistons",
    "GoldenStateWarriors",
    "HoustonRockets",
    "IndianaPacers",
    "LAClippers",
    "LosAngelesLakers",
    "MemphisGrizzlies",
    "MiamiHeat",
    "MilwaukeeBucks",
    "MinnesotaTimberwolves",
    "NewOrleansPelicans",
    "NewYorkKnicks",
    "OklahomaCityThunder",
    "OrlandoMagic",
    "Philadelphia76ers",
    "PhoenixSuns",
    "PortlandTrailBlazers",
    "SacramentoKings",
    "SanAntonioSpurs",
    "TorontoRaptors",
    "UtahJazz",
    "WashingtonWizards"
]

TEAM_RX = re.compile(
    "|".join(
        sorted(
            map(re.escape, TEAMS),
            key=len,
            reverse=True
        )
    )
)

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/pdf"
})


def find_latest():
    print("NBA resmi rapor sayfasi kontrol ediliyor...",
          flush=True)

    response = SESSION.get(PAGE, timeout=30)

    print(
        "NBA sayfa HTTP:",
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    reports = []

    for anchor in soup.find_all("a", href=True):
        url = urljoin(PAGE, anchor["href"])

        parsed = urlparse(url)
        match = PDF_RX.search(parsed.path)

        if not match:
            continue

        if parsed.hostname != "ak-static.cms.nba.com":
            continue

        date, hour, minute, ampm = match.groups()

        try:
            dt = datetime.strptime(
                f"{date} {hour}:{minute} {ampm.upper()}",
                "%Y-%m-%d %I:%M %p"
            )
        except ValueError:
            continue

        reports.append((dt, url))

    print(
        "Bulunan PDF sayisi:",
        len(reports),
        flush=True
    )

    if not reports:
        raise RuntimeError(
            "NBA sayfasinda PDF linki bulunamadi"
        )

    dt, url = max(
        reports,
        key=lambda item: item[0]
    )

    return dt, url


def normalize_player(last, first):
    last = re.sub(
        r"(Jr\.|Jr|Sr\.|Sr|II|III|IV)$",
        r" \1",
        last
    )

    return f"{first} {last}".replace(
        "  ", " "
    ).strip()


def parse_pdf(raw):
    records = []
    unsubmitted = []

    team = None
    current = None

    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        print(
            "PDF sayfa sayisi:",
            len(pdf.pages),
            flush=True
        )

        for page in pdf.pages:
            text = page.extract_text() or ""

            for raw_line in text.splitlines():
                line = raw_line.strip()

                if not line:
                    continue

                if HEADER_RX.match(line):
                    current = None
                    continue

                team_match = TEAM_RX.search(line)

                if team_match:
                    team = team_match.group(0)
                    current = None

                normalized = line.replace(
                    " ", ""
                ).upper()

                if "NOTYETSUBMITTED" in normalized:
                    unsubmitted.append(
                        team or "UNKNOWN"
                    )
                    current = None
                    continue

                match = PLAYER_RX.search(line)

                if match:
                    if not team:
                        raise RuntimeError(
                            "Oyuncunun takimi bulunamadi: "
                            + line
                        )

                    current = {
                        "player_name": normalize_player(
                            match.group("last"),
                            match.group("first")
                        ),
                        "team": team,
                        "status": match.group(
                            "status"
                        ).upper(),
                        "reason": line[
                            match.end():
                        ].strip()[:500]
                    }

                    records.append(current)

                elif current and not team_match:
                    # Aciklamanin devam satirlarini
                    # son oyuncuya ekle.
                    if not re.search(
                        r"\b\d{2}:\d{2}\(ET\)",
                        line
                    ):
                        current["reason"] = (
                            current["reason"]
                            + " "
                            + line
                        ).strip()[:500]

    if not records:
        raise RuntimeError(
            "PDF icinden oyuncu bulunamadi"
        )

    seen = set()

    for player in records:
        key = (
            player["team"],
            player["player_name"]
        )

        if key in seen:
            raise RuntimeError(
                "Tekrar eden oyuncu: " + str(key)
            )

        seen.add(key)

    return records, sorted(set(unsubmitted))


def main():
    print(
        "=== CIZGI MASASI NBA SYNC BASLADI ===",
        flush=True
    )

    # 1 - En guncel raporu bul
    dt, url = find_latest()

    print(
        "Secilen rapor:",
        url,
        flush=True
    )

    # 2 - PDF dosyasini indir
    response = SESSION.get(
        url,
        timeout=45
    )

    print(
        "PDF indirme HTTP:",
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    if not response.content.startswith(b"%PDF-"):
        raise RuntimeError(
            "Indirilen dosya PDF degil"
        )

    # 3 - Oyunculari ayristir
    records, missing = parse_pdf(
        response.content
    )

    print(
        "Oyuncular:",
        len(records),
        flush=True
    )

    print(
        "Rapor gondermeyen takimlar:",
        len(missing),
        flush=True
    )

    statuses = {}

    for player in records:
        status = player["status"]
        statuses[status] = (
            statuses.get(status, 0) + 1
        )

    print(
        "Durum dagilimi:",
        statuses,
        flush=True
    )

    print(
        "Ilk 5 oyuncu:",
        json.dumps(
            records[:5],
            ensure_ascii=False
        ),
        flush=True
    )

    # 4 - Cloudflare'a gonderilecek veri
    data = {
        "report_url": url,
        "report_key": dt.strftime(
            "%Y-%m-%d_%H%M"
        ),
        "report_date": dt.strftime(
            "%Y-%m-%d %H:%M ET"
        ),
        "players": records,
        "not_submitted_teams": missing
    }

    # 5 - Gizli anahtar kontrolu
    token = os.getenv("NBA_IMPORT_TOKEN")

    if not token:
        raise RuntimeError(
            "GitHub NBA_IMPORT_TOKEN secret eksik"
        )

    worker = os.getenv(
        "WORKER_URL",
        "https://cizgi-masasi-api.k-melihsari.workers.dev"
    ).rstrip("/")

    if not worker.startswith("https://"):
        raise RuntimeError(
            "HTTPS Worker adresi gerekli"
        )

    # 6 - NBA verilerini Cloudflare'a aktar
    print(
        "Cloudflare D1 aktarimi basliyor...",
        flush=True
    )

    result = SESSION.post(
        worker + "/api/import-nba",
        json=data,
        headers={
            "Authorization": "Bearer " + token
        },
        timeout=45
    )

    print(
        "D1 aktarim HTTP:",
        result.status_code,
        flush=True
    )

    print(
        "Sunucu yaniti:",
        result.text[:2000],
        flush=True
    )

    # HTTP hatalarini GitHub'a bildir
    result.raise_for_status()

    try:
        result_data = result.json()
    except ValueError:
        raise RuntimeError(
            "Cloudflare gecersiz JSON dondurdu"
        )

    if not result_data.get("success"):
        raise RuntimeError(
            "NBA aktarimi basarisiz: "
            + str(result_data)
        )

    if result_data.get("skipped"):
        print(
            "Bu rapor zaten aktarilmis. "
            "Yeni kayit gerekmiyor.",
            flush=True
        )
    else:
        stored = result_data.get("stored")

        if stored != len(records):
            raise RuntimeError(
                "Kaydedilen oyuncu sayisi uyusmuyor"
            )

        print(
            "D1'e kaydedilen oyuncu:",
            stored,
            flush=True
        )

    print(
        "=== NBA SENKRONIZASYONU BASARILI ===",
        flush=True
    )


if __name__ == "__main__":
    main()
