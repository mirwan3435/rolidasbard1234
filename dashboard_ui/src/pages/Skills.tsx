import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "../api/client";
import { fmtTime, lineDiff } from "../lib/format";
import { useSettings } from "../components/Layout";

type AgentRow = { name: string; locked: boolean; reason?: string; enabled?: boolean; model?: string };
type AgentDoc = {
  name: string;
  locked: boolean;
  reason?: string;
  enabled: boolean;
  model: string;
  temperature: number;
  max_tokens: number;
  timeout_sec: number;
  system_prompt: string;
  output_schema: Record<string, unknown>;
  versions: { n: number; ts: string; note: string }[];
  variables: string[];
  presets: string[];
  model_note: string;
};

const formSchema = z.object({
  temperature: z.number().min(0).max(1.5),
  max_tokens: z.number().int().min(64).max(4000),
  timeout_sec: z.number().int().min(5).max(120),
  model: z.string().max(80),
  system_prompt: z.string().max(20000),
});

export function SkillsPage() {
  const list = useQuery({ queryKey: ["agents"], queryFn: () => api<{ agents: AgentRow[]; variables: string[] }>("/api/agents") });
  const [name, setName] = useState("DEBATE");
  const agents = list.data?.agents || [];
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "220px 1fr" }}>
      <aside className="card p-2">
        {agents.map((agent) => (
          <button key={agent.name} className={`side-link w-full text-left ${name === agent.name ? "active" : ""}`} onClick={() => setName(agent.name)}>
            {agent.name} {agent.locked ? "· terkunci" : ""}
          </button>
        ))}
      </aside>
      <AgentEditor name={name} />
    </div>
  );
}

