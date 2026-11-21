"""Build the Serie B prototype from the original FootyLogos ZIP using Python 3."""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

# Slug, club name, city, abbreviation. Colours are simplified for the prototype.
CLUBS = """
america-mineiro|América-MG|Belo Horizonte|AME|16683d
athletic|Athletic Club|São João del-Rei|ATH|202020
atletico-goianiense|Atlético-GO|Goiânia|ACG|cf1829
avai-fc|Avaí|Florianópolis|AVA|1758a6
botafogo-sp|Botafogo-SP|Ribeirão Preto|BOT|bd2230
ceara-sc|Ceará|Fortaleza|CEA|202020
crb|CRB|Maceió|CRB|bf1925
criciuma|Criciúma|Criciúma|CRI|edbb24
cuiaba|Cuiabá|Cuiabá|CUI|176c48
fortaleza|Fortaleza|Fortaleza|FOR|194890
goias|Goiás|Goiânia|GOI|007b49
gremio-novorizontino|Novorizontino|Novo Horizonte|NOV|deb11f
juventude|Juventude|Caxias do Sul|JUV|187947
operario-ferroviario|Operário-PR|Ponta Grossa|OPE|202020
sport-recife|Sport|Recife|SPO|be192a
vila-nova|Vila Nova|Goiânia|VIL|ca2432
londrina|Londrina|Londrina|LON|5598c8
ponte-preta|Ponte Preta|Campinas|PON|202020
nautico|Náutico|Recife|NAU|c52738
sao-bernardo|São Bernardo|São Bernardo do Campo|SBE|e1b724
""".strip().splitlines()


def build(source, destination):
    files, teams, cards = {}, [], []
    with ZipFile(source) as archive:
        index = {item["slug"]: item for item in json.loads(archive.read("included-logos.json"))}
        for line in CLUBS:
            slug, name, city, short, color = line.split("|")
            record = index[slug]
            data = archive.read(record["filename"])
            if hashlib.sha256(data).hexdigest() != record["sha256"] or not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"Invalid crest: {slug}")
            logo = f"assets/logos/{slug}.png"
            files[logo] = data
            teams.append(dict(id=slug, name=name, shortName=short, city=city, country="BR",
                              logo=logo, colors=dict(primary="#"+color, secondary="#ffffff")))
            uri = base64.b64encode(data).decode("ascii")
            cards.append(f'<article><img alt="" src="data:image/png;base64,{uri}"><b>{html.escape(name)}</b><small>{html.escape(city)}</small></article>')
    league = "br-serie-b"
    documents = {
        "package.json": dict(schema="world", id="br-serie-b-demo", name="Brasileirão Série B 2026",
            description="Protótipo com 20 clubes. Escudos: https://www.footylogos.com/",
            version="0.1.0", formatVersion=1, gameMinVersion="0.3.0", baseYear=2026,
            packageType="database", defaultActiveRegions=[], defaultActiveCompetitions=[league]),
        "teams/teams.json": dict(schema="team",items=teams),
        "competitions/serie-b.json": dict(schema="competition", id=league, name="Brasileirão Série B",
            type="League", scope="Domestic", countryId="BR", priority=1,
            format=dict(kind="LeagueTable",legs=2), participants=dict(explicit=[t["id"] for t in teams]),
            seasonStartMonth=4, seasonStartDay=1),
    }
    destination.mkdir(parents=True, exist_ok=True)
    package = destination / "Serie-B-2026.ofm"
    with ZipFile(package, "w", ZIP_DEFLATED) as out:
        for path, doc in documents.items():
            out.writestr(path, json.dumps(doc,ensure_ascii=False).encode())
        for path, data in files.items():
            out.writestr(path,data)
    with ZipFile(package) as check:
        assert check.testzip() is None
        for team in json.loads(check.read("teams/teams.json"))["items"]:
            assert check.read(team["logo"]) == files[team["logo"]]
    page = """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Série B 2026</title><style>
    *{box-sizing:border-box}body{margin:0;background:#10271f;color:white;font:16px system-ui}main{max-width:1080px;margin:auto;padding:32px 20px}h1{font-size:clamp(30px,5vw,56px);margin:0}section{margin:24px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px}article{background:#f6f4ea;color:#152d22;border-radius:10px;padding:16px;display:grid;gap:5px}img{width:78px;height:78px;object-fit:contain;margin-bottom:8px}small{color:#46564c}a{color:#c7eb95}</style><main><h1>Brasileirão Série B</h1><p>2026 · 20 clubes</p><section>"""
    (destination/"Serie-B-2026.html").write_text(page+"".join(cards)+'</section>Escudos de <a href="https://www.footylogos.com/">FootyLogos</a></main></html>',encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip",type=Path)
    parser.add_argument("--output",type=Path,default=Path("serie-b-demo"))
    args = parser.parse_args()
    build(args.zip,args.output)
