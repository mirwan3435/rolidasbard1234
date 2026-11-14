import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "../api/client";
import { GrokMark } from "../components/ui/GrokMark";
import { Drawer, Panel, Spinner } from "../components/ui/Panel";
import { useI18n } from "../i18n";
import { fmtTime, lineDiff } from "../lib/format";
import { useSettings } from "../components/Layout";

type AgentRow = { name: string; locked: boolean; reason?: string; enabled?: boolean; model?: string; tier?: string; llm?: boolean; color?: string; label?: string; summary?: string; params_editable?: boolean };
type AgentDoc = {
  name: string; locked: boolean; reason?: string; enabled?: boolean; model?: string; temperature?: number; max_tokens?: number; timeout_sec?: number;
  system_prompt?: string; output_schema?: Record<string, unknown>; versions?: { n: number; ts: string; note: string }[];
  variables?: string[]; presets?: string[]; model_note?: string; params?: Record<string, number>; params_editable?: boolean;
  label?: string; tier?: string; llm?: boolean; color?: string; skill?: { summary?: string };
};
type Status = { agents: { id: string; state: string; events_today: number; color: string }[] };

const formSchema = z.object({
  temperature: z.number().min(0).max(1.5),
  max_tokens: z.number().int().min(64).max(4000),
  timeout_sec: z.number().int().min(5).max(120),
  model: z.string().max(80),
  system_prompt: z.string().max(20000),
});

const VERDICT = `{
  "signal_id": "string",
  "verdict": "accept | reduce | reject",
  "score_adjust": "integer -10..0",
  "reasons": "max 5 strings",
  "risk_flags": "news | low_liquidity | htf_conflict | overextended | correlation | spread | other",
  "confidence": "0..1"
}`;

export function SkillsPage() {
  const { t } = useI18n();
  const list = useQuery({ queryKey: ["agents"], queryFn: () => api<{ agents: AgentRow[] }>("/api/agents") });
  const status = useQuery({ queryKey: ["agent-status"], queryFn: () => api<Status>("/api/agents/status") });
  const [name, setName] = useState<string | null>(null);
  const agents = list.data?.agents || [];
  const live = Object.fromEntries((status.data?.agents || []).map((agent) => [agent.id, agent]));
  if (list.isLoading) return <Spinner />;
  const tierA = agents.filter((agent) => agent.tier !== "B");
  const tierB = agents.filter((agent) => agent.tier === "B");
  return (
    <div className="space-y-4">
      <Panel title={t("skill.tierA")} source="real">
        <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))" }}>
          {tierA.map((agent) => <Card key={agent.name} agent={agent} live={live[agent.name]} onEdit={() => setName(agent.name)} />)}
        </div>
      </Panel>
      <Panel title={t("skill.tierB")} source="real">
        <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))" }}>
          {tierB.map((agent) => <Card key={agent.name} agent={agent} live={live[agent.name]} onEdit={() => setName(agent.name)} />)}
        </div>
      </Panel>
      {name && <AgentEditor name={name} onClose={() => setName(null)} />}
    </div>
  );
}

function Card({ agent, live, onEdit }: { agent: AgentRow; live?: { state: string; events_today: number }; onEdit: () => void }) {
  const { t } = useI18n();
  const state = live?.state === "working" ? "active" : live?.state === "error" ? "error" : "idle";
  return (
    <article className="card p-3">
      <div className="flex items-center gap-2">
        <GrokMark state={state} color={agent.color} />
        <strong>{agent.label || agent.name}</strong>
      </div>
      <p className="text-xs text-muted mt-1">{agent.tier} · {agent.llm ? t("skill.llm") : t("skill.det")}</p>
      <p className="text-sm mt-1">{agent.summary}</p>
      <p className="text-xs text-muted">{live?.events_today ?? 0} {t("skill.events")}</p>
      <button className="btn mt-2" onClick={onEdit}>{t("skill.edit")}</button>
    </article>
  );
}

