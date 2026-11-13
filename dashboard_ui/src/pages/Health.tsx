import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { type Status, useSettings } from "../components/Layout";
import { ageLabel } from "../lib/format";

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
  const settings = useSettings();
  const refresh = settings.data?.refresh_ms ?? 2000;
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta"), refetchInterval: refresh });
  const status = useQuery({ queryKey: ["status-health"], queryFn: () => api<Status>("/api/status"), refetchInterval: refresh });
  if (!meta.data || !status.data) return <div className="skeleton h-40" />;
  const info = meta.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Card title="Versi" value={`${info.version} · ${info.git}`} />
        <Card title="MT5" value={info.mt5_connected ? "terhubung" : "tidak terhubung"} />
        <Card title="Offset jam server" value={`${info.server_offset_hours} jam vs UTC`} />
        <Card title="Grok" value={info.grok_last_ok == null ? "belum dites" : info.grok_last_ok ? "OK" : "gagal"} />
        <Card title="Token hari ini" value={String(info.grok_tokens_today)} />
        <Card title="Perkiraan biaya" value={`$${info.estimated_cost_today} @ ${info.token_usd_per_million}/jt`} />
        <Card title="Baris log rusak" value={String(info.corrupt_lines)} />
      </div>
      <p className="text-sm text-muted">{info.mt5_message} {info.grok_last_message}</p>
      <section className="card p-3">
        <h2 className="font-semibold mb-2">Usia tick</h2>
        <ul className="text-sm grid grid-cols-2 gap-1">
          {status.data.symbols.map((row) => (
            <li key={row.name}>{row.name}: {ageLabel(row.tick_age_sec)} · {row.enabled ? "aktif" : "mati"}</li>
          ))}
        </ul>
      </section>
      <section className="card p-3">
        <h2 className="font-semibold mb-2">Heartbeat node</h2>
        <ul className="text-sm">
          {Object.entries(status.data.nodes).map(([id, node]) => (
            <li key={id}>{id}: {node.status} · {node.updated_at ? ageLabel(Math.max(0, (Date.now() - new Date(node.updated_at).getTime()) / 1000)) : "belum"} · {node.last_summary}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return <div className="card p-3"><div className="text-sm text-muted">{title}</div><div className="font-semibold">{value}</div></div>;
}
