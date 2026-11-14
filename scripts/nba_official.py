
import argparse
import io
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup


# CIZGI MASASI - NBA PDF V4 TESHIS
# Bu surum SADECE TEST yapar.
# Cloudflare D1'e veri gondermez.

PAGE = (
    "https://official.nba.com/"
    "nba-injury-report-2026-27-season/"
)

PDF_RX = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_"
    r"(\d{1,2})_(\d{2})(AM|PM)\.pdf",
    re.I
)

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/pdf"
})


def latest_report():
    print(
        "NBA resmi sayfasi kontrol ediliyor...",
        flush=True
    )

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

    for link in soup.find_all(
        "a",
        href=True
    ):
        url = urljoin(
            PAGE,
            link["href"]
        )

        parsed = urlparse(url)
        match = PDF_RX.search(parsed.path)

        if not match:
            continue

        if (
            parsed.hostname
            != "ak-static.cms.nba.com"
        ):
            continue

        day, hour, minute, ampm = (
            match.groups()
        )

        try:
            stamp = datetime.strptime(
                f"{day} {hour}:{minute} {ampm}",
                "%Y-%m-%d %I:%M %p"
            )
        except ValueError:
            continue

        reports.append(
            (stamp, url)
        )

    if not reports:
        raise RuntimeError(
            "Resmi NBA PDF bulunamadi"
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


def group_words(words, tolerance=3):
    rows = []

    words = sorted(
        words,
        key=lambda w: (
            w["top"],
            w["x0"]
        )
    )

    for word in words:
        found = None

        for row in reversed(rows[-8:]):
            if (
                abs(
                    row["top"] - word["top"]
                ) <= tolerance
            ):
                found = row
                break

        if found is None:
            found = {
                "top": word["top"],
                "words": []
            }
            rows.append(found)

        found["words"].append(word)

    rows.sort(
        key=lambda row: row["top"]
    )

    return rows


def inspect_page(page, page_number):
    width = page.width
    height = page.height

    print(
        "\n===== SAYFA",
        page_number,
        "=====",
        flush=True
    )

    print(
        "Boyut:",
        width,
        "x",
        height,
        flush=True
    )

    print(
        "PDF nesneleri:",
        "edges =", len(page.edges),
        "lines =", len(page.lines),
        "rects =", len(page.rects),
        flush=True
    )

    horizontal = []

    for edge in page.edges:
        if edge.get("orientation") == "h":
            horizontal.append(edge)

    print(
        "Yatay cizgi sayisi:",
        len(horizontal),
        flush=True
    )

    for edge in horizontal[:10]:
        print(
            "CIZGI:",
            "x0 =", round(edge["x0"], 1),
            "x1 =", round(edge["x1"], 1),
            "y =", round(edge["top"], 1),
            flush=True
        )

    words = page.extract_words(
        x_tolerance=2,
        y_tolerance=3
    )

    print(
        "Kelime sayisi:",
        len(words),
        flush=True
    )

    rows = group_words(words)

    print(
        "Algilanan metin satiri:",
        len(rows),
        flush=True
    )

    # Ilk iki sayfayi daha ayrintili incele.
    max_rows = (
        45 if page_number <= 2 else 12
    )

    for row in rows[:max_rows]:
        ordered = sorted(
            row["words"],
            key=lambda w: w["x0"]
        )

        content = " ".join(
            w["text"]
            for w in ordered
        )

        x_start = min(
            w["x0"]
            for w in ordered
        )

        x_end = max(
            w["x1"]
            for w in ordered
        )

        print(
            "SATIR:",
            "Y =", round(row["top"], 1),
            "X =", round(x_start, 1),
            "-",
            round(x_end, 1),
            "|",
            content[:220],
            flush=True
        )

    if page_number == 1:
        print(
            "\nSUTUN KONUM TESTI",
            flush=True
        )

        for word in words:
            text = word["text"]

            if (
                "," in text
                or text.upper() in (
                    "OUT",
                    "QUESTIONABLE",
                    "PROBABLE",
                    "DOUBTFUL",
                    "AVAILABLE"
                )
            ):
                print(
                    "ALAN:",
                    "x =", round(
                        word["x0"], 1
                    ),
                    "y =", round(
                        word["top"], 1
                    ),
                    "deger =", text,
                    flush=True
                )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true"
    )

    parser.parse_args()

    print(
        "=== CIZGI MASASI NBA V4 TESHIS ===",
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

    if not response.content.startswith(
        b"%PDF-"
    ):
        raise RuntimeError(
            "Indirilen icerik PDF degil"
        )

    with pdfplumber.open(
        io.BytesIO(response.content)
    ) as pdf:

        print(
            "PDF toplam sayfa:",
            len(pdf.pages),
            flush=True
        )

        for index, page in enumerate(
            pdf.pages,
            start=1
        ):
            inspect_page(
                page,
                index
            )

    print(
        "\n=== V4 TESHIS TAMAMLANDI ===",
        flush=True
    )

    print(
        "TEST MODU: VERITABANINA YAZILMADI",
        flush=True
    )


if __name__ == "__main__":
    main()
