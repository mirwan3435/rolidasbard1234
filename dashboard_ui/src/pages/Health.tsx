import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { type Status, useSettings } from "../components/Layout";
import { ageLabel } from "../lib/format";
import { useI18n } from "../i18n";

type Meta = {
  version: string;
  git: string;
  corrupt_lines: number;
  grok_last_ok: boolean | null;
  grok_last_message: string;
  grok_tokens_today: number;
  estimated_cost_today: number;
  token_usd_per_million: number;
  server_offset_hours: number;
  mt5_connected: boolean;
  mt5_message: string;
};

export function HealthPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const refresh = settings.data?.refresh_ms ?? 2000;
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta"), refetchInterval: refresh });
  const status = useQuery({ queryKey: ["status-health"], queryFn: () => api<Status>("/api/status"), refetchInterval: refresh });
  if (!meta.data || !status.data) return <div className="skeleton h-40" />;
  const info = meta.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Card title={t("health.version")} value={`${info.version} · ${info.git}`} />
        <Card title={t("health.mt5")} value={info.mt5_connected ? t("health.connected") : t("health.disconnected")} />
        <Card title={t("health.offset")} value={`${info.server_offset_hours} h UTC`} />
        <Card title={t("health.grok")} value={info.grok_last_ok == null ? t("health.untested") : info.grok_last_ok ? t("health.ok") : t("health.bad")} />
        <Card title={t("health.tokens")} value={String(info.grok_tokens_today)} />
        <Card title={t("health.cost")} value={`$${info.estimated_cost_today} @ ${info.token_usd_per_million}`} />
        <Card title={t("health.corrupt")} value={String(info.corrupt_lines)} />
      </div>
      <p className="text-sm text-muted">{info.mt5_message} {info.grok_last_message}</p>
      <section className="card p-3">
        <h2 className="font-semibold mb-2">{t("health.tickAge")}</h2>
        <ul className="text-sm grid grid-cols-2 gap-1">
          {status.data.symbols.map((row) => (
            <li key={row.name}>{row.name}: {ageLabel(row.tick_age_sec)} · {row.enabled ? t("health.on") : t("health.off")}</li>
          ))}
        </ul>
      </section>
      <section className="card p-3">
        <h2 className="font-semibold mb-2">{t("health.heartbeat")}</h2>
        <ul className="text-sm">
          {Object.entries(status.data.nodes).map(([id, node]) => (
            <li key={id}>{id}: {node.status} · {node.updated_at ? ageLabel(Math.max(0, (Date.now() - new Date(node.updated_at).getTime()) / 1000)) : t("health.never")} · {node.last_summary}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return <div className="card p-3"><div className="text-sm text-muted">{title}</div><div className="font-semibold">{value}</div></div>;
}
