import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, sessionToken } from "../api/client";
import { GrokMark } from "../components/ui/GrokMark";
import { Panel, Tabs } from "../components/ui/Panel";
import { useI18n } from "../i18n";
import { fmtTime } from "../lib/format";

type Agent = { id: string; label: string; state: string; color: string; task: string; llm: boolean; events_today: number; summary?: string; tier?: string };
const PIPE = ["DATA", "CONTEXT", "SCOPE", "WHALES", "PROFILER", "DEBATE", "CORE", "PORTFOLIO", "RISK", "EXEC", "POSMGR"];
const SIDE = ["JOURNAL", "WATCHDOG"];

export default function RoomPage() {
  const { t } = useI18n();
  const [view, setView] = useState("overview");
  const [selected, setSelected] = useState("SCOPE");
  const [packet, setPacket] = useState(0);
  const query = useQuery({ queryKey: ["room"], queryFn: () => api<{ agents: Agent[]; source: "real" | "sample" }>("/api/agentroom/state"), refetchInterval: 2000 });
  const events = useQuery({
    queryKey: ["room-events", selected],
    queryFn: () => api<{ events: { ts?: string; summary?: string }[] }>(`/api/events?agent=${selected}&limit=20`),
  });
  const agents = query.data?.agents || [];
  const byId = Object.fromEntries(agents.map((agent) => [agent.id, agent]));
  const follow = agents.find((agent) => agent.state === "working")?.id || selected;

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${location.host}/api/ws/handoff?token=${encodeURIComponent(sessionToken())}`);
    socket.onmessage = () => setPacket((value) => value + 1);
    return () => socket.close();
  }, []);

  function desk(id: string, index: number, row: number) {
    const agent = byId[id];
    const x = view === "workflow" ? 24 + index * 78 : view === "top" ? 30 + (index % 6) * 90 : 40 + index * 62 + row * 18;
    const y = view === "workflow" ? 70 : view === "top" ? 36 + Math.floor(index / 6) * 70 : 150 - index * 8 + row * 46;
    const active = view === "follow" && id === follow;
    return { id, agent, x, y, active };
  }
  const desks = [...PIPE.map((id, index) => desk(id, index, 0)), ...SIDE.map((id, index) => desk(id, index, 1))];

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 300px" }}>
      <Panel title={t("room.title")} source={query.data?.source} subtitle={t("room.pipeline")}>
        <Tabs tabs={[
          { id: "overview", label: t("room.overview") },
          { id: "top", label: t("room.top") },
          { id: "workflow", label: t("room.workflow") },
          { id: "follow", label: t("room.follow") },
        ]} value={view} onChange={setView} />
        <svg viewBox="0 0 760 280" width="100%" height="280" role="img" aria-label={t("room.title")}>
          <polygon points="40,190 700,190 740,230 80,230" fill="#0c1218" stroke="var(--border)" />
          {desks.map((item) => (
            <g key={item.id} transform={`translate(${item.x} ${item.y})`} onClick={() => setSelected(item.id)} style={{ cursor: "pointer" }}>
              <polygon points="0,18 34,18 46,28 12,28" fill={item.agent?.state === "error" ? "#3a1618" : "#121820"} stroke={item.agent?.color || "var(--border)"} />
              <polygon points="0,18 34,18 34,8 0,8" fill={item.agent?.state === "working" ? item.agent.color : "#0e141b"} opacity={item.agent?.state === "idle" ? 0.45 : 1} />
              {item.active && <circle cx="18" cy="8" r="8" fill="none" stroke="var(--accent)" />}
              <text x="0" y="44" fill="var(--muted)" fontSize="9">{item.id}</text>
            </g>
          ))}
          {packet > 0 && <circle className="packet" r="4" fill="var(--accent)" style={{ offsetPath: "path('M70 160 H640')" }} />}
        </svg>
        <p className="text-xs text-muted">{t("room.legend")}</p>
      </Panel>
      <Panel title={selected} source={query.data?.source}>
        <GrokMark state={byId[selected]?.state === "working" ? "active" : byId[selected]?.state === "error" ? "error" : "idle"} color={byId[selected]?.color} />
        <p className="text-sm mt-2">{byId[selected]?.summary || byId[selected]?.task || "—"}</p>
        <p className="text-xs text-muted">{byId[selected]?.llm ? "LLM" : "DETERMINISTIC"} · {byId[selected]?.events_today ?? 0}</p>
        <h3 className="mt-3 text-sm">{t("room.events")}</h3>
        <ul className="text-sm">
          {(events.data?.events || []).slice(0, 20).map((event, index) => (
            <li key={index}>{fmtTime(event.ts)} · {event.summary}</li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
