
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

PAGE = "https://official.nba.com/nba-injury-report-2026-27-season/"

PDF_RX = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_"
    r"(\d{1,2})_(\d{2})(AM|PM)\.pdf",
    re.I
)

TEAMS = [
    "AtlantaHawks", "BostonCeltics", "BrooklynNets",
    "CharlotteHornets", "ChicagoBulls", "ClevelandCavaliers",
    "DallasMavericks", "DenverNuggets", "DetroitPistons",
    "GoldenStateWarriors", "HoustonRockets", "IndianaPacers",
    "LAClippers", "LosAngelesLakers", "MemphisGrizzlies",
    "MiamiHeat", "MilwaukeeBucks", "MinnesotaTimberwolves",
    "NewOrleansPelicans", "NewYorkKnicks",
    "OklahomaCityThunder", "OrlandoMagic",
    "Philadelphia76ers", "PhoenixSuns",
    "PortlandTrailBlazers", "SacramentoKings",
    "SanAntonioSpurs", "TorontoRaptors", "UtahJazz",
    "WashingtonWizards"
]

TEAM_KEYS = {
    re.sub(r"[^A-Z0-9]", "", x.upper()): x
    for x in TEAMS
}

STATUSES = {
    "OUT", "QUESTIONABLE", "DOUBTFUL",
    "PROBABLE", "AVAILABLE"
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/pdf"
})


def latest_report():
    response = SESSION.get(PAGE, timeout=30)
    print("NBA sayfa HTTP:", response.status_code, flush=True)
    response.raise_for_status()

    reports = []

    soup = BeautifulSoup(
        response.text, "html.parser"
    )

    for a in soup.find_all("a", href=True):
        url = urljoin(PAGE, a["href"])
        parsed = urlparse(url)
        match = PDF_RX.search(parsed.path)

        if parsed.hostname != "ak-static.cms.nba.com":
            continue

        if not match:
            continue

        day, hour, minute, ampm = match.groups()

        stamp = datetime.strptime(
            f"{day} {hour}:{minute} {ampm}",
            "%Y-%m-%d %I:%M %p"
        )

        reports.append((stamp, url))

    if not reports:
        raise RuntimeError(
            "NBA resmi PDF bulunamadi"
        )

    print(
        "Bulunan PDF sayisi:",
        len(reports),
        flush=True
    )

    return max(reports, key=lambda pair: pair[0])


def clip_text(page, x0, y0, x1, y1):
    if y1 - y0 < 2:
        return ""

    crop = page.crop((
        x0, y0 + 0.3,
        x1, y1 - 0.3
    ))

    return re.sub(
        r"\s+",
        " ",
        crop.extract_text(
            x_tolerance=2,
            y_tolerance=3
        ) or ""
    ).strip()


def team_from_text(raw):
    key = re.sub(
        r"[^A-Z0-9]",
        "",
        raw.upper()
    )

    return TEAM_KEYS.get(key)


def normalize_name(value):
    parts = [
        x.strip()
        for x in value.split(",")
    ]

    if len(parts) < 2 or not parts[-1]:
        raise RuntimeError(
            "Oyuncu adi ayristirilamadi: " + value
        )

    first = parts[-1]
    last = " ".join(parts[:-1])

    return re.sub(
        r"\s+", " ",
        first + " " + last
    ).strip()


