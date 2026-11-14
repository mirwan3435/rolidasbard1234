import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { AreaChart, Bars, DrawdownChart, Sparkline } from "../components/ui/Charts";
import { EmptyState, KpiCard, Panel, Spinner } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Strategy = { id: string; kind: string; note: string; source?: string; param_schema?: { properties?: Record<string, { default?: number; type?: string }> } };
type Run = {
  id: string; status: string; strategy?: string; symbol?: string; source?: string; warning?: string; data_source?: string;
  kpis?: { trade_count: number; win_rate: number; expectancy_r: number; net_usd: number; max_drawdown_pct: number; profit_factor: number | null; monthly_r?: { month: string; r: number }[]; drawdown_curve?: { dd: number }[] };
  equity_curve?: { equity: number }[];
};

export default function LabPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const strategies = useQuery({ queryKey: ["lab-strategies"], queryFn: () => api<{ strategies: Strategy[] }>("/api/lab/strategies") });
  const symbols = useQuery({ queryKey: ["symbols"], queryFn: () => api<{ symbols: { name: string }[] }>("/api/symbols") });
  const history = useQuery({ queryKey: ["lab-runs"], queryFn: () => api<{ runs: Run[] }>("/api/lab/runs") });
  const config = useQuery({ queryKey: ["config"], queryFn: () => api<{ config: { active_profile: string; profiles: Record<string, { commission_verified?: boolean; commission_per_lot_usd?: number }> } }>("/api/config") });
  const [strategy, setStrategy] = useState("reference_atr_breakout");
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("M5");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [csv, setCsv] = useState("");
  const [params, setParams] = useState<Record<string, number>>({});
  const [run, setRun] = useState<Run | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const list = strategies.data?.strategies || [];
  const chosen = list.find((item) => item.id === strategy) || list[0];
  const fields = chosen?.param_schema?.properties || {};
  const active = config.data?.config.profiles?.[config.data.config.active_profile];
  const warn = !active?.commission_verified || active?.commission_per_lot_usd === 7;
  const symbolName = symbol || symbols.data?.symbols?.[0]?.name || "";
  function sparkOf(id: string) {
    const last = (history.data?.runs || []).find((item) => item.strategy === id && item.equity_curve && item.equity_curve.length > 1);
    return (last?.equity_curve || []).map((point) => point.equity);
  }

  const formParams = useMemo(() => {
    const next: Record<string, number> = {};
    Object.entries(fields).forEach(([key, spec]) => { next[key] = params[key] ?? Number(spec.default ?? 0); });
    return next;
  }, [fields, params]);

  async function upload() {
    setMessage("");
    try {
      await api("/api/lab/history", { method: "POST", body: JSON.stringify({ symbol: symbolName, timeframe, csv }) });
      setMessage(t("lab.saved"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("common.failed"));
    }
  }

  async function runBacktest() {
    setMessage("");
    setBusy(true);
    try {
      const started = await api<{ run_id: string }>("/api/lab/runs", {
        method: "POST",
        body: JSON.stringify({ symbol: symbolName, timeframe, strategy: chosen?.id || strategy, params: formParams, date_from: dateFrom, date_to: dateTo }),
      });
      for (let i = 0; i < 30; i += 1) {
        const doc = await api<Run>(`/api/lab/runs/${started.run_id}`);
        setRun(doc);
        if (doc.status !== "running") break;
        await new Promise((resolve) => setTimeout(resolve, 400));
      }
      client.invalidateQueries({ queryKey: ["lab-runs"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("common.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "280px 1fr" }}>
      <Panel title={t("lab.title")} source="sample" subtitle={t("lab.reference")}>
        {list.length === 0 && <EmptyState text={t("lab.empty")} />}
        {list.map((item) => (
          <button key={item.id} className={`side-link w-full text-left ${chosen?.id === item.id ? "active" : ""}`} onClick={() => setStrategy(item.id)}>
            <span className="flex justify-between gap-2"><span>{item.id}</span>{sparkOf(item.id).length > 1 && <Sparkline values={sparkOf(item.id)} />}</span>
            <span className="text-xs text-muted">{item.kind} · {item.note}</span>
          </button>
        ))}
      </Panel>
      <div className="space-y-4">
        {warn && <div className="banner warn">{t("lab.warning")}</div>}
        <Panel title={t("lab.params")} source={run?.source === "real" ? "real" : "sample"}>
          <div className="grid grid-cols-2 gap-2">
            <select className="field" value={symbolName} onChange={(e) => setSymbol(e.target.value)} aria-label={t("common.symbol")}>
              {(symbols.data?.symbols || []).map((row) => <option key={row.name}>{row.name}</option>)}
            </select>
            <select className="field" value={timeframe} onChange={(e) => setTimeframe(e.target.value)} aria-label={t("lab.timeframe")}>
              {["M1", "M5", "M15"].map((tf) => <option key={tf}>{tf}</option>)}
            </select>
            <label className="text-sm">{t("lab.from")}<input className="field" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label>
            <label className="text-sm">{t("lab.to")}<input className="field" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></label>
            {Object.entries(fields).map(([key, spec]) => (
              <label key={key} className="text-sm">{key}
                <input className="field" type="number" value={formParams[key] ?? ""} onChange={(e) => setParams({ ...formParams, [key]: Number(e.target.value) })} />
              </label>
            ))}
          </div>
          <textarea className="field mt-2 min-h-24 mono" placeholder="time,open,high,low,close,volume" value={csv} onChange={(e) => setCsv(e.target.value)} />
          <div className="flex gap-2 mt-2">
            <button className="btn" onClick={upload}>{t("lab.upload")}</button>
            <button className="btn primary" disabled={busy} onClick={runBacktest}>{t("lab.run")}</button>
            {busy && <Spinner size="sm" />}
          </div>
          {message && <p className="mt-2">{message}</p>}
          {!run && <EmptyState text={t("lab.empty")} />}
        </Panel>
        {run?.kpis && (
          <Panel title="KPI" source={run.source === "real" ? "real" : "sample"} subtitle={run.data_source}>
            {run.warning && <div className="banner warn mb-2">{run.warning}</div>}
            <div className="grid grid-cols-4 gap-2">
              <KpiCard label={t("lab.trades")} value={String(run.kpis.trade_count)} />
              <KpiCard label={t("lab.win")} value={`${run.kpis.win_rate.toFixed(1)}%`} />
              <KpiCard label={t("lab.expectancy")} value={run.kpis.expectancy_r.toFixed(2)} />
              <KpiCard label={t("lab.net")} value={run.kpis.net_usd.toFixed(2)} />
              <KpiCard label={t("lab.drawdown")} value={`${run.kpis.max_drawdown_pct.toFixed(1)}%`} />
              <KpiCard label={t("lab.pf")} value={run.kpis.profit_factor == null ? "—" : run.kpis.profit_factor.toFixed(2)} />
            </div>
            <h3 className="mt-3 text-sm">{t("lab.equity")}</h3>
            <AreaChart label={t("lab.equity")} values={(run.equity_curve || []).map((point) => point.equity)} />
            <h3 className="text-sm">{t("lab.drawdown")}</h3>
            <DrawdownChart label={t("lab.drawdown")} values={(run.kpis.drawdown_curve || []).map((point) => point.dd)} />
            <h3 className="text-sm">{t("lab.monthly")}</h3>
            <Bars label={t("lab.monthly")} rows={(run.kpis.monthly_r || []).map((row) => ({ label: row.month, value: row.r }))} />
          </Panel>
        )}
        <Panel title={t("lab.history")} source="real">
          <table className="table">
            <tbody>
              {(history.data?.runs || []).map((item) => (
                <tr key={item.id} onClick={() => item.id && api<Run>(`/api/lab/runs/${item.id}`).then(setRun)}>
                  <td>{item.strategy}</td><td>{item.symbol}</td><td>{item.status}</td><td>{item.kpis?.expectancy_r?.toFixed?.(2) ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
