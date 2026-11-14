import type { ReactNode } from "react";
import { useI18n } from "../../i18n";

export function Panel({ title, subtitle, source, actions, children }: { title: string; subtitle?: string; source?: "real" | "sample"; actions?: ReactNode; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <section className="panel">
      <header className="panel-title">
        <span>▪ {title}{subtitle ? ` · ${subtitle}` : ""}</span>
        <span className="panel-actions">
          {source && <span className={`badge ${source === "real" ? "ok" : ""}`}>{source === "real" ? t("source.real") : t("source.sample")}</span>}
          {actions}
        </span>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const dim = size === "sm" ? 14 : size === "lg" ? 28 : 18;
  return <span className="spinner" style={{ width: dim, height: dim }} role="status" aria-busy="true" />;
}

export function StatusDot({ status }: { status: string }) {
  const map: Record<string, string> = { connected: "ok", working: "ok", idle: "warn", disconnected: "bad", error: "bad", offline: "idle", not_configured: "idle" };
  return <span className={`dot ${map[status] || "idle"}`} />;
}

export function EmptyState({ text }: { text: string }) {
  return <p className="empty">{text}</p>;
}

export function KpiCard({ label, value }: { label: string; value: string }) {
  return <div className="kpi"><span className="text-muted text-xs">{label}</span><b>{value}</b></div>;
}

export function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <div className="drawer-back" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label={title} onClick={(event) => event.stopPropagation()}>
        <div className="flex justify-between items-center mb-3">
          <strong>{title}</strong>
          <button className="btn" type="button" onClick={onClose}>{t("common.close")}</button>
        </div>
        {children}
      </aside>
    </div>
  );
}

export function Tabs({ tabs, value, onChange }: { tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <button key={tab.id} className={`btn ${value === tab.id ? "primary" : ""}`} type="button" onClick={() => onChange(tab.id)}>{tab.label}</button>
      ))}
    </div>
  );
}
