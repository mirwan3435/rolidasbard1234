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
