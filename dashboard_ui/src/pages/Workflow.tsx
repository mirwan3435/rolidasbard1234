import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "../api/client";
import { type NodeState, type Status, useSettings } from "../components/Layout";
import { fmtTime, statusColor, statusLabel } from "../lib/format";
import { useUi } from "../store/ui";
import { useI18n } from "../i18n";

const INFO: Record<string, { title: string; agent: string; note?: string; summary: string; input: string; output: string }> = {
  mt5: { title: "MT5 Feed", agent: "SYSTEM", summary: "Membaca tick. Tidak ada pengiriman order dari dashboard.", input: "Terminal MT5 (read-only)", output: "Harga, spread, waktu tick" },
  validator: { title: "Validator Data", agent: "DATA", summary: "Cek candle kosong, gap, dan jam pasar sebelum analisis.", input: "OHLC + spread", output: "valid / alasan gagal" },
  scope: { title: "SCOPE", agent: "SCOPE", summary: "Cari order block, FVG, liquidity pool, BOS/CHOCH. Skor 0-100 adalah skor zona, bukan probabilitas profit.", input: "Candle tervalidasi", output: "Daftar zona + skor" },
  whales: { title: "WHALES", agent: "WHALES", summary: "Konteks jejak volume/aliran besar. Bukan keputusan masuk.", input: "Volume", output: "Catatan konteks" },
  dxy: { title: "DXYm", agent: "DATA", summary: "Konteks arah USD saja, bukan simbol entry. Bisa dimatikan di halaman Simbol.", input: "Tick DXYm", output: "Bias USD" },
  debate: { title: "DEBATE", agent: "DEBATE", summary: "Beberapa sudut pandang AI membahas setup. Keluaran hanya usulan.", input: "Zona, whales, DXY", output: "Argumen JSON" },
  core: { title: "Grok Core", agent: "CORE", summary: "Menggabungkan usulan agent lain. Tidak mengubah batas RISK.", input: "Keluaran agent", output: "Usulan keputusan" },
  risk: { title: "RISK", agent: "RISK", note: "Deterministik, tanpa AI", summary: "Kill-switch, data, drawdown, arah stop, spread, lot, eksposur. Fail-closed.", input: "Usulan + spesifikasi simbol", output: "Setuju/tolak + alasan" },
  exec: { title: "EXEC", agent: "EXEC", summary: "Paper trading. Saldo virtual, bukan order MT5.", input: "Keputusan RISK", output: "Posisi virtual" },
  kill: { title: "Kill-Switch", agent: "", summary: "Hanya ditampilkan. Reset manual: hapus logs\\KILL_SWITCH.lock. Tidak ada tombol reset.", input: "File lock", output: "Aktif / tidak" },
};

const BASE: Record<string, { x: number; y: number }> = {
  mt5: { x: 0, y: 140 },
  validator: { x: 260, y: 140 },
  scope: { x: 530, y: 20 },
  whales: { x: 530, y: 250 },
  dxy: { x: 260, y: 360 },
  debate: { x: 820, y: 150 },
  core: { x: 1100, y: 150 },
  risk: { x: 1380, y: 150 },
  kill: { x: 1380, y: 370 },
  exec: { x: 1660, y: 150 },
};

const EDGE_DEFS = [
  ["mt5", "validator"],
  ["validator", "scope"],
  ["validator", "whales"],
  ["scope", "debate"],
  ["whales", "debate"],
  ["dxy", "debate"],
  ["debate", "core"],
  ["core", "risk"],
  ["risk", "exec"],
  ["kill", "risk"],
];

function Spark({ values }: { values: number[] }) {
  const max = Math.max(1, ...values);
  const width = 180;
  const height = 26;
  const step = width / Math.max(1, values.length - 1);
  const d = values.map((value, index) => `${index === 0 ? "M" : "L"} ${index * step} ${height - (value / max) * (height - 2)}`).join(" ");
  return (
    <svg width={width} height={height} aria-hidden>
      <path d={d} stroke="var(--run)" fill="none" strokeWidth="1.6" />
    </svg>
  );
}

