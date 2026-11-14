import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { GrokMark } from "../components/ui/GrokMark";
import { Panel, StatusDot } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Agent = { id: string; label: string; state: string; color: string; task: string; llm: boolean; events_today: number };

export default function RoomPage() {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["room"], queryFn: () => api<{ agents: Agent[]; source: "real" | "sample" }>("/api/agentroom/state"), refetchInterval: 2000 });
  const agents = query.data?.agents || [];
  return (
    <Panel title={t("room.title")} source={query.data?.source}>
      <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))" }}>
        {agents.map((agent) => (
          <article key={agent.id} className="card p-2" style={{ borderColor: agent.color }}>
            <div className="flex items-center gap-2">
              <GrokMark state={agent.state === "working" ? "active" : agent.state === "error" ? "error" : "idle"} color={agent.color} />
              <strong>{agent.label}</strong>
              <StatusDot status={agent.state} />
            </div>
            <p className="text-xs text-muted mt-1">{agent.llm ? "LLM" : "DETERMINISTIC"} · {agent.events_today}</p>
            <p className="text-sm">{agent.task || "—"}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}
