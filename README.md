# about

this repo is for collecting dataset from 2015 elections

from commission website
https://www.cvk.gov.ua/pls/vm2015/pvm002pt001f01=100pt00_t001f01=100.html

## stage 1: gather html

Requires [uv](https://docs.astral.sh/uv/) (Python >= 3.10).

```bash
uv sync                                         # install dependencies

uv run python gather.py --region Вінницька      # one region first (~30 requests)
uv run python gather.py                         # all 24 regions (~500 requests, ~9 min at 1 req/s)
```

Options:

| flag | default | meaning |
|---|---|---|
| `--delay SEC` | `1.0` | minimum seconds between requests (rate limit) |
| `--region TEXT` | all | only regions whose name contains TEXT; repeatable |
| `--limit N` | all | only the first N regions |
| `--out DIR` | `data/raw` | destination folder |

Requests run one at a time. Responses 429 and 5xx are retried with exponential backoff.

Output:

```
data/raw/
  index.html                                  # start page (table of regions)
  Вінницька область/
    _councils.html                            # list of district councils in the region
    Барська районна рада__6468.html           # council page: <Найменування ради>__<site id>
    ...
```

Pages are saved as-is, in their original `windows-1251` encoding. Files that already exist are not downloaded again, so an interrupted run resumes where it stopped. To re-download a page, delete its file.

## stage 2: parse to csv

```bash
uv run python parse.py          # data/raw -> data/deputies.csv (offline, ~3 s)
```

Options: `--src DIR` (default `data/raw`), `--out FILE` (default `data/deputies.csv`).

One row per elected deputy, UTF-8, comma-separated. Fields that contain commas or quotes (always `info`, often `party`) are wrapped in double quotes:

| column | source on the council page |
|---|---|
| `region` | region folder name, e.g. `Вінницька область` |
| `council` | council name from the page header |
| `tvo` | № ТВО, за яким закріплено (`Перший кандидат` = party list leader) |
| `name` | Прізвище, ім'я, по батькові |
| `info` | Відомості про обраного депутата |
| `party` | party group row above the deputies |
| `votes` | Голосів ЗА у ТВО (empty for `Перший кандидат`) |
| `votes_pct` | % in the district, decimal point (empty for `Перший кандидат`) |

Rows are grouped region → council → party. Regions and councils are sorted by name. Parties and deputies keep the site's order.
Councils where repeat elections were called (2 in Луганська область) have no deputies and are logged as warnings.

## checks

Offline check of the link extraction and deputy parsing: `uv run python test_gather.py`
