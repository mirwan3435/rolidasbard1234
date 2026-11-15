import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useSettings } from "../components/Layout";
import { Emblem } from "../components/ui/Emblem";
import { fmtTime, money } from "../lib/format";
import { useI18n } from "../i18n";

type RiskState = {
  virtual_capital: number;
  equity: number;
  peak: number;
  drawdown_pct: number;
  max_drawdown_pct: number;
  session_loss_pct: number;
  daily_loss_limit_pct: number;
  open_positions: number;
  max_open_positions: number;
  total_risk_usd: number;
  risk_limit_usd: number;
  total_margin_usd: number;
  margin_limit_usd: number;
  positions: { symbol: string; direction: string; lot: number; entry: number; stop: number; risk_usd: number }[];
  kill_switch: { active: boolean; reason: string; since: string; reset_hint: string };
  active_profile: string;
};

type Decision = { ts: string; symbol: string; approved: boolean; lot: number; risk_usd: number; reasons: string[]; summary: string };

function Gauge({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm"><span>{label}</span><span>{value.toFixed(2)} / {max.toFixed(2)}</span></div>
      <div className="h-2 rounded bg-black/20 mt-1"><div className="h-2 rounded" style={{ width: `${pct}%`, background: pct > 85 ? "var(--bad)" : "var(--run)" }} /></div>
    </div>
  );
}

export function RiskPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const refresh = settings.data?.refresh_ms ?? 2000;
  const state = useQuery({ queryKey: ["risk"], queryFn: () => api<RiskState>("/api/risk/state"), refetchInterval: refresh });
  const decisions = useQuery({ queryKey: ["decisions"], queryFn: () => api<{ decisions: Decision[] }>("/api/risk/decisions"), refetchInterval: refresh });
  const data = state.data;
  if (state.isLoading) return <div className="skeleton h-40" />;
  if (!data) return <p>{t("risk.missing")}</p>;
  const kill = data.kill_switch;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <Card title={t("risk.capital")} value={money(data.virtual_capital)} />
        <Card title={t("risk.equity")} value={money(data.equity)} />
        <Card title={t("risk.peak")} value={money(data.peak)} />
        <Card title={t("risk.profile")} value={data.active_profile} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Card title={t("risk.dd")} value={`${data.drawdown_pct.toFixed(2)}% / ${t("risk.limit")} ${data.max_drawdown_pct}%`} />
        <Card title={t("risk.session")} value={`${data.session_loss_pct.toFixed(2)}% / ${t("risk.limit")} ${data.daily_loss_limit_pct}%`} />
      </div>
      <section className="card p-3 space-y-3">
        <h2 className="font-semibold">{t("risk.exposure")}</h2>
        <Gauge label={t("risk.positions")} value={data.open_positions} max={data.max_open_positions} />
        <Gauge label={t("risk.riskUsd")} value={data.total_risk_usd} max={data.risk_limit_usd} />
        <Gauge label={t("risk.marginUsd")} value={data.total_margin_usd} max={data.margin_limit_usd} />
      </section>
      <section className="card p-3" style={{ borderColor: kill.active ? "var(--bad)" : undefined }}>
        <h2 className="font-semibold flex items-center gap-2"><Emblem size={22} state={kill.active ? "error" : "idle"} alarm={kill.active} />Kill-switch {kill.active ? t("risk.killOn") : t("risk.killOff")}</h2>
        {kill.active && <p className="mt-2">{fmtTime(kill.since, settings.data?.timezone)} — {kill.reason}</p>}
        <p className="text-sm mt-2">{kill.reset_hint}</p>
      </section>
      <section className="card p-3 overflow-auto">
        <h2 className="font-semibold mb-2">{t("risk.positions")}</h2>
        {data.positions.length === 0 && <p className="text-muted">{t("risk.noPositions")}</p>}
        {data.positions.length > 0 && (
          <table className="table">
            <thead><tr><th>{t("common.symbol")}</th><th>{t("common.direction")}</th><th>Lot</th><th>Entry</th><th>Stop</th><th>{t("risk.riskUsd")}</th></tr></thead>
            <tbody>
              {data.positions.map((pos, index) => (
                <tr key={index}><td>{pos.symbol}</td><td>{pos.direction}</td><td>{pos.lot}</td><td>{pos.entry}</td><td>{pos.stop}</td><td>{money(pos.risk_usd)}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section className="card p-3 overflow-auto">
        <h2 className="font-semibold mb-2">{t("risk.decisions")}</h2>
        <table className="table">
          <thead><tr><th>{t("common.time")}</th><th>{t("common.symbol")}</th><th>{t("common.result")}</th><th>{t("common.reason")}</th></tr></thead>
          <tbody>
            {(decisions.data?.decisions || []).length === 0 && <tr><td colSpan={4}>{t("risk.none")}</td></tr>}
            {(decisions.data?.decisions || []).map((row, index) => (
              <tr key={index}>
                <td>{fmtTime(row.ts, settings.data?.timezone)}</td>
                <td>{row.symbol}</td>
                <td style={{ color: row.approved ? "var(--ok)" : "var(--bad)" }}>{row.approved ? t("risk.approved") : t("risk.rejected")}</td>
                <td>{row.approved ? row.summary : (row.reasons || []).join("; ") || row.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return <div className="card p-3"><div className="text-sm text-muted">{title}</div><div className="text-xl font-semibold">{value}</div></div>;
}
