import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "../api/client";

type Profile = {
  risk_per_trade_pct: number;
  stop_pct_of_price: number | null;
  max_open_positions: number;
  max_total_risk_pct: number;
  max_margin_pct: number;
  daily_loss_limit_pct: number;
  max_drawdown_pct: number;
  max_spread_to_stop_ratio: number;
  commission_per_lot_usd: number;
};

type ConfigDoc = {
  virtual_capital: number;
  active_profile: "standard" | "experiment_a";
  commission_confirmed: boolean;
  profiles: { standard: Profile; experiment_a: Profile };
};

const FIELDS: { key: keyof Profile; label: string; step?: string }[] = [
  { key: "risk_per_trade_pct", label: "Risiko per trade %", step: "0.1" },
  { key: "max_open_positions", label: "Maks posisi terbuka", step: "1" },
  { key: "max_total_risk_pct", label: "Maks total risiko %", step: "0.1" },
  { key: "max_margin_pct", label: "Maks margin %", step: "1" },
  { key: "daily_loss_limit_pct", label: "Batas rugi sesi %", step: "0.1" },
  { key: "max_drawdown_pct", label: "Batas drawdown %", step: "0.1" },
  { key: "max_spread_to_stop_ratio", label: "Maks rasio spread/stop", step: "0.01" },
  { key: "commission_per_lot_usd", label: "Komisi USD per lot", step: "0.1" },
];

const loose = z.object({
  virtual_capital: z.number().positive(),
  active_profile: z.enum(["standard", "experiment_a"]),
  commission_confirmed: z.boolean(),
});

export function ConfigPage() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["config"],
    queryFn: () => api<{ config: ConfigDoc; limits: unknown; reload_note: string; experiment_label: string }>("/api/config"),
  });
  const [draft, setDraft] = useState<ConfigDoc | null>(null);
  const [diff, setDiff] = useState<{ path: string; before: unknown; after: unknown }[]>([]);
  const [message, setMessage] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (query.data) setDraft(structuredClone(query.data.config));
  }, [query.data]);

  if (!draft || !query.data) return <div className="skeleton h-40" />;

  function updateProfile(name: "standard" | "experiment_a", key: keyof Profile, raw: string) {
    setDraft((current) => {
      if (!current) return current;
      const next = structuredClone(current);
      if (key === "stop_pct_of_price") {
        next.profiles[name].stop_pct_of_price = raw === "" ? null : Number(raw);
        return next;
      }
      const value = key === "max_open_positions" ? parseInt(raw, 10) : Number(raw);
      if (!Number.isNaN(value)) {
        next.profiles[name][key] = value;
      }
      return next;
    });
  }

  async function preview() {
    const check = loose.safeParse(draft);
    if (!check.success) {
      setMessage("Tipe nilai tidak valid.");
      return;
    }
    try {
      const result = await api<{ needs_confirm?: boolean; diff: { path: string; before: unknown; after: unknown }[]; saved: boolean }>("/api/config", {
        method: "PUT",
        body: JSON.stringify({ ...draft, confirm: false }),
      });
      setDiff(result.diff || []);
      setOpen(true);
      setMessage(result.diff?.length ? "Periksa diff sebelum menyimpan." : "Tidak ada perubahan.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ditolak");
      setOpen(false);
    }
  }

  async function commit() {
    try {
      const result = await api<{ saved: boolean; reload_note?: string }>("/api/config", {
        method: "PUT",
        body: JSON.stringify({ ...draft, confirm: true }),
      });
      setOpen(false);
      setMessage(result.reload_note || "Tersimpan.");
      client.invalidateQueries({ queryKey: ["config"] });
      client.invalidateQueries({ queryKey: ["status-header"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ditolak backend");
    }
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <p className="text-sm">{query.data.reload_note}</p>
      <p className="text-sm text-muted">Batas keras ada di <span className="mono">dashboard_api/hard_limits.py</span>. Rugi sesi dan drawdown tidak bisa dinaikkan melewati bawaan. Profil standard: risiko per trade maks 5%.</p>
      <div className="card p-4 grid grid-cols-2 gap-3">
        <label>Modal virtual
          <input className="field" type="number" value={draft.virtual_capital} onChange={(e) => setDraft({ ...draft, virtual_capital: Number(e.target.value) })} />
        </label>
        <label>Profil aktif
          <select className="field" value={draft.active_profile} onChange={(e) => setDraft({ ...draft, active_profile: e.target.value as ConfigDoc["active_profile"] })}>
            <option value="standard">standard</option>
            <option value="experiment_a">experiment_a</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <ProfileCard title="standard" profile={draft.profiles.standard} onChange={(key, value) => updateProfile("standard", key, value)} stopLocked />
        <ProfileCard title={`experiment_a — ${query.data.experiment_label}`} profile={draft.profiles.experiment_a} onChange={(key, value) => updateProfile("experiment_a", key, value)} />
      </div>
      <label className="flex gap-2 items-center card p-3">
        <input type="checkbox" checked={draft.commission_confirmed} onChange={(e) => setDraft({ ...draft, commission_confirmed: e.target.checked })} />
        Saya sudah cek komisi asli akun
      </label>
      {!draft.commission_confirmed && <div className="banner warn">Selama ini belum dikonfirmasi, banner kuning tetap tampil bila komisi masih 7.0.</div>}
      <button className="btn primary" onClick={preview}>Tinjau perubahan</button>
      {message && <p className="text-sm whitespace-pre-wrap">{message}</p>}
      {open && (
        <section className="card p-4 space-y-2">
          <h2 className="font-semibold">Diff</h2>
          {diff.length === 0 && <p>Tidak ada perubahan.</p>}
          {diff.map((row) => (
            <p key={row.path} className="mono text-sm">{row.path}: {String(row.before)} → {String(row.after)}</p>
          ))}
          <button className="btn primary" disabled={diff.length === 0} onClick={commit}>Konfirmasi simpan</button>
        </section>
      )}
    </div>
  );
}

function ProfileCard({ title, profile, onChange, stopLocked = false }: { title: string; profile: Profile; onChange: (key: keyof Profile, value: string) => void; stopLocked?: boolean }) {
  return (
    <section className="card p-3 space-y-2">
      <h2 className="font-semibold">{title}</h2>
      {FIELDS.map((field) => (
        <label key={field.key} className="block text-sm">{field.label}
          <input className="field" type="number" step={field.step} value={Number(profile[field.key] ?? 0)} onChange={(e) => onChange(field.key, e.target.value)} />
        </label>
      ))}
      <label className="block text-sm">Stop % dari harga
        <input className="field" type="number" step="0.1" disabled={stopLocked} value={profile.stop_pct_of_price ?? ""} placeholder={stopLocked ? "kosong (profil standard)" : ""} onChange={(e) => onChange("stop_pct_of_price", e.target.value)} />
      </label>
    </section>
  );
}
