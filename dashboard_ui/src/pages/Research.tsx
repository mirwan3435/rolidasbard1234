import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { EmptyState, Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Item = { ts: string; summary: string; concepts: string[]; source_type: string };

export default function ResearchPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["research"], queryFn: () => api<{ items: Item[] }>("/api/research/items") });
  const [value, setValue] = useState("");
  const [kind, setKind] = useState<"text" | "url">("text");
  const [message, setMessage] = useState("");
  const items = query.data?.items || [];
  const concepts = Array.from(new Set(items.flatMap((item) => item.concepts)));

  async function add() {
    setMessage("");
    try {
      await api("/api/research/ingest", { method: "POST", body: JSON.stringify({ kind, value }) });
      setValue("");
      client.invalidateQueries({ queryKey: ["research"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Gagal");
    }
  }

  return (
    <div className="space-y-4">
      <Panel title={t("nav.research")} source={items.length ? "real" : "sample"}>
        {items.length === 0 && <EmptyState text={t("research.empty")} />}
        <svg viewBox="0 0 400 180" width="100%" height="180" role="img" aria-label="peta">
          {concepts.map((concept, index) => {
            const angle = (index / Math.max(1, concepts.length)) * Math.PI * 2;
            const x = 200 + Math.cos(angle) * 70;
            const y = 90 + Math.sin(angle) * 50;
            return <g key={concept}><circle cx={x} cy={y} r="4" fill="var(--accent)" /><text x={x + 8} y={y} fill="var(--muted)" fontSize="11">{concept}</text></g>;
          })}
        </svg>
        <ul className="text-sm">{items.slice(-8).map((item) => <li key={item.ts}>{item.source_type}: {item.summary}</li>)}</ul>
      </Panel>
      <Panel title={t("research.add")}>
        <select className="field" value={kind} onChange={(e) => setKind(e.target.value as "text" | "url")} aria-label="Jenis">
          <option value="text">Teks</option>
          <option value="url">URL</option>
        </select>
        <textarea className="field mt-2" value={value} onChange={(e) => setValue(e.target.value)} />
        <button className="btn primary mt-2" onClick={add}>{t("research.add")}</button>
        {message && <p>{message}</p>}
      </Panel>
    </div>
  );
}
