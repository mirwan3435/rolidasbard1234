import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { type SymbolRow, useSettings } from "../components/Layout";
import { ageLabel } from "../lib/format";
import { useI18n } from "../i18n";

type Payload = { symbols: SymbolRow[]; correlation: { symbols: string[]; matrix: number[][]; warnings: string[]; mock: boolean } };

export function SymbolsPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["symbols"],
    queryFn: () => api<Payload>("/api/symbols"),
    refetchInterval: settings.data?.refresh_ms ?? 2000,
  });
  const data = query.data;

  async function toggle(name: string, enabled: boolean) {
    await api(`/api/symbols/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify({ enabled }) });
    client.invalidateQueries({ queryKey: ["symbols"] });
  }

  if (query.isLoading) return <div className="skeleton h-40" />;
  if (!data) return <p>{t("symbols.missing")}</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{t("symbols.note")}</p>
      <div className="card overflow-auto">
        <table className="table">
          <thead>
            <tr>
              <th>{t("symbols.symbol")}</th><th>{t("symbols.role")}</th><th>{t("symbols.enabled")}</th><th>{t("symbols.spread")}</th><th>{t("symbols.minLot")}</th><th>{t("symbols.step")}</th><th>{t("symbols.tick")}</th><th>{t("symbols.margin")}</th><th>{t("symbols.stops")}</th><th>{t("symbols.age")}</th><th>{t("symbols.session")}</th><th>{t("symbols.minRisk")}</th>
            </tr>
          </thead>
          <tbody>
            {data.symbols.map((row) => (
              <tr key={row.name}>
                <td className="mono">{row.name}</td>
                <td>{row.role === "context" ? t("symbols.context") : t("symbols.entry")}</td>
                <td>
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={row.enabled} onChange={(e) => toggle(row.name, e.target.checked)} aria-label={`Aktifkan ${row.name}`} />
                    {row.role === "context" && <span className="text-xs text-muted">{t("symbols.contextOnly")}</span>}
                  </label>
                </td>
                <td>{row.spread}</td>
                <td>{row.volume_min}</td>
                <td>{row.volume_step}</td>
                <td>{row.tick_value}</td>
                <td>{row.margin_per_lot}</td>
                <td>{row.stops_level}</td>
                <td>{ageLabel(row.tick_age_sec)}</td>
                <td>{row.session_open ? t("symbols.open") : t("symbols.closed")}</td>
                <td style={{ color: row.fit ? (row.fit.fits ? "var(--ok)" : "var(--bad)") : "var(--muted)" }}>
                  {row.fit ? `${row.fit.min_lot_risk_usd.toFixed(2)} / ${t("risk.limit")} ${row.fit.risk_budget_usd.toFixed(2)}` : t("symbols.notEntry")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <section className="card p-3">
        <h2 className="font-semibold mb-2">{t("symbols.correlation")} {data.correlation.mock ? "(SAMPLE)" : ""}</h2>
        {data.correlation.warnings.length > 0 && (
          <div className="banner warn mb-2">{t("symbols.corrWarn")} {data.correlation.warnings.join("; ")}</div>
        )}
        <div className="overflow-auto">
          <table className="table">
            <thead>
              <tr><th></th>{data.correlation.symbols.map((name) => <th key={name}>{name}</th>)}</tr>
            </thead>
            <tbody>
              {data.correlation.matrix.map((row, i) => (
                <tr key={data.correlation.symbols[i]}>
                  <th>{data.correlation.symbols[i]}</th>
                  {row.map((value, j) => (
                    <td key={j} style={{ color: Math.abs(value) >= 0.7 && i !== j ? "var(--warn)" : undefined }}>{value.toFixed(2)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
