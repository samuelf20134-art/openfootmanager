import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useBackendList } from "../../hooks/useBackendList";
import type { GameStateData } from "../../store/gameStore";
import catalogue from "./historicalWinners.json";

type Winner = [string, number, string];
const fetchWinners = () => invoke<Winner[]>("get_archived_title_winners");
const competitions: Record<string, string> = {
  "league-bra1": "Campeonato Brasileiro",
  "copa-uniao": "Copa União · Módulo Verde",
  "cup-ucl": "UEFA Champions League",
  "world-cup": "Copa do Mundo",
};
const aliases: Record<string, string> = {
  "FC Barcelona": "Barcelona", "CR Flamengo": "Flamengo", "Clube de Regatas do Flamengo": "Flamengo",
  "SE Palmeiras": "Palmeiras", "Sport Recife": "Sport", "Real Madrid CF": "Real Madrid",
};

export default function HistoricalRanking({ game }: { game: GameStateData }) {
  const [competition, select] = useState("league-bra1");
  const saved = useBackendList(fetchWinners, `${game.career_token ?? 0}|${game.clock.current_date}`);
  const names: Record<string, string> = { ...competitions };
  const teams = new Map(game.teams.map((team) => [team.id, team.name]));
  const records = new Map<string, { team: string; year: number; edition: string }>();
  const currentYear = Number(game.clock.current_date.slice(0, 4));
  for (const entry of catalogue.editions) {
    if (entry.competition !== competition || entry.year >= currentYear) continue;
    const edition = entry.edition ?? "";
    records.set(`${entry.year}|${edition}`, { team: entry.club, year: entry.year, edition });
  }
  for (const [id, year, winner] of saved) {
    names[id] ??= game.competitions?.find((item) => item.id === id)?.name ?? id;
    if (id === competition) records.set(`${year}|`, { team: teams.get(winner) ?? winner, year, edition: "" });
  }
  if (competition === "world-cup") {
    for (const champion of game.world_history?.world_cup_champions ?? []) {
      records.set(`${champion.year}|`, { team: champion.nation_name, year: champion.year, edition: "" });
    }
  }
  const groups = new Map<string, string[]>();
  for (const { team, year, edition } of [...records.values()].sort((a, b) => a.year - b.year)) {
    const name = aliases[team] ?? team;
    const years = groups.get(name) ?? [];
    years.push(edition ? `${year} (${edition})` : String(year));
    groups.set(name, years);
  }
  const ranking = [...groups].sort(([a, x], [b, y]) => y.length - x.length || a.localeCompare(b));
  return (
    <section className="rounded-xl p-4 bg-white dark:bg-navy-800">
      <h3 className="font-heading text-xl font-bold mb-3">Ranking histórico de campeões</h3>
      <select aria-label="Competição" value={competition} onChange={(event) => select(event.target.value)} className="rounded p-2 dark:bg-navy-700">
        {Object.entries(names).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
      </select>
      {ranking.length === 0 && <p className="mt-3">Nenhuma edição registrada.</p>}
      <ol className="mt-3 divide-y">
        {ranking.map(([club, years]) => (
          <li key={club} className="py-2"><strong>{club} · {years.length}</strong><div className="text-sm">{years.join(", ")}</div></li>
        ))}
      </ol>
    </section>
  );
}
