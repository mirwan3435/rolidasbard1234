import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Drawer, EmptyState, Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";
import { fmtTime } from "../lib/format";

type Row = {
  id: string; ts: string; symbol: string; strategy: string; direction: string; score: number | null; outcome: string; reason: string; source?: string;
  signal?: Record<string, unknown>; scores?: Record<string, number>; grok?: Record<string, unknown> | null;
  risk?: { failed?: string[]; passed?: string[]; lot?: number; risk_pct?: number };
};

export default function DecisionsPage() {
  const { t } = useI18n();
  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState("");
  const [outcome, setOutcome] = useState("");
  const query = useQuery({
    queryKey: ["decisions-page", symbol, strategy, outcome],
    queryFn: () => api<{ decisions: Row[] }>(`/api/decisions?symbol=${encodeURIComponent(symbol)}&strategy=${encodeURIComponent(strategy)}&outcome=${encodeURIComponent(outcome)}`),
  });
  const [openId, setOpenId] = useState<string | null>(null);
  const detail = useQuery({
    queryKey: ["decision", openId],
    queryFn: () => api<Row>(`/api/decisions/${encodeURIComponent(openId || "")}`),
    enabled: Boolean(openId),
  });
  const rows = query.data?.decisions || [];
  const open = detail.data;
  return (
    <Panel title={t("nav.decisions")} source={rows.some((row) => row.source === "real") || rows.length ? "real" : "sample"}>
      <div className="grid grid-cols-3 gap-2 mb-2">
        <input className="field" placeholder={t("common.symbol")} aria-label={t("common.symbol")} value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        <input className="field" placeholder={t("decisions.strategy")} aria-label={t("decisions.strategy")} value={strategy} onChange={(e) => setStrategy(e.target.value)} />
        <select className="field" aria-label={t("decisions.outcome")} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
          <option value="">{t("common.all")}</option>
          <option value="placed">placed</option>
          <option value="rejected">rejected</option>
          <option value="skipped">skipped</option>
        </select>
      </div>
      {rows.length === 0 && <EmptyState text={t("decisions.empty")} />}
      <table className="table">
        <thead><tr><th>{t("common.time")}</th><th>{t("common.symbol")}</th><th>{t("decisions.strategy")}</th><th>{t("common.direction")}</th><th>{t("decisions.score")}</th><th>{t("decisions.outcome")}</th><th>{t("common.reason")}</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id + row.ts} onClick={() => setOpenId(row.id)}>
              <td>{fmtTime(row.ts)}</td><td>{row.symbol}</td><td>{row.strategy}</td><td>{row.direction}</td><td>{row.score ?? "—"}</td><td>{row.outcome}</td><td>{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {openId && open && (
        <Drawer title={open.symbol || open.id} onClose={() => setOpenId(null)}>
          <p>{open.direction} · {open.outcome} · {open.reason}</p>
          <h3 className="mt-3">{t("decisions.score")}</h3>
          <pre className="mono text-xs whitespace-pre-wrap">{JSON.stringify(open.scores || open.signal || {}, null, 2)}</pre>
          <h3 className="mt-3">{t("decisions.grok")}</h3>
          <pre className="mono text-xs whitespace-pre-wrap">{JSON.stringify(open.grok || { verdict: "reject" }, null, 2)}</pre>
          <h3 className="mt-3">{t("decisions.passed")}</h3>
          <p>{(open.risk?.passed || []).join("; ") || "—"}</p>
          <h3>{t("decisions.failed")}</h3>
          <p>{(open.risk?.failed || []).join("; ") || "—"}</p>
          <p className="text-sm text-muted">lot {open.risk?.lot ?? "—"} · risk {open.risk?.risk_pct ?? "—"}</p>
        </Drawer>
      )}
    </Panel>
  );
}