function AgentEditor({ name }: { name: string }) {
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
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(0);
  const [diff, setDiff] = useState<{ kind: string; text: string }[]>([]);
  const [testOut, setTestOut] = useState("");

  useEffect(() => {
    if (!doc || doc.locked) return;
    setEnabled(doc.enabled);
    setModel(doc.model || "");
    setTemperature(doc.temperature);
    setMaxTokens(doc.max_tokens);
    setTimeoutSec(doc.timeout_sec);
    setPrompt(doc.system_prompt || "");
    setSchemaText(JSON.stringify(doc.output_schema || {}, null, 2));
  }, [doc]);

  if (query.isLoading) return <div className="skeleton h-40" />;
  if (!doc) return <p>Agent tidak terbaca.</p>;
  if (doc.locked) {
    return (
      <section className="card p-4">
        <h2 className="text-xl font-semibold">{doc.name} terkunci</h2>
        <p className="mt-2">{doc.reason}</p>
        <p className="text-sm text-muted mt-2">Tidak ada editor prompt. Output AI lain tetap hanya usulan; yang memutuskan adalah RISK.</p>
      </section>
    );
  }

  const keyReady = keys.data?.slots.some((slot) => slot.slot === "XAI_API_KEY" && slot.filled);
  const tokens = Math.ceil(prompt.length / 4);

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
      setMessage("Skema keluaran harus objek JSON.");
      return;
    }
    try {
      await api(`/api/agents/${name}`, {
        method: "PUT",
        body: JSON.stringify({ enabled, model, temperature, max_tokens: maxTokens, timeout_sec: timeoutSec, system_prompt: prompt, output_schema, note }),
      });
      setNote("");
      setMessage("Versi baru tersimpan. Sistem trading membaca skill saat mulai sesi atau reload.");
      client.invalidateQueries({ queryKey: ["agent", name] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Gagal simpan");
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
    setMessage(`Rollback ke v${left} disimpan sebagai versi baru.`);
    client.invalidateQueries({ queryKey: ["agent", name] });
  }

  async function testPrompt() {
    setTestOut("");
    try {
      const result = await api<Record<string, unknown>>(`/api/agents/${name}/test`, { method: "POST" });
      setTestOut(JSON.stringify(result, null, 2));
    } catch (error) {
      setTestOut(error instanceof Error ? error.message : "Tes gagal");
    }
  }

  return (
    <section className="card p-4 space-y-3">
      <h2 className="text-xl font-semibold">{name}</h2>
      <p className="text-sm text-muted">{doc.model_note} Prompt tidak boleh menjadi jalur mengubah RISK. Keluaran diperlakukan sebagai usulan.</p>
      <label className="flex gap-2 items-center"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /> Agent aktif</label>
      <label className="block text-sm">Model
        <input className="field" value={model} onChange={(e) => setModel(e.target.value)} placeholder="lihat dokumentasi xAI" />
      </label>
      <div className="grid grid-cols-3 gap-2">
        <label className="text-sm">Temperature
          <input className="field" type="number" step="0.1" value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} />
        </label>
        <label className="text-sm">Max tokens
          <input className="field" type="number" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} />
        </label>
        <label className="text-sm">Timeout (detik)
          <input className="field" type="number" value={timeoutSec} onChange={(e) => setTimeoutSec(Number(e.target.value))} />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        {(doc.presets || []).map((preset) => (
          <button key={preset} className="btn" onClick={() => applyPreset(preset)}>Preset {preset}</button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {(doc.variables || []).map((variable) => (
          <button key={variable} className="btn" onClick={() => setPrompt((text) => `${text}${text.endsWith(" ") || text.length === 0 ? "" : " "}${variable}`)}>Sisipkan {variable}</button>
        ))}
      </div>
      <label className="block text-sm">System prompt / skill
        <textarea className="field min-h-40" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      </label>
      <p className="text-xs text-muted">{prompt.length} karakter · perkiraan {tokens} token</p>
      <label className="block text-sm">Skema keluaran JSON
        <textarea className="field min-h-28 mono" value={schemaText} onChange={(e) => setSchemaText(e.target.value)} />
      </label>
      <label className="block text-sm">Catatan versi (opsional)
        <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="flex gap-2">
        <button className="btn primary" onClick={save}>Simpan versi baru</button>
        <button className="btn" disabled={!keyReady || !model} onClick={testPrompt}>Tes prompt</button>
      </div>
      {!keyReady && <p className="text-sm text-muted">Tes prompt nonaktif sampai XAI_API_KEY terisi.</p>}
      {message && <p>{message}</p>}
      {testOut && <pre className="mono text-xs whitespace-pre-wrap">{testOut}</pre>}
      <div className="border-t border-line pt-3">
        <h3 className="font-semibold">Riwayat versi</h3>
        <ul className="text-sm my-2">
          {(doc.versions || []).map((version) => (
            <li key={version.n}>v{version.n} · {fmtTime(version.ts, settings.data?.timezone)} · {version.note || "tanpa catatan"}</li>
          ))}
        </ul>
        <div className="flex gap-2 items-center">
          <select className="field" value={left} onChange={(e) => setLeft(Number(e.target.value))} aria-label="Versi kiri">
            <option value={0}>Versi A</option>
            {doc.versions.map((version) => <option key={version.n} value={version.n}>v{version.n}</option>)}
          </select>
          <select className="field" value={right} onChange={(e) => setRight(Number(e.target.value))} aria-label="Versi kanan">
            <option value={0}>Versi B</option>
            {doc.versions.map((version) => <option key={version.n} value={version.n}>v{version.n}</option>)}
          </select>
          <button className="btn" onClick={showDiff}>Lihat diff</button>
          <button className="btn" disabled={!left} onClick={rollback}>Rollback ke A</button>
        </div>
        {diff.length > 0 && (
          <pre className="mono text-xs mt-2 whitespace-pre-wrap">
            {diff.map((row, index) => (
              <div key={index} style={{ color: row.kind === "add" ? "var(--ok)" : row.kind === "del" ? "var(--bad)" : undefined }}>
                {row.kind === "add" ? "+ " : row.kind === "del" ? "- " : "  "}{row.text}
              </div>
            ))}
          </pre>
        )}
      </div>
    </section>
  );
}
