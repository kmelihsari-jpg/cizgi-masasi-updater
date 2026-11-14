
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


# CIZGI MASASI - NBA OFFICIAL READER V3

PAGE = (
    "https://official.nba.com/"
    "nba-injury-report-2026-27-season/"
)

PDF_RX = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_"
    r"(\d{1,2})_(\d{2})(AM|PM)\.pdf",
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

TEAM_BY_KEY = {
    re.sub(r"\W", "", team).upper(): team
    for team in TEAMS
}

STATUSES = {
    "OUT",
    "QUESTIONABLE",
    "DOUBTFUL",
    "PROBABLE",
    "AVAILABLE"
}

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/pdf"
})


def latest_report():
    response = SESSION.get(
        PAGE,
        timeout=30
    )

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

    for link in soup.find_all("a", href=True):
        url = urljoin(
            PAGE,
            link["href"]
        )

        parsed = urlparse(url)

        match = PDF_RX.search(
            parsed.path
        )

        if not match:
            continue

        if (
            parsed.hostname
            != "ak-static.cms.nba.com"
        ):
            continue

        day, hour, minute, meridian = (
            match.groups()
        )

        stamp = datetime.strptime(
            f"{day} {hour}:{minute} {meridian}",
            "%Y-%m-%d %I:%M %p"
        )

        reports.append(
            (stamp, url)
        )

    if not reports:
        raise RuntimeError(
            "NBA sayfasinda PDF bulunamadi"
        )

    print(
        "Bulunan PDF sayisi:",
        len(reports),
        flush=True
    )

    return max(
        reports,
        key=lambda item: item[0]
    )


def extract_column(
    page,
    left,
    top,
    right,
    bottom
):
    if bottom <= top + 1:
        return ""

    cropped = page.crop((
        left,
        top + 0.5,
        right,
        bottom - 0.5
    ))

    text = cropped.extract_text(
        x_tolerance=2,
        y_tolerance=3
    )

    return (text or "").strip()


def normalize_name(raw):
    last, first = raw.rsplit(
        ",", 1
    )

    first = first.strip()
    last = last.strip()

    last = re.sub(
        r"(Jr\.|Jr|Sr\.|Sr|II|III|IV)$",
        r" \1",
        last
    )

    return re.sub(
        r"\s+",
        " ",
        f"{first} {last}"
    ).strip()