function TradeNode({ data }: NodeProps) {
  const node = data as unknown as { title: string; status: string; updated: string; latency: string; errors: number; spark: number[]; note?: string };
  const solid = node.status === "error";
  return (
    <div className={`node-card ${solid ? "bad" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="flex justify-between gap-2">
        <strong>{node.title}</strong>
        <span className="badge" style={{ color: statusColor(node.status) }}>{statusLabel(node.status)}</span>
      </div>
      <div className="text-muted mt-1">{node.updated} · {node.latency} · err {node.errors}</div>
      <Spark values={node.spark || []} />
      {node.note && <div className="mt-1" style={{ color: "var(--warn)" }}>{node.note}</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { trade: TradeNode };

export function WorkflowPage() {
  return (
    <ReactFlowProvider>
      <WorkflowCanvas />
    </ReactFlowProvider>
  );
}

function WorkflowCanvas() {
  const { t } = useI18n();
  const settings = useSettings();
  const tz = settings.data?.timezone ?? "Asia/Makassar";
  const refresh = settings.data?.refresh_ms ?? 2000;
  const symbol = useUi((s) => s.symbol);
  const setSymbol = useUi((s) => s.setSymbol);
  const setPositions = useUi((s) => s.setPositions);
  const [layout] = useState(() => useUi.getState().positions);
  const [selected, setSelected] = useState("risk");
  const [tab, setTab] = useState("ringkasan");
  const [symbolEvent, setSymbolEvent] = useState("");
  const theme = settings.data?.theme ?? "dark";

  const status = useQuery({
    queryKey: ["status", symbol],
    queryFn: () => api<Status>(`/api/status${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`),
    refetchInterval: refresh,
  });

  const initialNodes = useMemo<Node[]>(() => Object.keys(INFO).map((id) => ({
    id,
    type: "trade",
    position: layout[id] || BASE[id],
    data: { title: INFO[id].title, status: "idle", updated: "—", latency: "—", errors: 0, spark: [], note: INFO[id].note },
    draggable: true,
  })), []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(EDGE_DEFS.map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    animated: false,
  })));

  useEffect(() => {
    const nodesState = status.data?.nodes;
    if (!nodesState) return;
    setNodes((current) => current.map((node) => {
      const live = nodesState[node.id] as NodeState | undefined;
      return {
        ...node,
        data: {
          ...node.data,
          title: INFO[node.id].title,
          note: INFO[node.id].note,
          status: live?.status || "idle",
          updated: fmtTime(live?.updated_at, tz),
          latency: live?.latency_ms != null ? `${Math.round(live.latency_ms)} ms` : "—",
          errors: live?.errors_1h ?? 0,
          spark: live?.spark || [],
        },
      };
    }));
    setEdges((current) => current.map((edge) => ({ ...edge, animated: Boolean(status.data?.flowing) })));
  }, [status.data, setNodes, setEdges, tz]);

  const events = useQuery({
    queryKey: ["node-events", selected, symbolEvent],
    queryFn: () => {
      const agent = INFO[selected]?.agent;
      const params = new URLSearchParams({ limit: "50" });
      if (agent && selected !== "dxy") params.set("agent", agent);
      if (selected === "dxy") params.set("symbol", "DXYm");
      else if (symbolEvent) params.set("symbol", symbolEvent);
      return api<{ events: Record<string, unknown>[] }>(`/api/events?${params.toString()}`);
    },
    refetchInterval: refresh,
  });

  const info = INFO[selected];
  const live = status.data?.nodes?.[selected];

  return (
    <div className="h-[calc(100vh-140px)] min-h-[640px] grid gap-3" style={{ gridTemplateColumns: "1fr 380px" }}>
      <section className="card min-w-0 flex flex-col">
        <div className="flex items-center gap-3 p-3 border-b border-line">
          <label htmlFor="symbol-filter">{t("wf.symbol")}</label>
          <select id="symbol-filter" className="field" style={{ width: 220 }} value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            <option value="">{t("wf.allSymbols")}</option>
            {(status.data?.symbols || []).map((row) => (
              <option key={row.name} value={row.name}>{row.name}</option>
            ))}
          </select>
          <span className="text-sm text-muted">{t("wf.drag")}</span>
        </div>
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            colorMode={theme === "light" ? "light" : "dark"}
            onNodesChange={(changes) => {
              onNodesChange(changes.filter((change) => change.type !== "remove"));
            }}
            onNodeDragStop={(_, _node, all) => {
              const positions: Record<string, { x: number; y: number }> = {};
              all.forEach((node) => { positions[node.id] = node.position; });
              setPositions(positions);
            }}
            onEdgesChange={onEdgesChange}
            deleteKeyCode={null}
            nodesConnectable={false}
            fitView
            onNodeClick={(_, node) => { setSelected(node.id); setTab("ringkasan"); }}
            proOptions={{ hideAttribution: true }}
          >
            <MiniMap />
            <Controls />
            <Background />
          </ReactFlow>
        </div>
      </section>
      <aside className="card p-3 overflow-auto">
        <h2 className="text-lg font-semibold">{info.title}</h2>
        <div className="text-sm mt-1" style={{ color: statusColor(live?.status) }}>{statusLabel(live?.status)} · {live?.last_summary || t("wf.noActivity")}</div>
        <div className="flex flex-wrap gap-2 my-3">
          {[["ringkasan", "wf.summary"], ["aktivitas", "wf.activity"], ["io", "wf.io"], ["konfigurasi", "wf.config"], ["kesehatan", "wf.health"]].map(([name, key]) => (
            <button key={name} className={`btn ${tab === name ? "primary" : ""}`} onClick={() => setTab(name)}>{t(key as "wf.summary")}</button>
          ))}
        </div>
        {tab === "ringkasan" && (
          <div className="space-y-2 text-sm">
            <p>{info.summary}</p>
            <p><strong>Input.</strong> {info.input}</p>
            <p><strong>Output.</strong> {info.output}</p>
          </div>
        )}
        {tab === "aktivitas" && (
          <div>
            <label className="text-sm" htmlFor="ev-symbol">{t("wf.filter")}</label>
            <select id="ev-symbol" className="field my-2" value={symbolEvent} onChange={(e) => setSymbolEvent(e.target.value)}>
              <option value="">{t("common.all")}</option>
              {(status.data?.symbols || []).map((row) => <option key={row.name}>{row.name}</option>)}
            </select>
            <ul className="space-y-2 text-sm">
              {(events.data?.events || []).length === 0 && <li className="text-muted">{t("wf.noEvent")}</li>}
              {(events.data?.events || []).map((event, index) => (
                <li key={index} className="border-b border-line pb-1">
                  <div className="text-muted">{fmtTime(String(event.ts || ""), tz)} · {String(event.symbol || "—")}</div>
                  <div>{String(event.summary || "")}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
        {tab === "io" && <IoBlock event={events.data?.events?.[0]} />}
        {tab === "konfigurasi" && (
          <div className="text-sm space-y-2">
            {selected === "risk" && <a className="btn" href="/config">{t("wf.openConfig")}</a>}
            {["debate", "core", "whales"].includes(selected) && <a className="btn" href="/skill">{t("wf.openSkill")}</a>}
            {selected === "scope" && <p>{t("wf.scopeLocked")}</p>}
            {selected === "kill" && <p>{t("wf.killLocked")}</p>}
            {!["risk", "debate", "core", "whales", "scope", "kill"].includes(selected) && <p>{t("wf.noParam")}</p>}
          </div>
        )}
        {tab === "kesehatan" && (
          <div className="text-sm space-y-2">
            <p>{t("wf.errors")}: {live?.errors_1h ?? 0}</p>
            <p>{t("wf.latency")}: {live?.latency_ms != null ? `${live.latency_ms} ms` : "—"}</p>
            <p>{t("wf.last")}: {live?.last_summary || "—"}</p>
            <Spark values={live?.spark || []} />
          </div>
        )}
      </aside>
    </div>
  );
}

function IoBlock({ event }: { event?: Record<string, unknown> }) {
  const data = (event?.data && typeof event.data === "object" ? event.data : {}) as Record<string, unknown>;
  const input = JSON.stringify(data.input ?? data, null, 2);
  const output = JSON.stringify(data.output ?? { summary: event?.summary ?? null }, null, 2);
  return (
    <div className="text-sm space-y-2">
      <JsonBox title="Input" text={input} />
      <JsonBox title="Output" text={output} />
    </div>
  );
}

function JsonBox({ title, text }: { title: string; text: string }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button className="btn" onClick={() => setOpen((v) => !v)}>{open ? t("common.close") : t("common.open")} {title}</button>
      <button className="btn ml-2" onClick={() => navigator.clipboard.writeText(text)}>{t("common.copy")}</button>
      {open && <pre className="mono text-xs mt-2 whitespace-pre-wrap">{text}</pre>}
    </div>
  );
}