function AgentEditor({ name, onClose }: { name: string; onClose: () => void }) {
  const { t } = useI18n();
  const settings = useSettings();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["agent", name], queryFn: () => api<AgentDoc>(`/api/agents/${name}`) });
  const keys = useQuery({ queryKey: ["keys"], queryFn: () => api<{ slots: { slot: string; filled: boolean }[] }>("/api/keys") });
  const doc = query.data;
  const [enabled, setEnabled] = useState(true);
  const [model, setModel] = useState("");
  const [temperature, setTemperature] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(800);
  const [timeoutSec, setTimeoutSec] = useState(30);
  const [prompt, setPrompt] = useState("");
  const [schemaText, setSchemaText] = useState("{}");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [params, setParams] = useState<Record<string, number>>({});
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(0);
  const [diff, setDiff] = useState<{ kind: string; text: string }[]>([]);
  const [testOut, setTestOut] = useState("");

  useEffect(() => {
    if (!doc || doc.locked) return;
    setEnabled(Boolean(doc.enabled));
    setModel(doc.model || "");
    setTemperature(doc.temperature ?? 0.3);
    setMaxTokens(doc.max_tokens ?? 800);
    setTimeoutSec(doc.timeout_sec ?? 30);
    setPrompt(doc.system_prompt || "");
    setSchemaText(JSON.stringify(doc.output_schema || {}, null, 2));
  }, [doc]);
  useEffect(() => { if (doc?.params) setParams(doc.params); }, [doc]);

  if (!doc) return <Drawer title={name} onClose={onClose}><Spinner /></Drawer>;
  const keyReady = keys.data?.slots.some((slot) => slot.slot === "XAI_API_KEY" && slot.filled);
  const numeric = !doc.llm && (doc.params_editable || doc.locked);

  async function saveParams() {
    setMessage("");
    try {
      await api(`/api/agents/${name}/params`, { method: "PUT", body: JSON.stringify({ params, note }) });
      setMessage(t("skill.saved"));
      client.invalidateQueries({ queryKey: ["agent", name] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("common.failed"));
    }
  }

  async function save() {
    setMessage("");
    const parsed = formSchema.safeParse({ temperature, max_tokens: maxTokens, timeout_sec: timeoutSec, model, system_prompt: prompt });
    if (!parsed.success) {
      setMessage(parsed.error.issues.map((issue) => issue.message).join("; "));
      return;
    }
    let output_schema: Record<string, unknown>;
    try {
      output_schema = JSON.parse(schemaText);
      if (typeof output_schema !== "object" || output_schema === null || Array.isArray(output_schema)) throw new Error("objek");
    } catch {
      setMessage(t("skill.schema"));
      return;
    }
    try {
      await api(`/api/agents/${name}`, {
        method: "PUT",
        body: JSON.stringify({ enabled, model, temperature, max_tokens: maxTokens, timeout_sec: timeoutSec, system_prompt: prompt, output_schema, note }),
      });
      setNote("");
      setMessage(t("skill.saved"));
      client.invalidateQueries({ queryKey: ["agent", name] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("common.failed"));
    }
  }

  async function applyPreset(preset: string) {
    const result = await api<{ text: string }>(`/api/agents/${name}/presets/${encodeURIComponent(preset)}`);
    setPrompt(result.text);
  }
  async function showDiff() {
    if (!left || !right) return;
    const [a, b] = await Promise.all([
      api<{ snapshot: { system_prompt: string } }>(`/api/agents/${name}/versions/${left}`),
      api<{ snapshot: { system_prompt: string } }>(`/api/agents/${name}/versions/${right}`),
    ]);
    setDiff(lineDiff(a.snapshot?.system_prompt || "", b.snapshot?.system_prompt || ""));
  }
  async function rollback() {
    if (!left) return;
    await api(`/api/agents/${name}/rollback`, { method: "POST", body: JSON.stringify({ version: left }) });
    setMessage(t("skill.saved"));
    client.invalidateQueries({ queryKey: ["agent", name] });
  }
  async function testPrompt() {
    setTestOut("");
    try {
      const result = await api<Record<string, unknown>>(`/api/agents/${name}/test`, { method: "POST" });
      setTestOut(JSON.stringify(result, null, 2));
    } catch (error) {
      setTestOut(error instanceof Error ? error.message : t("common.failed"));
    }
  }

  return (
    <Drawer title={doc.label || name} onClose={onClose}>
      {(doc.locked && !doc.params_editable) && <p>{doc.reason}</p>}
      {(doc.locked && !doc.params_editable) && <p className="text-sm text-muted mt-2">{t("skill.readonly")}</p>}
      {numeric && doc.params_editable && (
        <div className="space-y-2">
          <p className="text-sm">{doc.reason || doc.model_note}</p>
          {Object.entries(params).map(([key, value]) => (
            <label key={key} className="block text-sm">{key}
              <input className="field" type="number" value={value} onChange={(e) => setParams({ ...params, [key]: Number(e.target.value) })} />
            </label>
          ))}
          <button className="btn primary" onClick={saveParams}>{t("common.save")}</button>
        </div>
      )}
      {doc.llm && (
        <div className="space-y-2">
          <p className="text-sm text-muted">{doc.model_note}</p>
          <label className="flex gap-2 items-center"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /> {t("skill.active")}</label>
          <label className="block text-sm">{t("skill.model")}<input className="field" value={model} onChange={(e) => setModel(e.target.value)} /></label>
          <label className="block text-sm">{t("skill.temperature")}<input className="field" type="number" step="0.1" value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} /></label>
          <label className="block text-sm">{t("skill.tokens")}<input className="field" type="number" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} /></label>
          <label className="block text-sm">{t("skill.timeout")}<input className="field" type="number" value={timeoutSec} onChange={(e) => setTimeoutSec(Number(e.target.value))} /></label>
          <div className="flex flex-wrap gap-2">
            {(doc.presets || []).map((preset) => <button key={preset} className="btn" onClick={() => applyPreset(preset)}>{t("skill.preset")} {preset}</button>)}
          </div>
          <div className="flex flex-wrap gap-2">
            {(doc.variables || []).map((variable) => (
              <button key={variable} className="btn" onClick={() => setPrompt((text) => `${text}${text.endsWith(" ") || text.length === 0 ? "" : " "}${variable}`)}>{t("skill.insert")} {variable}</button>
            ))}
          </div>
          <label className="block text-sm">{t("skill.prompt")}<textarea className="field min-h-40" value={prompt} onChange={(e) => setPrompt(e.target.value)} /></label>
          <label className="block text-sm">{t("skill.schema")}<textarea className="field min-h-28 mono" value={schemaText} onChange={(e) => setSchemaText(e.target.value)} /></label>
          <p className="text-xs">{t("skill.verdict")}</p>
          <pre className="mono text-xs whitespace-pre-wrap">{VERDICT}</pre>
          <label className="block text-sm">{t("skill.versionNote")}<input className="field" value={note} onChange={(e) => setNote(e.target.value)} /></label>
          <div className="flex gap-2">
            <button className="btn primary" onClick={save}>{t("skill.save")}</button>
            <button className="btn" disabled={!keyReady || !model} onClick={testPrompt}>{t("skill.test")}</button>
          </div>
          {!keyReady && <p className="text-sm text-muted">{t("skill.needKey")}</p>}
          <h3 className="font-semibold">{t("skill.history")}</h3>
          <ul className="text-sm">
            {(doc.versions || []).map((version) => <li key={version.n}>v{version.n} · {fmtTime(version.ts, settings.data?.timezone)} · {version.note || "—"}</li>)}
          </ul>
          <div className="flex gap-2 items-center">
            <select className="field" value={left} onChange={(e) => setLeft(Number(e.target.value))} aria-label="A">
              <option value={0}>A</option>
              {(doc.versions || []).map((version) => <option key={version.n} value={version.n}>v{version.n}</option>)}
            </select>
            <select className="field" value={right} onChange={(e) => setRight(Number(e.target.value))} aria-label="B">
              <option value={0}>B</option>
              {(doc.versions || []).map((version) => <option key={version.n} value={version.n}>v{version.n}</option>)}
            </select>
            <button className="btn" onClick={showDiff}>{t("skill.diff")}</button>
            <button className="btn" disabled={!left} onClick={rollback}>{t("skill.rollback")}</button>
          </div>
          {diff.length > 0 && (
            <pre className="mono text-xs whitespace-pre-wrap">
              {diff.map((row, index) => <div key={index}>{row.kind === "add" ? "+ " : row.kind === "del" ? "- " : "  "}{row.text}</div>)}
            </pre>
          )}
        </div>
      )}
      {message && <p className="mt-2">{message}</p>}
      {testOut && <pre className="mono text-xs whitespace-pre-wrap">{testOut}</pre>}
    </Drawer>
  );
}
