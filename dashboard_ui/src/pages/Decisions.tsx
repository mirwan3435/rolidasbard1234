import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { EmptyState, Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Row = { id: string; ts: string; symbol: string; strategy: string; direction: string; score: number | null; outcome: string; reason: string; source: string; risk: { failed: string[]; passed: string[]; lot: number } };

export default function DecisionsPage() {
  const { t } = useI18n();
  const [symbol, setSymbol] = useState("");
  const query = useQuery({
    queryKey: ["decisions", symbol],
    queryFn: () => api<{ decisions: Row[] }>(`/api/decisions?symbol=${encodeURIComponent(symbol)}`),
  });
  const [open, setOpen] = useState<Row | null>(null);
  const rows = query.data?.decisions || [];
  return (
    <Panel title={t("nav.decisions")} source={rows.length ? "real" : "sample"}>
      <input className="field mb-2" placeholder="Simbol" aria-label="Simbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
      {rows.length === 0 && <EmptyState text={t("decisions.empty")} />}
      <table className="table">
        <tbody>
          {rows.map((row) => (
            <tr key={row.id + row.ts} onClick={() => setOpen(row)}>
              <td>{row.ts}</td><td>{row.symbol}</td><td>{row.outcome}</td><td>{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {open && (
        <aside className="card p-3 mt-3">
          <p>{open.symbol} {open.direction} · {open.outcome}</p>
          <p>Gagal: {(open.risk?.failed || []).join("; ") || "—"}</p>
          <button className="btn" onClick={() => setOpen(null)}>Tutup</button>
        </aside>
      )}
    </Panel>
  );
}
