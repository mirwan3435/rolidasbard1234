import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Bars } from "../components/ui/Charts";
import { KpiCard, Panel, Spinner } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Costs = {
  tokens_today: number; calls_today: number; tokens_7d: number; calls_7d: number;
  usd_today: number | null; usd_7d: number | null; prices_set: boolean; price_note: string;
  token_budget: number; usd_budget: number | null; by_agent: Record<string, number>;
  recent?: { ts: string; agent: string; model: string; tokens_in: number; tokens_out: number }[];
  source: "real" | "sample";
};

export default function CostsPage() {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["costs-page"], queryFn: () => api<Costs>("/api/costs") });
  const data = query.data;
  if (!data) return <Panel title={t("costs.title")}><Spinner /></Panel>;
  const pct = Math.min(100, (data.tokens_today / (data.token_budget || 1)) * 100);
  const rows = Object.entries(data.by_agent || {}).map(([label, value]) => ({ label, value }));
  return (
    <div className="space-y-4">
      {!data.prices_set && <div className="banner warn">{data.price_note || t("costs.priceNote")} <Link to="/pengaturan">{t("nav.settings")}</Link></div>}
      <Panel title={t("costs.title")} source={data.source}>
        <div className="grid grid-cols-4 gap-2">
          <KpiCard label={t("costs.today")} value={String(data.tokens_today)} />
          <KpiCard label={t("costs.calls")} value={String(data.calls_today)} />
          <KpiCard label={t("costs.week")} value={String(data.tokens_7d)} />
          <KpiCard label="USD" value={data.usd_today == null ? "—" : data.usd_today.toFixed(4)} />
        </div>
        <div className="h-2 mt-3" style={{ background: "var(--surface-2)" }}>
          <div style={{ width: `${pct}%`, height: 8, background: pct > 90 ? "var(--danger)" : "var(--accent)" }} />
        </div>
        <p className="text-xs text-muted mt-1">{data.tokens_today} / {data.token_budget}</p>
        <h3 className="mt-3 text-sm">{t("costs.byAgent")}</h3>
        <Bars label={t("costs.byAgent")} rows={rows} />
        <h3 className="text-sm">{t("costs.recent")}</h3>
        <ul className="text-sm">
          {(data.recent || []).slice(0, 12).map((row, index) => (
            <li key={index}>{row.agent} · {row.model || "—"} · {row.tokens_in + row.tokens_out}</li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
