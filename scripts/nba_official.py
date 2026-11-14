
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

PAGE = (
    "https://official.nba.com/"
    "nba-injury-report-2026-27-season/"
)

PDF_RX = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_"
    r"(\d{1,2})_(\d{2})(AM|PM)\.pdf",
    re.I
)

STATUSES = {
    "OUT", "QUESTIONABLE", "DOUBTFUL",
    "PROBABLE", "AVAILABLE"
}

TEAMS = [
    "AtlantaHawks", "BostonCeltics",
    "BrooklynNets", "CharlotteHornets",
    "ChicagoBulls", "ClevelandCavaliers",
    "DallasMavericks", "DenverNuggets",
    "DetroitPistons", "GoldenStateWarriors",
    "HoustonRockets", "IndianaPacers",
    "LAClippers", "LosAngelesLakers",
    "MemphisGrizzlies", "MiamiHeat",
    "MilwaukeeBucks", "MinnesotaTimberwolves",
    "NewOrleansPelicans", "NewYorkKnicks",
    "OklahomaCityThunder", "OrlandoMagic",
    "Philadelphia76ers", "PhoenixSuns",
    "PortlandTrailBlazers", "SacramentoKings",
    "SanAntonioSpurs", "TorontoRaptors",
    "UtahJazz", "WashingtonWizards"
]

TEAM_MAP = {t.upper(): t for t in TEAMS}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/pdf"
})


def latest_report():
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

    found = []

    for link in soup.find_all("a", href=True):
        url = urljoin(PAGE, link["href"])
        parsed = urlparse(url)
        match = PDF_RX.search(parsed.path)

        if not match:
            continue

        if parsed.hostname != "ak-static.cms.nba.com":
            continue

        day, hour, minute, ampm = match.groups()

        stamp = datetime.strptime(
            f"{day} {hour}:{minute} {ampm}",
            "%Y-%m-%d %I:%M %p"
        )

        found.append((stamp, url))

    if not found:
        raise RuntimeError(
            "NBA sayfasinda PDF bulunamadi"
        )

    print(
        "Bulunan PDF:",
        len(found),
        flush=True
    )

    return max(found, key=lambda x: x[0])


def lines_by_position(words):
    lines = []

    ordered = sorted(
        words,
        key=lambda w: (w["top"], w["x0"])
    )

    for word in ordered:
        row = next(
            (
                r for r in reversed(lines[-5:])
                if abs(r[0] - word["top"]) <= 3
            ),
            None
        )

        if row is None:
            row = [word["top"], []]
            lines.append(row)

        row[1].append(word)

    return [
        sorted(row[1], key=lambda w: w["x0"])
        for row in sorted(lines, key=lambda r: r[0])
    ]


def normalize_name(raw):
    last, first = raw.rsplit(",", 1)

    first = first.strip()
    last = last.strip()

    if not first or not last:
        raise ValueError(
            "Gecersiz oyuncu adi: " + raw
        )

    return (
        f"{first} {last}"
        .replace(", Jr.", " Jr.")
        .replace(", Sr.", " Sr.")
    )


