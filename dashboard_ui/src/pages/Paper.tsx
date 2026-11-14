import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import { useSettings } from "../components/Layout";
import { download, fmtTime, money } from "../lib/format";

type Trade = {
  id: number;
  symbol: string;
  direction: string;
  entry: number;
  exit: number;
  lot: number;
  result_usd: number;
  spread_cost_usd: number;
  commission_usd: number;
  r_multiple: number;
  reason: string;
  scope_score: number;
  closed_at: string;
};

type Stats = {
  journal: Trade[];
  equity_curve: { ts: string; equity: number }[];
  trade_count: number;
  win_rate: number;
  avg_r: number;
  max_drawdown_pct: number;
  disclaimer: string;
};

export function PaperPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const ladder = useQuery({
    queryKey: ["promotion"],
    queryFn: () => api<{ stages: { id: string; label: string; passed: boolean; locked: boolean; note?: string }[]; source: string }>("/api/promotion"),
  });
  const query = useQuery({
    queryKey: ["paper"],
    queryFn: () => api<Stats>("/api/paper/journal"),
    refetchInterval: settings.data?.refresh_ms ?? 2000,
  });
  const data = query.data;
  if (query.isLoading) return <div className="skeleton h-64" />;
  if (!data) return <p>Jurnal paper belum ada.</p>;

  function exportCsv() {
    const header = ["waktu", "simbol", "arah", "entry", "exit", "lot", "hasil_usd", "spread", "komisi", "r", "alasan", "skor_scope"];
    const lines = data!.journal.map((row) => [row.closed_at, row.symbol, row.direction, row.entry, row.exit, row.lot, row.result_usd, row.spread_cost_usd, row.commission_usd, row.r_multiple, `"${(row.reason || "").replaceAll('"', '""')}"`, row.scope_score].join(","));
    download("jurnal-paper.csv", [header.join(","), ...lines].join("\n"), "text/csv");
  }

  return (
    <div className="space-y-4">
      <div className="banner warn">{data.disclaimer}</div>
      <section className="card p-3">
        <h2 className="font-semibold">{t("promotion.title")}</h2>
        <ul className="mt-2 text-sm">
          {(ladder.data?.stages || []).map((stage) => (
            <li key={stage.id}>{stage.label}: {stage.passed ? "lolos" : "belum"} {stage.locked ? `· ${t("promotion.locked")}` : ""} {stage.note || ""}</li>
          ))}
        </ul>
      </section>
      <div className="grid grid-cols-4 gap-3">
        <Stat title="Jumlah trade" value={String(data.trade_count)} />
        <Stat title="Win rate" value={`${data.win_rate.toFixed(1)}%`} />
        <Stat title="Rata-rata R" value={data.avg_r.toFixed(2)} />
        <Stat title="Drawdown maks" value={`${data.max_drawdown_pct.toFixed(2)}%`} />
      </div>
      <section className="card p-3 h-72">
        <h2 className="font-semibold mb-2">Equity virtual</h2>
        {data.equity_curve.length === 0 ? <p className="text-muted">Belum ada kurva.</p> : (
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={data.equity_curve}>
              <CartesianGrid stroke="var(--line)" />
              <XAxis dataKey="ts" hide />
              <YAxis stroke="var(--muted)" domain={["auto", "auto"]} />
              <Tooltip />
              <Line type="monotone" dataKey="equity" stroke="var(--run)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>
      <section className="card p-3 overflow-auto">
        <div className="flex justify-between mb-2">
          <h2 className="font-semibold">Jurnal</h2>
          <button className="btn" onClick={exportCsv}>Ekspor CSV</button>
        </div>
        <table className="table">
          <thead><tr><th>Waktu</th><th>Simbol</th><th>Arah</th><th>Hasil</th><th>Spread</th><th>Komisi</th><th>R</th><th>Alasan</th><th>Skor SCOPE</th></tr></thead>
          <tbody>
            {data.journal.length === 0 && <tr><td colSpan={9}>Jurnal kosong.</td></tr>}
            {data.journal.map((row) => (
              <tr key={row.id}>
                <td>{fmtTime(row.closed_at, settings.data?.timezone)}</td>
                <td>{row.symbol}</td><td>{row.direction}</td>
                <td>{money(row.result_usd)}</td>
                <td>{money(row.spread_cost_usd)}</td>
                <td>{money(row.commission_usd)}</td>
                <td>{row.r_multiple}</td>
                <td>{row.reason}</td>
                <td>{row.scope_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Stat({ title, value }: { title: string; value: string }) {
  return <div className="card p-3"><div className="text-sm text-muted">{title}</div><div className="text-xl font-semibold">{value}</div></div>;
}
