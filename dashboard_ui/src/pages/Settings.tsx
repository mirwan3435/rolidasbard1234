import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "../api/client";
import { useI18n } from "../i18n";

const schema = z.object({
  theme: z.enum(["dark", "light"]),
  timezone: z.enum(["Asia/Makassar", "Asia/Jakarta", "UTC"]),
  refresh_ms: z.number().int().min(500).max(30000),
  log_retention_days: z.number().int().min(1).max(90),
  token_usd_per_million: z.number().min(0).max(100),
  language: z.enum(["id", "en"]).default("id"),
  app_title: z.string().min(3).max(80).default("JARVIS // TRADE-BREIN"),
});

type Settings = z.infer<typeof schema>;

export function SettingsPage() {
  const { t, setLang } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/api/settings") });
  const [draft, setDraft] = useState<Settings | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { if (query.data) setDraft(query.data); }, [query.data]);
  if (!draft) return <div className="skeleton h-32" />;

  async function save() {
    const parsed = schema.safeParse(draft);
    if (!parsed.success) {
      setMessage(parsed.error.issues.map((issue) => issue.message).join("; "));
      return;
    }
    await api("/api/settings", { method: "PUT", body: JSON.stringify(parsed.data) });
    setLang(parsed.data.language);
    setMessage(t("settings.saved"));
    client.invalidateQueries({ queryKey: ["settings"] });
  }

  return (
    <div className="card p-4 max-w-xl space-y-3">
      <label>{t("settings.language")}
        <select className="field" value={draft.language || "id"} onChange={(e) => { const language = e.target.value as Settings["language"]; setDraft({ ...draft, language }); setLang(language); }}>
          <option value="id">Bahasa Indonesia</option>
          <option value="en">English</option>
        </select>
      </label>
      <label>{t("settings.title")}
        <input className="field" value={draft.app_title || "JARVIS // TRADE-BREIN"} onChange={(e) => setDraft({ ...draft, app_title: e.target.value })} />
      </label>
      <label>Tema
        <select className="field" value={draft.theme} onChange={(e) => setDraft({ ...draft, theme: e.target.value as Settings["theme"] })}>
          <option value="dark">Gelap</option>
          <option value="light">Terang</option>
        </select>
      </label>
      <label>Zona waktu tampilan
        <select className="field" value={draft.timezone} onChange={(e) => setDraft({ ...draft, timezone: e.target.value as Settings["timezone"] })}>
          <option value="Asia/Makassar">WITA (Asia/Makassar)</option>
          <option value="Asia/Jakarta">WIB (Asia/Jakarta)</option>
          <option value="UTC">UTC</option>
        </select>
      </label>
      <label>Interval refresh (ms)
        <input className="field" type="number" value={draft.refresh_ms} onChange={(e) => setDraft({ ...draft, refresh_ms: Number(e.target.value) })} />
      </label>
      <label>Retensi log (hari)
        <input className="field" type="number" value={draft.log_retention_days} onChange={(e) => setDraft({ ...draft, log_retention_days: Number(e.target.value) })} />
      </label>
      <label>Tarif token USD per 1 juta (isi sendiri, tidak dikunci di kode)
        <input className="field" type="number" step="0.1" value={draft.token_usd_per_million} onChange={(e) => setDraft({ ...draft, token_usd_per_million: Number(e.target.value) })} />
      </label>
      <button className="btn primary" onClick={save}>Simpan</button>
      {message && <p>{message}</p>}
      <p className="text-sm text-muted">Rotasi file JSONL berjalan harian di backend dan menyimpan arsip sesuai jumlah hari ini.</p>
    </div>
  );
}
