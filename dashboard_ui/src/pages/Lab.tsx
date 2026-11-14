import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { EmptyState, Panel, Spinner } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Run = { id: string; status: string; kpis?: { trade_count: number; win_rate: number; expectancy_r: number; net_usd: number; max_drawdown_pct: number }; warning?: string; equity_curve?: { equity: number }[]; source?: string };

export default function LabPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const strategies = useQuery({ queryKey: ["lab-strategies"], queryFn: () => api<{ strategies: { id: string; kind: string; note: string }[] }>("/api/lab/strategies") });
  const symbols = useQuery({ queryKey: ["symbols"], queryFn: () => api<{ symbols: { name: string }[] }>("/api/symbols") });
  const [symbol, setSymbol] = useState("EURUSDm");
  const [timeframe, setTimeframe] = useState("M5");
  const [csv, setCsv] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [message, setMessage] = useState("");

  async function upload() {
    setMessage("");
    try {
      await api("/api/lab/history", { method: "POST", body: JSON.stringify({ symbol, timeframe, csv }) });
      setMessage("CSV tersimpan.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Gagal");
    }
  }

  async function runBacktest() {
    setMessage("");
    try {
      const started = await api<{ run_id: string }>("/api/lab/runs", { method: "POST", body: JSON.stringify({ symbol, timeframe, params: { atr_period: 14 } }) });
      for (let i = 0; i < 20; i += 1) {
        const doc = await api<Run>(`/api/lab/runs/${started.run_id}`);
        setRun(doc);
        if (doc.status !== "running") break;
        await new Promise((resolve) => setTimeout(resolve, 400));
      }
      client.invalidateQueries({ queryKey: ["lab-runs"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Gagal");
    }
  }

  const list = strategies.data?.strategies || [];
  return (
    <div className="space-y-4">
      <Panel title={t("lab.title")} source="sample" subtitle={t("lab.reference")}>
        {list.length === 0 && <EmptyState text={t("lab.empty")} />}
        {list.map((item) => <p key={item.id}>{item.id} · {item.kind} · {item.note}</p>)}
        <div className="banner warn mt-3">{t("lab.warning")}</div>
      </Panel>
      <Panel title="CSV" source="real">
        <div className="grid grid-cols-2 gap-2">
          <select className="field" value={symbol} onChange={(e) => setSymbol(e.target.value)} aria-label="Simbol">
            {(symbols.data?.symbols || [{ name: "EURUSDm" }]).map((row) => <option key={row.name}>{row.name}</option>)}
          </select>
          <select className="field" value={timeframe} onChange={(e) => setTimeframe(e.target.value)} aria-label="Timeframe">
            {["M1", "M5", "M15"].map((tf) => <option key={tf}>{tf}</option>)}
          </select>
        </div>
        <textarea className="field mt-2 min-h-28 mono" placeholder="time,open,high,low,close,volume" value={csv} onChange={(e) => setCsv(e.target.value)} />
        <div className="flex gap-2 mt-2">
          <button className="btn" onClick={upload}>{t("common.save")}</button>
          <button className="btn primary" onClick={runBacktest}>{t("lab.run")}</button>
        </div>
        {message && <p className="mt-2">{message}</p>}
      </Panel>
      {run?.status === "running" && <Spinner />}
      {run?.kpis && (
        <Panel title="KPI" source={run.source === "real" ? "real" : "sample"}>
          {run.warning && <div className="banner warn mb-2">{run.warning}</div>}
          <p>Trade {run.kpis.trade_count} · win {run.kpis.win_rate.toFixed(1)}% · R {run.kpis.expectancy_r.toFixed(2)} · net {run.kpis.net_usd.toFixed(2)} · DD {run.kpis.max_drawdown_pct.toFixed(1)}%</p>
          <svg width="100%" height="80" aria-label="equity">
            {(run.equity_curve || []).map((point, index, all) => {
              const max = Math.max(...all.map((item) => item.equity));
              const min = Math.min(...all.map((item) => item.equity));
              const x = all.length < 2 ? 0 : (index / (all.length - 1)) * 300;
              const y = 70 - ((point.equity - min) / (max - min || 1)) * 60;
              return <circle key={index} cx={x} cy={y} r="2" fill="var(--accent)" />;
            })}
          </svg>
        </Panel>
      )}
    </div>
  );
}
