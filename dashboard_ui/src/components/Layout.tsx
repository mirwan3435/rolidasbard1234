import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, openEvents } from "../api/client";
import { useI18n } from "../i18n";
import type { DictKey } from "../i18n/id";
import { ageLabel } from "../lib/format";
import { StatusDot } from "./ui/Panel";

const GROUPS: [DictKey, [string, DictKey][]][] = [
  ["nav.overview", [["/", "nav.workflow"], ["/simbol", "nav.symbols"]]],
  ["nav.brain", [["/skill", "nav.skills"], ["/agentkamer", "nav.room"], ["/keputusan", "nav.decisions"]]],
  ["nav.money", [["/risk", "nav.risk"], ["/paper", "nav.paper"], ["/biaya", "nav.costs"], ["/config", "nav.config"]]],
  ["nav.system", [["/log", "nav.log"], ["/kesehatan", "nav.health"], ["/mesin", "nav.machine"], ["/kunci", "nav.keys"], ["/pengaturan", "nav.settings"]]],
  ["nav.tools", [["/lab", "nav.lab"], ["/riset", "nav.research"], ["/kennisbank", "nav.knowledge"]]],
];

export type Status = {
  mode: string;
  mt5_connected: boolean;
  mt5_message: string;
  kill_switch: { active: boolean; reason: string; since: string; reset_hint: string };
  commission_placeholder: boolean;
  commission_per_lot_usd: number;
  data_age_sec: number | null;
  nodes: Record<string, NodeState>;
  symbols: SymbolRow[];
  corrupt_lines: number;
  flowing: boolean;
  equity: number;
  drawdown_pct: number;
  grok_tokens_today: number;
  server_offset_hours: number;
  round?: number;
  decisions_today?: number;
};

export type NodeState = {
  status: string;
  updated_at?: string | null;
  latency_ms?: number | null;
  errors_1h: number;
  spark: number[];
  last_summary: string;
};

export type SymbolRow = {
  name: string;
  role: string;
  enabled: boolean;
  spread: number;
  volume_min: number;
  volume_step: number;
  tick_value: number;
  margin_per_lot: number;
  stops_level: number;
  tick_age_sec: number | null;
  session_open: boolean;
  fit: { min_lot_risk_usd: number; risk_budget_usd: number; fits: boolean; note: string } | null;
};

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: () => api<{
      theme: "dark" | "light"; timezone: string; refresh_ms: number; log_retention_days: number; token_usd_per_million: number;
      app_title?: string; language?: "id" | "en"; calendar_provider?: string; net_check_url?: string;
      grok_price_in_per_million?: number | null; grok_price_out_per_million?: number | null;
      grok_daily_token_budget?: number; grok_daily_usd_budget?: number | null;
    }>("/api/settings"),
  });
}

