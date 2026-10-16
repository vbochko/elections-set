# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goal

Python scraper building a dataset of the 2015 Ukrainian local elections from the Central Election Commission (ЦВК) site:
https://www.cvk.gov.ua/pls/vm2015/pvm002pt001f01=100pt00_t001f01=100.html

`SPEC.md` is the source of truth for requirements. Two stages, kept separate:

1. **Gather** (`gather.py`, done) — crawl and save raw HTML to `data/raw/`.
2. **Parse** (`parse.py`) — reads only the saved HTML, writes `data/deputies.csv` (one row per elected deputy). Must not hit the network.

## Commands

```bash
uv sync
uv run python gather.py --region Вінницька   # test on one region before any full run
uv run python gather.py --delay 1.0          # full crawl, ~500 requests
uv run python parse.py                       # data/raw -> data/deputies.csv
uv run python test_gather.py                 # offline assert-based check, no pytest
```

## Site facts (from discovery)

- Pages are `windows-1251`; the HTTP header has no charset (only `<meta>`), so never use `requests`' `r.text`. Decode explicitly. Files are stored as raw bytes.
- Markup leaves `<tr>` unclosed; with `html.parser` rows nest, but each `tr`'s direct `<td>` children are still exactly that row. `region_links` relies on this.
- Index table: header groups span 2 columns (Обирається / Обрано). The link is in "Обрано". "Районні" links carry `pid112=21`, and `pid100` is the region id.
- Region page → `pvm057...pid102=<council id>...` links. Council names repeat across regions, so filenames use `<name>__<pid102>.html`.
- Council pages are self-contained (party votes, mandates, elected deputies), with no further links to follow.
- Deputy table: found by its header cell `№ ТВО, за яким закріплено`. Party groups are single `colspan=5` rows, and deputy rows have 5 cells. `Перший кандидат` (list leader) rows have empty votes/%.
- Validate parser changes by comparing the row count per page with the page's own "Кількість обраних депутатів місцевої ради". Two Луганська councils show "Призначені повторні вибори" instead of a number and have no table.

## Crawling etiquette

Real government server: keep requests sequential and rate-limited (`Fetcher`, default 1 req/s). Existing files are reused (`Fetcher.cached`), so reruns cost zero requests.