def parse_pdf(raw):
    records = []
    not_submitted = set()

    current_team = None

    with pdfplumber.open(
        io.BytesIO(raw)
    ) as pdf:

        print(
            "PDF sayfalari:",
            len(pdf.pages),
            flush=True
        )

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):
            width = page.width
            height = page.height

            # Yatay cizgileri bul.
            rules = sorted({
                round(edge["top"], 1)
                for edge in page.edges
                if (
                    edge.get("orientation")
                    == "h"
                )
                and edge["x0"] <= width * 0.53
                and edge["x1"] >= width * 0.95
                and height * 0.13
                    < edge["top"]
                    < height * 0.96
            })

            if len(rules) < 2:
                raise RuntimeError(
                    f"Sayfa {page_number}: "
                    "satir cizgileri bulunamadi"
                )

            boundaries = [
                height * 0.13
            ] + rules

            for top, bottom in zip(
                boundaries,
                boundaries[1:]
            ):
                # Sutunlari ayri ayri oku.
                team_text = extract_column(
                    page,
                    width * 0.30,
                    top,
                    width * 0.50,
                    bottom
                )

                player_text = extract_column(
                    page,
                    width * 0.50,
                    top,
                    width * 0.69,
                    bottom
                )

                status_text = extract_column(
                    page,
                    width * 0.69,
                    top,
                    width * 0.79,
                    bottom
                ).upper()

                reason_text = extract_column(
                    page,
                    width * 0.79,
                    top,
                    width * 0.995,
                    bottom
                )

                # Takimi tespit et.
                for line in team_text.splitlines():
                    key = re.sub(
                        r"[^A-Za-z0-9]",
                        "",
                        line
                    ).upper()

                    if key in TEAM_BY_KEY:
                        current_team = (
                            TEAM_BY_KEY[key]
                        )

                # Basliklari temizle.
                player_text = re.sub(
                    r"^Player Name\s*",
                    "",
                    player_text,
                    flags=re.I
                ).strip()

                status_text = re.sub(
                    r"^CURRENT STATUS\s*",
                    "",
                    status_text
                ).strip()

                reason_text = re.sub(
                    r"^Reason\s*",
                    "",
                    reason_text,
                    flags=re.I
                ).strip()

                if (
                    "NOT YET SUBMITTED"
                    in reason_text.upper()
                ):
                    if current_team:
                        not_submitted.add(
                            current_team
                        )
                    continue

                player_lines = [
                    line.strip()
                    for line in (
                        player_text.splitlines()
                    )
                    if "," in line
                ]

                status_lines = [
                    line.strip()
                    for line in (
                        status_text.splitlines()
                    )
                    if line.strip() in STATUSES
                ]

                if (
                    player_lines
                    and status_lines
                ):
                    if not current_team:
                        raise RuntimeError(
                            "Takimsiz oyuncu: "
                            + str(player_lines)
                        )

                    if (
                        len(player_lines) != 1
                        or len(status_lines) != 1
                    ):
                        raise RuntimeError(
                            "Bir satirda birden fazla "
                            "oyuncu bulundu"
                        )

                    records.append({
                        "player_name":
                            normalize_name(
                                player_lines[0]
                            ),
                        "team":
                            current_team,
                        "status":
                            status_lines[0],
                        "reason":
                            re.sub(
                                r"\s+",
                                " ",
                                reason_text
                            ).strip()
                    })

                elif (
                    reason_text
                    and records
                    and not player_lines
                    and not status_lines
                ):
                    # Devam eden aciklama.
                    records[-1]["reason"] = (
                        records[-1]["reason"]
                        + " "
                        + reason_text
                    ).strip()

    if len(records) < 20:
        raise RuntimeError(
            "Supheli oyuncu sayisi: "
            + str(len(records))
        )

    seen = set()

    for record in records:
        key = (
            record["team"],
            record["player_name"]
        )

        if key in seen:
            raise RuntimeError(
                "Tekrarlanan oyuncu: "
                + str(key)
            )

        if not record["reason"]:
            raise RuntimeError(
                "Bos sakatlik aciklamasi: "
                + record["player_name"]
            )

        if len(record["reason"]) > 500:
            raise RuntimeError(
                "Cok uzun aciklama: "
                + record["player_name"]
            )

        seen.add(key)

    return (
        records,
        sorted(not_submitted)
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true"
    )

    args = parser.parse_args()

    print(
        "=== CIZGI MASASI NBA READER V3 ===",
        flush=True
    )

    # En yeni NBA PDF'ini bul.
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

    if not response.content.startswith(
        b"%PDF-"
    ):
        raise RuntimeError(
            "Indirilen dosya PDF degil"
        )

    # PDF'den oyunculari ayristir.
    records, missing = parse_pdf(
        response.content
    )

    print(
        "Oyuncular:",
        len(records),
        flush=True
    )

    print(
        "Durumlar:",
        dict(Counter(
            player["status"]
            for player in records
        )),
        flush=True
    )

    print(
        "Rapor gondermeyen takimlar:",
        len(missing),
        flush=True
    )

    # Onceden hatali okunan oyuncular.
    check_names = [
        "Bryce McGowens",
        "Yves Missi",
        "Ben Saraf",
        "Nolan Traore",
        "Jarrett Allen"
    ]

    for name in check_names:
        player = next(
            (
                record
                for record in records
                if (
                    record["player_name"]
                    == name
                )
            ),
            None
        )

        print(
            "KONTROL:",
            json.dumps(
                player,
                ensure_ascii=False
            ),
            flush=True
        )

    # Test modunda D1'e veri yazma.
    if args.dry_run:
        print(
            "TEST TAMAMLANDI - "
            "VERITABANINA YAZILMADI",
            flush=True
        )
        return

    # Canli aktarim icin gizli anahtar.
    token = os.getenv(
        "NBA_IMPORT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "NBA_IMPORT_TOKEN bulunamadi"
        )

    worker = os.getenv(
        "WORKER_URL",
        "https://cizgi-masasi-api.k-melihsari.workers.dev"
    ).rstrip("/")

    if not worker.startswith(
        "https://"
    ):
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

    print(
        "Cloudflare D1 aktarimi basliyor...",
        flush=True
    )

    result = SESSION.post(
        worker + "/api/import-nba",
        json=payload,
        headers={
            "Authorization": (
                "Bearer " + token
            )
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
            "Ayni veya eski rapor atlandi",
            flush=True
        )

    elif (
        data.get("stored")
        != len(records)
    ):
        raise RuntimeError(
            "Kayit sayisi uyusmuyor"
        )

    else:
        print(
            "NBA D1 AKTARIMI BASARILI",
            flush=True
        )


if __name__ == "__main__":
    main()
