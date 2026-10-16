"""Offline check of link extraction and deputy parsing. Run: uv run python test_gather.py"""

from bs4 import BeautifulSoup

from gather import council_id, council_links, region_links, safe_name
from parse import deputies

# Same shape as the CVK index: unclosed <tr>, two-row header with colspan groups.
INDEX = """<table>
<tr><td rowspan=2>Назва регіону</td><td colspan=2>Обласні ради</td><td colspan=2>Районні</td>
<td colspan=2>Районні у містах</td>
<tr><td>Обирається</td><td>Обрано</td><td>Обирається</td><td>Обрано</td><td>Обирається</td><td>Обрано</td></tr>
<tr><td>A область</td><td>1</td><td><a href="obl-a">1</a></td><td>2</td><td><a href="rai-a">2</a></td>
<td>3</td><td><a href="mis-a">3</a></td>
<tr><td>м.Київ</td><td></td><td></td><td></td><td></td><td></td><td></td>
<tr><td>B область</td><td>1</td><td><a href="obl-b">1</a></td><td>2</td><td><a href="rai-b">2</a></td>
<td></td><td></td>
</table>"""

REGION = """<table><tr><td>Найменування ради</td><td>К-сть</td>
<tr><td><a href="pvm057pid112=21pid102=6468pf7691=6468.html">Барська районна рада</a></td><td>34</td>
</table>"""

COUNCIL = """<table><tr><td>№ ТВО, за яким закріплено</td><td>ПІБ</td><td>Відомості</td><td>Голосів</td><td>%</td>
<tr><td colspan=5><a name="65"></a><b>Партія А</b></td></tr>
<tr><td>21</td><td>Дмитрик Алла</td><td>Громадянка України, освіта вища</td><td>143</td><td>  57,8947</td>
<tr><td colspan=5><b>Партія Б</b></td></tr>
<tr><td>Перший кандидат</td><td>Піддубний Михайло</td><td>Громадянин України</td><td></td><td></td>
</table>"""

if __name__ == "__main__":
    assert region_links(BeautifulSoup(INDEX, "html.parser")) == [("A область", "rai-a"), ("B область", "rai-b")]
    councils = council_links(BeautifulSoup(REGION, "html.parser"))
    assert councils == [("Барська районна рада", "pvm057pid112=21pid102=6468pf7691=6468.html")]
    assert council_id(councils[0][1]) == "6468"
    assert safe_name('м. "Київ"/x') == "м. Київ x"
    assert deputies(BeautifulSoup(COUNCIL, "html.parser")) == [
        dict(tvo="21", name="Дмитрик Алла", info="Громадянка України, освіта вища", party="Партія А", votes="143", votes_pct="57.8947"),
        dict(tvo="Перший кандидат", name="Піддубний Михайло", info="Громадянин України", party="Партія Б", votes="", votes_pct=""),
    ]
    print("ok")
