import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Candles } from "../components/ui/Charts";
import { Panel, Spinner } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Card = { id: string; title: string; plain_language: string; code_snippet: string; status: string; source?: "real" | "sample"; example_candles?: { o: number; h: number; l: number; c: number }[] };

export default function KnowledgePage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["cards"], queryFn: () => api<{ cards: Card[] }>("/api/knowledge/cards") });
  const [index, setIndex] = useState(0);
  const [note, setNote] = useState("");
  const [search, setSearch] = useState("");
  const cards = useMemo(() => (query.data?.cards || []).filter((card) => `${card.title} ${card.plain_language}`.toLowerCase().includes(search.toLowerCase())), [query.data, search]);
  const card = cards[Math.min(index, Math.max(0, cards.length - 1))];

  async function vote(verdict: "ok" | "not_ok") {
    if (!card) return;
    await api(`/api/knowledge/cards/${card.id}/verdict`, { method: "POST", body: JSON.stringify({ verdict, note }) });
    setNote("");
    client.invalidateQueries({ queryKey: ["cards"] });
    client.invalidateQueries({ queryKey: ["review-count"] });
  }

  if (!query.data) return <Panel title={t("nav.knowledge")}><Spinner /></Panel>;
  if (!card) return <Panel title={t("nav.knowledge")}><p>{t("common.empty")}</p></Panel>;
  return (
    <Panel title={card.title} subtitle={`${index + 1}/${cards.length}`} source={card.source === "real" ? "real" : "sample"}>
      <input className="field mb-3" placeholder={t("common.search")} aria-label={t("common.search")} value={search} onChange={(e) => { setSearch(e.target.value); setIndex(0); }} />
      <p>{card.plain_language}</p>
      <Candles rows={card.example_candles || []} />
      <pre className="mono text-xs mt-2 whitespace-pre-wrap">{card.code_snippet}</pre>
      <p className="text-sm text-muted mt-2">{t("knowledge.status")}: {card.status}</p>
      <div className="flex gap-1 my-2">
        {cards.map((item, dot) => <button key={item.id} aria-label={item.title} className="dot" style={{ background: dot === index ? "var(--accent)" : undefined }} onClick={() => setIndex(dot)} />)}
      </div>
      <label className="text-sm">{t("knowledge.note")}
        <textarea className="field" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="flex gap-2 mt-2">
        <button className="btn" onClick={() => setIndex((index - 1 + cards.length) % cards.length)}>←</button>
        <button className="btn primary" onClick={() => vote("ok")}>{t("knowledge.match")}</button>
        <button className="btn" onClick={() => vote("not_ok")}>{t("knowledge.mismatch")}</button>
        <button className="btn" onClick={() => setIndex((index + 1) % cards.length)}>→</button>
      </div>
    </Panel>
  );
}
