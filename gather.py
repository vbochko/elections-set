"""Stage 1: download raw HTML pages from the CVK 2015 local elections site.

Crawl: index table -> "Районні" column (one link per region)
       -> region page -> "Найменування ради" column (one link per council)
       -> council page, saved as <out>/<region>/<council>__<id>.html

Pages are saved as raw bytes (windows-1251) and reused on rerun, so an
interrupted crawl resumes without hitting the server again.
"""

import argparse
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

INDEX_URL = "https://www.cvk.gov.ua/pls/vm2015/pvm002pt001f01=100pt00_t001f01=100.html"
ENCODING = "windows-1251"

log = logging.getLogger("gather")


class Fetcher:
    """Sequential HTTP client: at most one request per `delay` seconds, retries with backoff."""

    def __init__(self, delay: float):
        self.delay = delay
        self.last = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "elections-set research crawler (python-requests)"
        retry = Retry(total=5, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get(self, url: str) -> bytes:
        wait = self.last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()
        log.info("GET %s", url)
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.content

    def cached(self, url: str, path: Path) -> bytes:
        """Return the page from disk if already saved, else download and save it."""
        if path.exists():
            return path.read_bytes()
        content = self.get(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return content


def soup(content: bytes) -> BeautifulSoup:
    return BeautifulSoup(content, "html.parser", from_encoding=ENCODING)


def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', " ", name).strip()


def region_links(page: BeautifulSoup, column: str = "Районні") -> list[tuple[str, str]]:
    """(region name, href) for every region row that has a link in `column`."""
    header = page.find("td", string=column)
    # Each header group spans two sub-columns: "Обирається", "Обрано"; the link sits in "Обрано".
    col = sum(int(td.get("colspan", 1)) for td in header.find_previous_siblings("td")) + 1
    links = []
    # The site leaves <tr> unclosed, so html.parser nests rows; direct <td> children are still one row.
    for tr in header.find_parent("table").find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) > col and (a := tds[col].find("a", href=True)):
            links.append((tds[0].get_text(strip=True), a["href"]))
    return links


def council_links(page: BeautifulSoup) -> list[tuple[str, str]]:
    """(council name, href) for every row of the "Найменування ради" table."""
    table = page.find("td", string="Найменування ради").find_parent("table")
    return [(a.get_text(strip=True), a["href"]) for a in table.find_all("a", href=True)]


def council_id(href: str) -> str:
    # pid102 is the council's id on the site; council names repeat across regions.
    m = re.search(r"pid102=(\d+)", href)
    return m.group(1) if m else safe_name(href)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("data/raw"), help="destination folder (default: data/raw)")
    ap.add_argument("--delay", type=float, default=1.0, help="min seconds between requests (default: 1.0)")
    ap.add_argument("--region", action="append", help="only regions whose name contains this text (repeatable)")
    ap.add_argument("--limit", type=int, help="only the first N regions")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    f = Fetcher(args.delay)
    regions = region_links(soup(f.cached(INDEX_URL, args.out / "index.html")))
    if args.region:
        regions = [r for r in regions if any(q.lower() in r[0].lower() for q in args.region)]
    regions = regions[: args.limit]
    log.info("%d regions selected", len(regions))

    saved = 0
    for region, href in regions:
        region_dir = args.out / safe_name(region)
        councils = council_links(soup(f.cached(urljoin(INDEX_URL, href), region_dir / "_councils.html")))
        log.info("%s: %d councils", region, len(councils))
        for name, href in councils:
            f.cached(urljoin(INDEX_URL, href), region_dir / f"{safe_name(name)}__{council_id(href)}.html")
            saved += 1
    log.info("done: %d council pages in %s", saved, args.out)


if __name__ == "__main__":
    main()
