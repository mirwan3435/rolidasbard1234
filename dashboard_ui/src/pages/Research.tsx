import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Sparkline } from "../components/ui/Charts";
import { EmptyState, Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Item = { ts: string; summary: string; concepts: string[]; source_type: string };

function spot(seed: string, index: number) {
  let hash = index + 1;
  for (const char of seed) hash = (hash * 33 + char.charCodeAt(0)) % 997;
  const angle = (hash % 360) * Math.PI / 180;
  const ring = 40 + (hash % 50);
  return { x: 220 + Math.cos(angle) * ring, y: 120 + Math.sin(angle) * (ring * 0.55) };
}

export default function ResearchPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["research"], queryFn: () => api<{ items: Item[] }>("/api/research/items") });
  const clusters = useQuery({ queryKey: ["clusters"], queryFn: () => api<{ clusters: Record<string, { summary: string }[]> }>("/api/research/clusters") });
  const [value, setValue] = useState("");
  const [kind, setKind] = useState<"text" | "url">("text");
  const [message, setMessage] = useState("");
  const items = query.data?.items || [];
  const latest = items[0];
  const counts = ["youtube", "github", "arxiv", "article", "note"].map((name) => ({
    name,
    n: items.filter((item) => item.source_type === name).length,
  }));

  async function add() {
    setMessage("");
    try {
      await api("/api/research/ingest", { method: "POST", body: JSON.stringify({ kind, value }) });
      setValue("");
      client.invalidateQueries({ queryKey: ["research"] });
      client.invalidateQueries({ queryKey: ["clusters"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("common.failed"));
    }
  }

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "1.4fr .8fr" }}>
      <Panel title={t("research.map")} source={items.length ? "real" : "sample"}>
        {items.length === 0 && <EmptyState text={t("research.empty")} />}
        <svg viewBox="0 0 440 240" width="100%" height="240" role="img" aria-label={t("research.map")}>
          {Object.keys(clusters.data?.clusters || {}).map((concept, index) => {
            const at = spot(concept, index);
            return <text key={concept} x={at.x} y={at.y - 12} fill="var(--muted)" fontSize="11">{concept}</text>;
          })}
          {items.map((item, index) => {
            const at = spot(item.concepts[0] || item.source_type, index);
            return <circle key={`${item.ts}-${index}`} cx={at.x} cy={at.y} r="3.5" fill="var(--accent)"><title>{item.summary}</title></circle>;
          })}
        </svg>
      </Panel>
      <div className="space-y-4">
        <Panel title={t("research.now")} source={latest ? "real" : "sample"}>
          {latest ? <p>{latest.summary}</p> : <EmptyState text={t("research.empty")} />}
          <div className="flex flex-wrap gap-1 mt-2">
            {(latest?.concepts || []).map((tag) => <span key={tag} className="badge" style={{ color: "var(--accent)" }}>{tag}</span>)}
          </div>
        </Panel>
        <Panel title={t("nav.research")} source="real">
          {counts.map((row) => (
            <div key={row.name} className="flex justify-between items-center text-sm">
              <span>{row.name} · {row.n}</span>
              <Sparkline values={[row.n, row.n, row.n]} />
            </div>
          ))}
          <div className="flex gap-2 mt-2">
            <button className={`btn ${kind === "text" ? "primary" : ""}`} onClick={() => setKind("text")}>{t("research.text")}</button>
            <button className={`btn ${kind === "url" ? "primary" : ""}`} onClick={() => setKind("url")}>{t("research.url")}</button>
          </div>
          <textarea className="field mt-2 min-h-24" value={value} onChange={(e) => setValue(e.target.value)} />
          <button className="btn primary mt-2" onClick={add}>{t("research.add")}</button>
          {message && <p className="mt-2">{message}</p>}
        </Panel>
      </div>
    </div>
  );
}
