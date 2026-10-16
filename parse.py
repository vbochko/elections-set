"""Stage 2: build a CSV of elected deputies from the council pages saved by gather.py.

One row per deputy. Rows come out grouped region -> council -> party: regions and
councils sorted by name, parties and deputies in the order the site lists them.
"""

import argparse
import csv
import logging
from pathlib import Path

from bs4 import BeautifulSoup

from gather import soup

FIELDS = ["region", "council", "tvo", "name", "info", "party", "votes", "votes_pct"]

log = logging.getLogger("parse")


def deputies(page: BeautifulSoup) -> list[dict]:
    """Rows of the "№ ТВО, за яким закріплено" table, each tagged with its party group row."""
    header = page.find("td", string="№ ТВО, за яким закріплено")
    if header is None:  # council with no elected deputies listed
        return []
    rows, party = [], None
    # Unclosed <tr> again: rows nest, so take each row's direct <td> children only.
    for tr in header.find_parent("table").find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 1 and tds[0].get("colspan"):
            party = tds[0].get_text(strip=True)
        elif len(tds) == 5 and tds[0] is not header:
            tvo, name, info, votes, pct = (td.get_text(" ", strip=True) for td in tds)
            # tvo is a district number or "Перший кандидат" (party list leader); kept as-is.
            rows.append(dict(tvo=tvo, name=name, info=info, party=party, votes=votes, votes_pct=pct.replace(",", ".")))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=Path("data/raw"), help="gathered HTML (default: data/raw)")
    ap.add_argument("--out", type=Path, default=Path("data/deputies.csv"), help="CSV path (default: data/deputies.csv)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    total = 0
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)  # QUOTE_MINIMAL: fields with commas/quotes (e.g. info) get quoted
        w.writeheader()
        for path in sorted(args.src.glob("*/*__*.html")):
            page = soup(path.read_bytes())
            region = path.parent.name
            # <p class=p2>Вінницька обл., Барська районна рада</p>
            council = page.find("p", class_="p2").get_text(strip=True).split(", ", 1)[-1]
            rows = deputies(page)
            if not rows:
                log.warning("no deputies: %s", path)
            for row in rows:
                w.writerow(dict(region=region, council=council, **row))
            total += len(rows)
    log.info("done: %d deputies -> %s", total, args.out)


if __name__ == "__main__":
    main()
