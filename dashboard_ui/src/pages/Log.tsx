import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, openEvents } from "../api/client";
import { useSettings } from "../components/Layout";
import { download, fmtTime } from "../lib/format";

type EventRow = { ts?: string; agent?: string; type?: string; symbol?: string; level?: string; summary?: string; data?: unknown };

const AGENTS = ["", "DATA", "SCOPE", "WHALES", "DEBATE", "RISK", "EXEC", "CORE", "SYSTEM"];
const LEVELS = ["", "debug", "info", "warn", "error"];

export function LogPage() {
  const settings = useSettings();
  const [tab, setTab] = useState<"log" | "audit">("log");
  const [agent, setAgent] = useState("");
  const [level, setLevel] = useState("");
  const [symbol, setSymbol] = useState("");
  const [text, setText] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [paused, setPaused] = useState(false);
  const [live, setLive] = useState<EventRow[]>([]);

  const history = useQuery({
    queryKey: ["events", agent, level, symbol, text, since, until],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "200" });
      if (agent) params.set("agent", agent);
      if (level) params.set("level", level);
      if (symbol) params.set("symbol", symbol);
      if (text) params.set("text", text);
      if (since) params.set("since", new Date(since).toISOString().replace(".000", ""));
      if (until) params.set("until", new Date(until).toISOString().replace(".000", ""));
      return api<{ events: EventRow[] }>(`/api/events?${params.toString()}`);
    },
    refetchInterval: paused ? false : (settings.data?.refresh_ms ?? 2000),
  });
  const audit = useQuery({
    queryKey: ["audit"],
    queryFn: () => api<{ rows: { ts: string; kind: string; summary: string; slot?: string }[] }>("/api/audit"),
    enabled: tab === "audit",
  });

  useEffect(() => {
    const socket = openEvents((event) => {
      if (paused) return;
      setLive((rows) => [event as EventRow, ...rows].slice(0, 200));
    }, { agent, symbol, level });
    return () => socket.close();
  }, [agent, symbol, level, paused]);

  const rows = [...live, ...(history.data?.events || [])].filter((row, index, all) => {
    const key = `${row.ts}|${row.summary}`;
    return all.findIndex((item) => `${item.ts}|${item.summary}` === key) === index;
  });

  function exportJson() {
    download("events.json", JSON.stringify(rows, null, 2), "application/json");
  }
  function exportCsv() {
    const lines = rows.map((row) => [row.ts, row.agent, row.level, row.symbol, `"${String(row.summary || "").replaceAll('"', '""')}"`].join(","));
    download("events.csv", ["waktu,agent,level,simbol,ringkasan", ...lines].join("\n"), "text/csv");
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button className={`btn ${tab === "log" ? "primary" : ""}`} onClick={() => setTab("log")}>Event</button>
        <button className={`btn ${tab === "audit" ? "primary" : ""}`} onClick={() => setTab("audit")}>Audit</button>
      </div>
      {tab === "log" && (
        <>
          <div className="grid grid-cols-6 gap-2">
            <select className="field" aria-label="Agent" value={agent} onChange={(e) => setAgent(e.target.value)}>
              {AGENTS.map((item) => <option key={item} value={item}>{item || "Semua agent"}</option>)}
            </select>
            <select className="field" aria-label="Level" value={level} onChange={(e) => setLevel(e.target.value)}>
              {LEVELS.map((item) => <option key={item} value={item}>{item || "Semua level"}</option>)}
            </select>
            <input className="field" placeholder="Simbol" aria-label="Simbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
            <input className="field" placeholder="Teks" aria-label="Teks" value={text} onChange={(e) => setText(e.target.value)} />
            <input className="field" type="datetime-local" aria-label="Dari" value={since} onChange={(e) => setSince(e.target.value)} />
            <input className="field" type="datetime-local" aria-label="Sampai" value={until} onChange={(e) => setUntil(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button className="btn" onClick={() => history.refetch()}>Terapkan filter riwayat</button>
            <button className="btn" onClick={() => setPaused((v) => !v)}>{paused ? "Lanjutkan scroll" : "Jeda"}</button>
            <button className="btn" onClick={exportJson}>Ekspor JSON</button>
            <button className="btn" onClick={exportCsv}>Ekspor CSV</button>
          </div>
          <div className="card p-2 max-h-[70vh] overflow-auto">
            {rows.length === 0 && <p className="text-muted p-2">Belum ada event. Mode mock mengirim event beberapa detik sekali.</p>}
            {rows.map((row, index) => (
              <article key={`${row.ts}-${index}`} className="border-b border-line py-1 text-sm">
                <span className="text-muted">{fmtTime(row.ts, settings.data?.timezone)}</span>{" "}
                <strong>{row.agent}</strong> {row.level} {row.symbol} — {row.summary}
              </article>
            ))}
          </div>
        </>
      )}
      {tab === "audit" && (
        <div className="card p-3">
          <p className="text-sm text-muted mb-2">Perubahan config, skill, dan API key. Nilai key tidak dicatat, hanya nama slot dan waktu.</p>
          <table className="table">
            <thead><tr><th>Waktu</th><th>Jenis</th><th>Ringkasan</th></tr></thead>
            <tbody>
              {(audit.data?.rows || []).length === 0 && <tr><td colSpan={3}>Belum ada audit.</td></tr>}
              {(audit.data?.rows || []).map((row, index) => (
                <tr key={index}><td>{fmtTime(row.ts, settings.data?.timezone)}</td><td>{row.kind}</td><td>{row.summary}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
