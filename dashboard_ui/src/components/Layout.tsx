import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, openEvents } from "../api/client";
import { useI18n } from "../i18n";
import type { DictKey } from "../i18n/id";
import { ageLabel } from "../lib/format";
import { BottomNav, Sidebar, type SideItem } from "./Sidebar";
import { Emblem } from "./ui/Emblem";
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

function eventLine(row: { ts?: string; agent?: string; type?: string; summary?: string }) {
  const time = row.ts ? row.ts.slice(11, 19) : "";
  const text = `${time} ${row.agent || ""}/${row.type || ""} ${row.summary || ""}`.replace(/\s+/g, " ").trim();
  return text.length > 1 ? text.slice(0, 180) : "";
}

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
  const [tape, setTape] = useState<string[]>([]);
  const pending = useRef<string[]>([]);
  const tapeRef = useRef<string[]>([]);
  const [now, setNow] = useState(() => new Date());
  const [shellIn, setShellIn] = useState(false);
  const [photo, setPhoto] = useState(false);
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
  function pushLine(line: string, immediate: boolean) {
    const next = [line, ...pending.current.filter((item) => item !== line)].slice(0, 40);
    pending.current = next;
    if (immediate || tapeRef.current.length === 0) {
      tapeRef.current = next;
      setTape(next);
    }
  }
  useEffect(() => {
    let cancelled = false;
    api<{ events: { ts?: string; agent?: string; type?: string; summary?: string }[] }>("/api/events?limit=24")
      .then((body) => {
        if (cancelled) return;
        const lines = (body.events || []).map(eventLine).filter(Boolean);
        pending.current = lines;
        if (tapeRef.current.length === 0 && lines.length) {
          tapeRef.current = lines;
          setTape(lines);
        }
      })
      .catch(() => undefined);
    const socket = openEvents((event) => {
      const line = eventLine(event as { agent?: string; type?: string; summary?: string; ts?: string });
      if (line) pushLine(line, false);
    });
    return () => {
      cancelled = true;
      socket.close();
    };
  }, []);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    const img = new Image();
    img.onload = () => setPhoto(true);
    img.onerror = () => setPhoto(false);
    img.src = "/bg.jpg";
  }, []);
  useEffect(() => {
    const onDone = () => setShellIn(true);
    window.addEventListener("jarvis-splash-done", onDone);
    return () => window.removeEventListener("jarvis-splash-done", onDone);
  }, []);
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

  const items: SideItem[] = GROUPS.flatMap(([, links]) => links.map(([to, key]) => {
    const count = to === "/kennisbank" ? waiting : to === "/keputusan" ? rejected : 0;
    return { to, label: t(key), badge: count > 0 ? count : undefined };
  }));

  return (
    <div
      className={`relative h-full min-h-screen bg-cover bg-center bg-fixed ${photo ? "" : "bg-fallback"}`}
      style={{
        backgroundColor: "#f2f7fe",
        backgroundImage: photo ? "url('/bg.jpg')" : undefined,
      }}
    >
    <div className={`relative z-10 h-full${shellIn ? " shell-in" : ""}`}>
      <Sidebar items={items} onNavigate={go} />
      <BottomNav items={items} onNavigate={go} />
      <div className="shell-bars flex h-full min-w-0 flex-col pb-24 md:pb-0">
        <header className="glass-bar px-4 py-3 flex flex-wrap gap-2 items-center">
          <Emblem size={18} state={snap?.kill_switch.active ? "error" : "idle"} alarm={!!snap?.kill_switch.active} />
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
        <div className="ticker glass-bar">
          <span
            className="ticker-track"
            style={{ animationDuration: `${Math.max(28, tape.join(" ").length / 6)}s` }}
            onAnimationIteration={() => {
              tapeRef.current = pending.current;
              setTape(pending.current);
            }}
          >
            {(tape.length ? tape : ["—"]).join("    ·    ")}
          </span>
        </div>
        {snap?.kill_switch.active && (
          <div className="banner bad flex items-center gap-2"><Emblem size={22} state="error" alarm />{t("shell.kill")} {snap.kill_switch.reason} {snap.kill_switch.reset_hint}</div>
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
    </div>
  );
}