def parse_pdf(content):
    records = []
    missing = set()

    current_team = None
    current = None

    with pdfplumber.open(
        io.BytesIO(content)
    ) as pdf:

        print(
            "PDF sayfalari:",
            len(pdf.pages),
            flush=True
        )

        for page in pdf.pages:
            width = page.width

            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=3
            )

            for row in lines_by_position(words):

                def column(start, end):
                    selected = [
                        word["text"]
                        for word in row
                        if start <= word["x0"] < end
                    ]
                    return " ".join(selected).strip()

                # NBA PDF sutunlari
                team_text = column(
                    width * 0.31,
                    width * 0.50
                )

                player_text = column(
                    width * 0.50,
                    width * 0.69
                )

                status_text = column(
                    width * 0.69,
                    width * 0.79
                ).upper()

                reason_text = column(
                    width * 0.79,
                    width
                )

                normalized_team = re.sub(
                    r"[^A-Za-z0-9]",
                    "",
                    team_text
                ).upper()

                if normalized_team in TEAM_MAP:
                    current_team = TEAM_MAP[
                        normalized_team
                    ]
                    current = None

                if (
                    "NOT YET SUBMITTED"
                    in reason_text.upper()
                ):
                    if not current_team:
                        raise RuntimeError(
                            "Takim adi bulunamadi"
                        )

                    missing.add(current_team)
                    current = None
                    continue

                # Oyuncu ve durumu
                if (
                    "," in player_text
                    and status_text in STATUSES
                ):
                    if not current_team:
                        raise RuntimeError(
                            "Takimi bulunamayan oyuncu: "
                            + player_text
                        )

                    current = {
                        "player_name": normalize_name(
                            player_text
                        ),
                        "team": current_team,
                        "status": status_text,
                        "reason": reason_text
                    }

                    records.append(current)

                # Ayni oyuncunun aciklamasi
                # alt satirda devam edebilir
                elif (
                    reason_text
                    and current
                    and not player_text
                    and not status_text
                ):
                    current["reason"] = (
                        current["reason"]
                        + " "
                        + reason_text
                    ).strip()

    if not records:
        raise RuntimeError(
            "PDF icinde oyuncu bulunamadi"
        )

    seen = set()

    for player in records:
        key = (
            player["team"],
            player["player_name"]
        )

        if key in seen:
            raise RuntimeError(
                "Tekrarlanan oyuncu: "
                + str(key)
            )

        seen.add(key)

        player["reason"] = re.sub(
            r"\s+",
            " ",
            player["reason"]
        ).strip()[:500]

        if not player["reason"]:
            raise RuntimeError(
                "Bos sakatlik aciklamasi: "
                + player["player_name"]
            )

    return records, sorted(missing)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true"
    )

    args = parser.parse_args()

    print(
        "=== NBA OFFICIAL SYNC ===",
        flush=True
    )

    stamp, url = latest_report()

    print(
        "Secilen PDF:",
        url,
        flush=True
    )

    response = SESSION.get(
        url,
        timeout=45
    )

    print(
        "PDF HTTP:",
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    if not response.content.startswith(b"%PDF-"):
        raise RuntimeError(
            "PDF yerine baska veri geldi"
        )

    records, missing = parse_pdf(
        response.content
    )

    print(
        "Oyuncu sayisi:",
        len(records),
        flush=True
    )

    print(
        "Durumlar:",
        dict(
            Counter(
                p["status"]
                for p in records
            )
        ),
        flush=True
    )

    print(
        "Rapor gondermeyen takimlar:",
        len(missing),
        flush=True
    )

    print(
        "Ornek 10 oyuncu:",
        json.dumps(
            records[:10],
            ensure_ascii=False
        ),
        flush=True
    )

    print(
        "Tum oyuncular:",
        json.dumps(
            records,
            ensure_ascii=False
        ),
        flush=True
    )

    # Test modunda veritabani degismez
    if args.dry_run:
        print(
            "TEST TAMAMLANDI - "
            "VERITABANINA YAZILMADI",
            flush=True
        )
        return

    token = os.getenv("NBA_IMPORT_TOKEN")

    if not token:
        raise RuntimeError(
            "NBA_IMPORT_TOKEN tanimli degil"
        )

    worker = os.getenv(
        "WORKER_URL",
        "https://cizgi-masasi-api.k-melihsari.workers.dev"
    ).rstrip("/")

    if not worker.startswith("https://"):
        raise RuntimeError(
            "WORKER_URL HTTPS olmali"
        )

    payload = {
        "report_url": url,
        "report_key": stamp.strftime(
            "%Y-%m-%d_%H%M"
        ),
        "report_date": stamp.strftime(
            "%Y-%m-%d %H:%M ET"
        ),
        "players": records,
        "not_submitted_teams": missing
    }

    result = SESSION.post(
        worker + "/api/import-nba",
        json=payload,
        headers={
            "Authorization": "Bearer " + token
        },
        timeout=45
    )

    print(
        "D1 HTTP:",
        result.status_code,
        flush=True
    )

    print(
        "D1 yaniti:",
        result.text[:1000],
        flush=True
    )

    result.raise_for_status()

    data = result.json()

    if not data.get("success"):
        raise RuntimeError(
            "D1 aktarimi basarisiz"
        )

    if data.get("skipped"):
        print(
            "Ayni veya eski rapor; "
            "kayit atlandi",
            flush=True
        )

    elif data.get("stored") != len(records):
        raise RuntimeError(
            "D1 oyuncu sayisi uyusmuyor"
        )

    else:
        print(
            "NBA D1 AKTARIMI BASARILI",
            flush=True
        )


if __name__ == "__main__":
    main()