def parse_pdf(data):
    players = []
    not_submitted = set()
    active_team = None

    with pdfplumber.open(
        io.BytesIO(data)
    ) as pdf:

        print(
            "PDF sayfa sayisi:",
            len(pdf.pages),
            flush=True
        )

        for page_no, page in enumerate(
            pdf.pages, 1
        ):
            # Sutunlar PDF genisligine gore
            # otomatik olceklendirilir.
            scale = page.width / 841.95

            x_team = (
                260.2 * scale,
                421.0 * scale
            )

            x_player = (
                421.0 * scale,
                581.7 * scale
            )

            x_status = (
                581.7 * scale,
                662.1 * scale
            )

            x_reason = (
                662.1 * scale,
                822.8 * scale
            )

            ratio = page.height / page.width

            expected_ratio = 595.35 / 841.95

            if abs(
                ratio - expected_ratio
            ) > 0.025:
                raise RuntimeError(
                    f"Sayfa {page_no}: PDF duzeni degisti"
                )

            # Yatay sinirlarin oyuncu
            # sutunundaki parcasini bul.
            lines = sorted({
                round(edge["top"], 2)
                for edge in page.edges
                if (
                    edge.get("orientation") == "h"
                    and abs(
                        edge["x0"] - x_player[0]
                    ) < 2 * scale
                    and abs(
                        edge["x1"] - x_player[1]
                    ) < 2 * scale
                    and edge["top"] > 70 * scale
                    and edge["top"] <
                    page.height - 45 * scale
                )
            })

            print(
                f"Sayfa {page_no}: "
                f"oyuncu satiri siniri={len(lines)}",
                flush=True
            )

            if not lines:
                raise RuntimeError(
                    f"Sayfa {page_no}: "
                    "tablo sinirlari bulunamadi"
                )

            first_top = (
                115 * scale
                if page_no == 1
                else 76 * scale
            )

            bounds = [first_top] + [
                value
                for value in lines
                if value > first_top + 2
            ]

            last = (
                page.height - 65 * scale
            )

            if bounds[-1] < last - 5:
                bounds.append(last)

            for top, bottom in zip(
                bounds, bounds[1:]
            ):
                if bottom <= top:
                    continue

                team_raw = clip_text(
                    page,
                    x_team[0],
                    top,
                    x_team[1],
                    bottom
                )

                player_raw = clip_text(
                    page,
                    x_player[0],
                    top,
                    x_player[1],
                    bottom
                )

                status_raw = clip_text(
                    page,
                    x_status[0],
                    top,
                    x_status[1],
                    bottom
                ).upper()

                reason = clip_text(
                    page,
                    x_reason[0],
                    top,
                    x_reason[1],
                    bottom
                )

                team = team_from_text(
                    team_raw
                )

                if team:
                    active_team = team

                if (
                    "NOT YET SUBMITTED"
                    in reason.upper()
                ):
                    if not active_team:
                        raise RuntimeError(
                            "Takim adi bulunamadi"
                        )

                    not_submitted.add(
                        active_team
                    )
                    continue

                if status_raw in STATUSES:
                    if (
                        not player_raw
                        or "," not in player_raw
                    ):
                        raise RuntimeError(
                            "Oyuncu adi eksik: "
                            + status_raw
                        )

                    if not active_team:
                        raise RuntimeError(
                            "Oyuncunun takimi eksik"
                        )

                    players.append({
                        "player_name":
                            normalize_name(
                                player_raw
                            ),
                        "team": active_team,
                        "status": status_raw,
                        "reason": reason
                    })

                elif (
                    not player_raw
                    and not status_raw
                    and reason
                ):
                    # Onceki oyuncunun
                    # aciklamasinin devami.
                    if not players:
                        raise RuntimeError(
                            "Oyuncudan once "
                            "aciklama bulundu"
                        )

                    players[-1]["reason"] = (
                        players[-1]["reason"]
                        + " "
                        + reason
                    ).strip()

                elif (
                    player_raw
                    or status_raw
                ):
                    raise RuntimeError(
                        "Beklenmeyen hucre: "
                        + player_raw
                        + " / "
                        + status_raw
                    )

    if not players:
        raise RuntimeError(
            "Hic oyuncu bulunamadi"
        )

    seen = set()

    for player in players:
        key = (
            player["team"],
            player["player_name"]
        )

        if (
            key in seen
            or not player["reason"]
            or len(player["reason"]) > 500
        ):
            raise RuntimeError(
                "Supheli oyuncu: "
                + str(player)
            )

        seen.add(key)

    return players, sorted(not_submitted)


def validate_known_cases(players):
    index = {
        p["player_name"]: p
        for p in players
    }

    cases = [
        (
            "Bryce McGowens",
            "Left Elbow",
            "Left Knee"
        ),
        (
            "Yves Missi",
            "Left Knee",
            "Left Elbow"
        ),
        (
            "Ben Saraf",
            "On Assignment",
            "Right Calf"
        ),
        (
            "Nolan Traore",
            "Right Calf",
            "On Assignment"
        )
    ]

    for name, expected, forbidden in cases:
        if name not in index:
            continue

        reason = index[name]["reason"]

        if (
            expected.lower()
            not in reason.lower()
            or forbidden.lower()
            in reason.lower()
        ):
            raise RuntimeError(
                "Aciklama karismasi: "
                + name
                + ": "
                + reason
            )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true"
    )

    args = parser.parse_args()

    print(
        "=== CIZGI MASASI NBA READER V5 ===",
        flush=True
    )

    stamp, pdf_url = latest_report()

    print(
        "PDF:",
        pdf_url,
        flush=True
    )

    response = SESSION.get(
        pdf_url,
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
            "PDF dosyasi alinamadi"
        )

    players, missing = parse_pdf(
        response.content
    )

    validate_known_cases(players)

    print(
        "Oyuncular:",
        len(players),
        flush=True
    )

    print(
        "Durumlar:",
        dict(Counter(
            p["status"]
            for p in players
        )),
        flush=True
    )

    print(
        "Rapor gondermeyen takimlar:",
        len(missing),
        flush=True
    )

    names = [
        "Bryce McGowens",
        "Yves Missi",
        "Ben Saraf",
        "Nolan Traore",
        "Jarrett Allen"
    ]

    for name in names:
        player = next(
            (
                p for p in players
                if p["player_name"] == name
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

    if args.dry_run:
        print(
            "TEST TAMAMLANDI - "
            "VERITABANINA YAZILMADI",
            flush=True
        )
        return

    token = os.getenv(
        "NBA_IMPORT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "NBA_IMPORT_TOKEN eksik"
        )

    worker = os.getenv(
        "WORKER_URL",
        "https://cizgi-masasi-api.k-melihsari.workers.dev"
    ).rstrip("/")

    if not worker.startswith(
        "https://"
    ):
        raise RuntimeError(
            "Worker HTTPS olmali"
        )

    payload = {
        "report_url": pdf_url,
        "report_key": stamp.strftime(
            "%Y-%m-%d_%H%M"
        ),
        "report_date": stamp.strftime(
            "%Y-%m-%d %H:%M ET"
        ),
        "players": players,
        "not_submitted_teams": missing
    }

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

    output = result.json()

    if not output.get("success"):
        raise RuntimeError(
            "D1 aktarimi basarisiz"
        )

    if (
        not output.get("skipped")
        and output.get("stored")
        != len(players)
    ):
        raise RuntimeError(
            "D1 oyuncu sayisi farkli"
        )

    print(
        "NBA D1 AKTARIMI BASARILI",
        flush=True
    )


if __name__ == "__main__":
    main()
