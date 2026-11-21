"""Convert one season's clubs.csv and players.csv into a validated OFM package.

Usage: python scripts/import_world_db.py clubs.csv players.csv --year 2026
Requires ofm-cli on PATH. Output must be a new directory.
Transfermarkt domestic_competition_id or league_id identifies the division.
Optional clubs.csv column continental_cup accepts UCL, LIB or ACL for qualifiers.
For an unmapped league supply country (OFM code), league_name and tier (1-based).
"""
import argparse
import csv
import json
import re
import subprocess
import tempfile
from pathlib import Path

LEAGUES = {
    "BRA1": ("BR", "Brasileirão Série A", 1), "BRA2": ("BR", "Brasileirão Série B", 2),
    "GB1": ("ENG", "Premier League", 1), "ES1": ("ES", "La Liga", 1),
    "L1": ("DE", "Bundesliga", 1), "IT1": ("IT", "Serie A", 1),
    "FR1": ("FR", "Ligue 1", 1), "SG1": ("SG", "Singapore Premier League", 1),
}
CUPS = {"UCL": ("europe", "UEFA Champions League"),
        "LIB": ("south-america", "Copa Libertadores"), "ACL": ("asia", "AFC Champions League")}
POSITIONS = dict(zip("GK CB LB RB LWB RWB CDM CM CAM LM RM LW RW ST CF".split(),
                     "Goalkeeper CenterBack LeftBack RightBack LeftWingBack RightWingBack DefensiveMidfielder CentralMidfielder AttackingMidfielder LeftMidfielder RightMidfielder LeftWinger RightWinger Striker Striker".split()))
TM_POSITIONS = {"centre-back":"CB", "left-back":"LB", "right-back":"RB", "goalkeeper":"GK",
                "defensive midfield":"CDM", "central midfield":"CM", "attacking midfield":"CAM",
                "left midfield":"LM", "right midfield":"RM", "left winger":"LW",
                "right winger":"RW", "centre-forward":"ST", "second striker":"CF"}


def pick(row, *keys, default=None):
    for key in keys:
        if row.get(key):
            return row[key].strip()
    if default is None:
        raise ValueError(f"missing {' or '.join(keys)}")
    return default


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        for line, row in enumerate(csv.DictReader(source), 2):
            try:
                yield row
            except ValueError as exc:
                raise ValueError(f"{path}:{line}: {exc}") from exc


def identifier(value):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        raise ValueError(f"invalid identifier {value!r}")
    return value.lower()


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate(args, root):
    teams, leagues, cups = {}, {}, {}
    for row in rows(args.clubs):
        key = "club-" + identifier(pick(row, "club_id", "team_id"))
        if key in teams:
            raise ValueError(f"duplicate {key}")
        league = pick(row, "domestic_competition_id", "league_id")
        info = LEAGUES.get(league)
        if info is None:
            info = (pick(row, "country"), pick(row, "league_name"), int(pick(row, "tier")))
        country, name, tier = info
        lid = "league-" + identifier(league)
        comp = leagues.setdefault(lid, dict(schema="competition", id=lid, name=name,
            type="League", scope="Domestic", countryId=country, priority=tier-1,
            format={"kind":"LeagueTable","legs":2}, participants={"explicit":[]}))
        if (comp["name"], comp["countryId"], comp["priority"]) != (name, country, tier-1):
            raise ValueError(f"inconsistent metadata for {league}")
        comp["participants"]["explicit"].append(key)
        teams[key] = dict(id=key, name=pick(row,"name","club_name","team_name"), country=country,
            city=pick(row,"city",default=""), colors={"primary":pick(row,"primary_color",default="#34495e"),
            "secondary":pick(row,"secondary_color",default="#ffffff")})
        cup = pick(row,"continental_cup",default="")
        if cup:
            if cup not in CUPS:
                raise ValueError(f"unknown continental cup {cup}")
            cups.setdefault(cup, []).append(key)
    competitions = list(leagues.values())
    for cup, entrants in cups.items():
        region, name = CUPS[cup]
        competitions.append(dict(schema="competition", id="cup-"+cup.lower(), name=name,
            type="ContinentalClub", scope="Continental", regionId=region,
            format={"kind":"Knockout","legs":1}, participants={"explicit":entrants}))
    players = []
    for row in rows(args.players):
        club = "club-" + identifier(pick(row,"current_club_id","club_team_id","club_id"))
        if club not in teams:
            raise ValueError(f"unknown {club}")
        positions = []
        for raw in pick(row,"player_positions","sub_position","position").split(","):
            raw = raw.strip()
            pos = POSITIONS.get(TM_POSITIONS.get(raw.lower(),raw.upper()))
            if not pos:
                raise ValueError(f"unknown position {raw!r}")
            if pos not in positions:
                positions.append(pos)
        player = dict(id="player-"+identifier(pick(row,"player_id","sofifa_id")),
                      name=pick(row,"short_name","name","long_name"), club=club, position=positions[0])
        if len(positions)>1:
            player["alternatePositions"] = positions[1:]
        for field, keys in {"overall":["overall"],"potential":["potential"],"wage":["wage_eur","weekly_wage"],
                            "value":["value_eur","market_value_in_eur"],"age":["age"]}.items():
            value = pick(row,*keys,default="")
            if value:
                player[field] = int(value)
        birth = pick(row,"dob","date_of_birth",default="")
        if birth:
            player["dateOfBirth"] = birth
            player.pop("age",None)
        players.append(player)
    if not teams or not players:
        raise ValueError("expected at least one club and one player")
    write(root,"teams/teams.json",dict(schema="team",items=list(teams.values())))
    write(root,"players/players.json",dict(schema="player",items=players))
    for comp in competitions:
        write(root,"competitions/"+comp["id"]+".json",comp)
    write(root,"package.json",dict(schema="world",id="custom-world",name="Custom World",
          version="1.0.0",packageType="database",formatVersion=1,baseYear=args.year,
          defaultActiveCompetitions=[c["id"] for c in competitions]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clubs",type=Path)
    parser.add_argument("players",type=Path)
    parser.add_argument("--year",type=int,required=True)
    parser.add_argument("--output",type=Path,default=Path("custom-world-package"))
    parser.add_argument("--cli",default="ofm-cli")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=args.output.parent) as staging:
            package = Path(staging) / "world"
            generate(args, package)
            subprocess.run([args.cli,"validate",str(package)],check=True)
            package.rename(args.output)
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        parser.exit(1,f"Import failed: {exc}\n")


if __name__ == "__main__":
    main()
