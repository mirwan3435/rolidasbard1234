import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Card = { id: string; title: string; plain_language: string; code_snippet: string; status: string; source?: string };

export default function KnowledgePage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["cards"], queryFn: () => api<{ cards: Card[] }>("/api/knowledge/cards") });
  const [index, setIndex] = useState(0);
  const [note, setNote] = useState("");
  const cards = query.data?.cards || [];
  const card = cards[index];

  async function vote(verdict: "ok" | "not_ok") {
    if (!card) return;
    await api(`/api/knowledge/cards/${card.id}/verdict`, { method: "POST", body: JSON.stringify({ verdict, note }) });
    setNote("");
    client.invalidateQueries({ queryKey: ["cards"] });
  }

  if (!card) return <Panel title={t("nav.knowledge")}><p>{t("common.loading")}</p></Panel>;
  return (
    <Panel title={card.title} subtitle={`${index + 1}/${cards.length}`} source={card.source === "sample" ? "sample" : "real"}>
      <p>{card.plain_language}</p>
      <pre className="mono text-xs mt-2">{card.code_snippet}</pre>
      <p className="text-sm text-muted mt-2">Status: {card.status}</p>
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