export function Layout() {
  const { t, lang } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const [tick, setTick] = useState("");
  const [now, setNow] = useState(() => new Date());
  const settings = useSettings();
  const refresh = settings.data?.refresh_ms ?? 2000;
  const status = useQuery({ queryKey: ["status-header"], queryFn: () => api<Status>("/api/status"), refetchInterval: refresh });
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<{ gitignore_missing: string[] }>("/api/meta"), refetchInterval: 10000 });
  const agents = useQuery({
    queryKey: ["agent-status"],
    queryFn: () => api<{ agents: { id: string; state: string; color: string }[] }>("/api/agents/status"),
    refetchInterval: refresh,
  });
  const costs = useQuery({
    queryKey: ["costs"],
    queryFn: () => api<{ tokens_today: number; token_budget: number }>("/api/costs"),
    refetchInterval: refresh,
  });
  const review = useQuery({ queryKey: ["review-count"], queryFn: () => api<{ cards: unknown[] }>("/api/knowledge/review"), refetchInterval: 10000 });
  const decisions = useQuery({ queryKey: ["decision-badge"], queryFn: () => api<{ decisions: { ts: string; outcome: string }[] }>("/api/decisions?limit=200"), refetchInterval: 10000 });
  useEffect(() => {
    const socket = openEvents((event) => {
      const row = event as { agent?: string; type?: string; summary?: string; ts?: string };
      const time = row.ts ? row.ts.slice(11, 19) : "";
      setTick(`${time} ${row.agent || ""}/${row.type || ""} ${row.summary || ""}`.slice(0, 160));
    });
    return () => socket.close();
  }, []);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const theme = settings.data?.theme ?? "dark";
  if (typeof document !== "undefined") document.documentElement.classList.toggle("light", theme === "light");
  const snap = status.data;
  const title = settings.data?.app_title || "JARVIS // TRADE-BREIN";
  const used = costs.data?.tokens_today ?? 0;
  const budget = costs.data?.token_budget || 1;
  const hourAgo = Date.now() - 3600_000;
  const rejected = (decisions.data?.decisions || []).filter((row) => (row.outcome === "rejected" || row.outcome === "skipped") && new Date(row.ts).getTime() >= hourAgo).length;
  const waiting = review.data?.cards?.length || 0;
  const clock = new Intl.DateTimeFormat(lang === "en" ? "en-US" : "id-ID", {
    timeZone: settings.data?.timezone || "Asia/Makassar", hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(now);

  function go(event: React.MouseEvent<HTMLAnchorElement>, to: string) {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const start = (document as Document & { startViewTransition?: (callback: () => void) => void }).startViewTransition?.bind(document);
    if (reduced || !start || event.metaKey || event.ctrlKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    document.documentElement.style.setProperty("--wipe-x", `${event.clientX}px`);
    document.documentElement.style.setProperty("--wipe-y", `${event.clientY}px`);
    start(() => navigate(to));
  }

  return (
    <div className="h-full grid" style={{ gridTemplateColumns: "220px 1fr" }}>
      <aside className="border-r border-line p-3 overflow-auto" style={{ background: "var(--panel)" }}>
        <div className="px-2 py-2 mb-3">
          <div className="text-xs text-muted">PYTHON_AI_LAB</div>
          <div className="font-semibold">JARVIS</div>
        </div>
        <nav>
          {GROUPS.map(([label, links]) => (
            <div key={label}>
              <div className="nav-label">{t(label)}</div>
              {links.map(([to, key]) => (
                <NavLink key={to} to={to} end={to === "/"} onClick={(event) => go(event, to)} className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>
                  {t(key)}
                  {to === "/kennisbank" && waiting > 0 && <span className="badge ml-2">{waiting}</span>}
                  {to === "/keputusan" && rejected > 0 && <span className="badge ml-2">{rejected}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <div className="min-w-0 flex flex-col">
        <header className="border-b border-line px-4 py-3 flex flex-wrap gap-2 items-center" style={{ background: "var(--panel)" }}>
          <strong className="mono text-sm">{title}</strong>
          <span className="pill"><StatusDot status="idle" />{snap?.mode === "demo" ? t("shell.demo") : t("shell.paper")}</span>
          {(agents.data?.agents || []).map((agent) => (
            <span key={agent.id} className="pill" title={agent.id}><StatusDot status={agent.state} /><span style={{ color: agent.color }}>{agent.id}</span></span>
          ))}
          <span className="text-xs text-muted">{t("shell.budget")} {used}/{budget}</span>
          <span className="h-2 w-24" style={{ background: "var(--surface-2)" }}><span className="block h-2" style={{ width: `${Math.min(100, (used / budget) * 100)}%`, background: "var(--accent)" }} /></span>
          <span className="text-xs text-muted">{t("shell.round")} {snap?.round ?? 0}</span>
          <span className="text-xs text-muted">{t("shell.decisions")} {snap?.decisions_today ?? 0}</span>
          <span className="text-xs text-muted">{t("shell.mode")} {(snap?.mode || "…").toUpperCase()}</span>
          <span className="text-xs text-muted">{t("shell.age")} {ageLabel(snap?.data_age_sec)}</span>
          <span className="text-xs mono ml-auto">{clock}</span>
        </header>
        <div className="ticker"><span className="ticker-track">{tick || "—"}</span></div>
        {snap?.kill_switch.active && (
          <div className="banner bad">{t("shell.kill")} {snap.kill_switch.reason} {snap.kill_switch.reset_hint}</div>
        )}
        {snap?.commission_placeholder && <div className="banner warn">{t("shell.commissionDetail")} ({snap.commission_per_lot_usd})</div>}
        {(meta.data?.gitignore_missing.length ?? 0) > 0 && (
          <div className="banner bad flex items-center gap-3">
            <span>{t("shell.gitignore")} {meta.data?.gitignore_missing.join(", ")}</span>
            <button className="btn" onClick={async () => { await api("/api/security/fix-gitignore", { method: "POST" }); meta.refetch(); }}>{t("shell.gitignoreFix")}</button>
          </div>
        )}
        {status.isError && !snap && <div className="banner bad">{t("shell.backend")}</div>}
        <main className="flex-1 overflow-auto p-4">
          <div key={location.pathname} className="page-enter">
            <Outlet context={{ refresh }} />
          </div>
        </main>
        <p className="px-4 py-2 text-xs text-muted">{t("shell.noOrders")}</p>
      </div>
    </div>
  );
}
