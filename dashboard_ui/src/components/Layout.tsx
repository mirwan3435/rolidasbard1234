import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import { ageLabel } from "../lib/format";

const LINKS = [
  ["/", "Workflow"],
  ["/simbol", "Simbol"],
  ["/risk", "RISK"],
  ["/paper", "Paper"],
  ["/kunci", "API Key"],
  ["/skill", "Skill"],
  ["/config", "Config"],
  ["/log", "Log"],
  ["/kesehatan", "Kesehatan"],
  ["/pengaturan", "Pengaturan"],
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
    queryFn: () => api<{ theme: "dark" | "light"; timezone: string; refresh_ms: number; log_retention_days: number; token_usd_per_million: number }>("/api/settings"),
  });
}

export function Layout() {
  const settings = useSettings();
  const refresh = settings.data?.refresh_ms ?? 2000;
  const status = useQuery({
    queryKey: ["status-header"],
    queryFn: () => api<Status>("/api/status"),
    refetchInterval: refresh,
  });
  const meta = useQuery({
    queryKey: ["meta"],
    queryFn: () => api<{ gitignore_missing: string[] }>("/api/meta"),
    refetchInterval: 10000,
  });
  const theme = settings.data?.theme ?? "dark";
  if (typeof document !== "undefined") document.documentElement.classList.toggle("light", theme === "light");
  const snap = status.data;

  return (
    <div className="h-full grid" style={{ gridTemplateColumns: "220px 1fr" }}>
      <aside className="border-r border-line p-3 overflow-auto" style={{ background: "var(--panel)" }}>
        <div className="px-2 py-2 mb-3">
          <div className="text-xs text-muted">PYTHON_AI_LAB</div>
          <div className="font-semibold">5 Agent + Grok</div>
        </div>
        <nav className="space-y-1">
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="min-w-0 flex flex-col">
        <header className="border-b border-line px-4 py-3 flex flex-wrap gap-3 items-center" style={{ background: "var(--panel)" }}>
          <Pill
            label="Mode"
            value={(snap?.mode || "…").toUpperCase()}
            tone={snap?.mode === "live" ? "ok" : "run"}
          />
          <Pill label="MT5" value={snap ? (snap.mt5_connected ? "terhubung" : "tidak terhubung") : "…"} />
          <Pill label="Usia data" value={ageLabel(snap?.data_age_sec)} />
          <Pill label="Equity" value={snap ? snap.equity.toFixed(2) : "…"} />
          <span className="text-xs text-muted ml-auto">Paper trading. Dashboard tidak mengirim order.</span>
        </header>
        {snap?.kill_switch.active && (
          <div className="banner bad">
            KILL-SWITCH AKTIF. {snap.kill_switch.reason || "Alasan tidak terbaca."} {snap.kill_switch.reset_hint}
          </div>
        )}
        {snap?.commission_placeholder && (
          <div className="banner warn">
            Komisi masih placeholder {snap.commission_per_lot_usd} USD/lot. Cek komisi asli akun, lalu konfirmasi di halaman Config.
          </div>
        )}
        {(meta.data?.gitignore_missing.length ?? 0) > 0 && (
          <div className="banner bad flex items-center gap-3">
            <span>.gitignore belum menutup: {meta.data?.gitignore_missing.join(", ")}</span>
            <button
              className="btn"
              onClick={async () => {
                await api("/api/security/fix-gitignore", { method: "POST" });
                meta.refetch();
              }}
            >
              Tambahkan sekarang
            </button>
          </div>
        )}
        {status.isError && !snap && (
          <div className="banner bad">Backend tidak terhubung. Jalankan <span className="mono">.\scripts\run_dashboard.ps1</span></div>
        )}
        <main className="flex-1 overflow-auto p-4">
          <Outlet context={{ refresh }} />
        </main>
      </div>
    </div>
  );
}

function Pill({ label, value, tone }: { label: string; value: string; tone?: "ok" | "run" }) {
  return (
    <div className="text-sm">
      <span className="text-muted mr-1">{label}</span>
      <strong style={tone ? { color: tone === "ok" ? "var(--ok)" : "var(--run)" } : undefined}>{value}</strong>
    </div>
  );
}
