import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import type { DictKey } from "../i18n/id";

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
  active_profile: "standard" | "experiment_a" | "micro_10usd";
  commission_confirmed: boolean;
  profiles: { standard: Profile; experiment_a: Profile };
};

const FIELDS: { key: keyof Profile; label: DictKey; step?: string }[] = [
  { key: "risk_per_trade_pct", label: "config.field.risk_per_trade_pct", step: "0.1" },
  { key: "max_open_positions", label: "config.field.max_open_positions", step: "1" },
  { key: "max_total_risk_pct", label: "config.field.max_total_risk_pct", step: "0.1" },
  { key: "max_margin_pct", label: "config.field.max_margin_pct", step: "1" },
  { key: "daily_loss_limit_pct", label: "config.field.daily_loss_limit_pct", step: "0.1" },
  { key: "max_drawdown_pct", label: "config.field.max_drawdown_pct", step: "0.1" },
  { key: "max_spread_to_stop_ratio", label: "config.field.max_spread_to_stop_ratio", step: "0.01" },
  { key: "commission_per_lot_usd", label: "config.field.commission_per_lot_usd", step: "0.1" },
];

const loose = z.object({
  virtual_capital: z.number().positive(),
  active_profile: z.enum(["standard", "experiment_a", "micro_10usd"]),
  commission_confirmed: z.boolean(),
});

export function ConfigPage() {
  const { t } = useI18n();
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
      setMessage(t("config.badType"));
      return;
    }
    try {
      const result = await api<{ needs_confirm?: boolean; diff: { path: string; before: unknown; after: unknown }[]; saved: boolean }>("/api/config", {
        method: "PUT",
        body: JSON.stringify({ ...draft, confirm: false }),
      });
      setDiff(result.diff || []);
      setOpen(true);
      setMessage(result.diff?.length ? t("common.checkDiff") : t("common.noChange"));
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
      setMessage(result.reload_note || t("common.saved"));
      client.invalidateQueries({ queryKey: ["config"] });
      client.invalidateQueries({ queryKey: ["status-header"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ditolak backend");
    }
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <p className="text-sm">{query.data.reload_note}</p>
      <p className="text-sm text-muted">{t("config.limits")}</p>
      <div className="card p-4 grid grid-cols-2 gap-3">
        <label>{t("config.capital")}
          <input className="field" type="number" value={draft.virtual_capital} onChange={(e) => setDraft({ ...draft, virtual_capital: Number(e.target.value) })} />
        </label>
        <label>{t("config.profile")}
          <select className="field" value={draft.active_profile} onChange={(e) => setDraft({ ...draft, active_profile: e.target.value as ConfigDoc["active_profile"] })}>
            <option value="standard">standard</option>
            <option value="experiment_a">experiment_a</option>
            <option value="micro_10usd">micro_10usd</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <ProfileCard title="standard" profile={draft.profiles.standard} onChange={(key, value) => updateProfile("standard", key, value)} stopLocked />
        <ProfileCard title={`experiment_a — ${query.data.experiment_label}`} profile={draft.profiles.experiment_a} onChange={(key, value) => updateProfile("experiment_a", key, value)} />
      </div>
      <label className="flex gap-2 items-center card p-3">
        <input type="checkbox" checked={draft.commission_confirmed} onChange={(e) => setDraft({ ...draft, commission_confirmed: e.target.checked })} />
        {t("config.commission")}
      </label>
      <p className="text-sm text-muted">{t("config.micro")}</p>
      <pre className="mono text-xs whitespace-pre-wrap">{JSON.stringify((draft.profiles as { micro_10usd?: unknown }).micro_10usd || {}, null, 2)}</pre>
      {!draft.commission_confirmed && <div className="banner warn">{t("config.banner")}</div>}
      <button className="btn primary" onClick={preview}>{t("common.preview")}</button>
      {message && <p className="text-sm whitespace-pre-wrap">{message}</p>}
      {open && (
        <section className="card p-4 space-y-2">
          <h2 className="font-semibold">{t("config.diff")}</h2>
          {diff.length === 0 && <p>{t("common.noChange")}</p>}
          {diff.map((row) => (
            <p key={row.path} className="mono text-sm">{row.path}: {String(row.before)} → {String(row.after)}</p>
          ))}
          <button className="btn primary" disabled={diff.length === 0} onClick={commit}>{t("common.confirm")}</button>
        </section>
      )}
    </div>
  );
}

function ProfileCard({ title, profile, onChange, stopLocked = false }: { title: string; profile: Profile; onChange: (key: keyof Profile, value: string) => void; stopLocked?: boolean }) {
  const { t } = useI18n();
  return (
    <section className="card p-3 space-y-2">
      <h2 className="font-semibold">{title}</h2>
      {FIELDS.map((field) => (
        <label key={field.key} className="block text-sm">{t(field.label)}
          <input className="field" type="number" step={field.step} value={Number(profile[field.key] ?? 0)} onChange={(e) => onChange(field.key, e.target.value)} />
        </label>
      ))}
      <label className="block text-sm">{t("config.stop")}
        <input className="field" type="number" step="0.1" disabled={stopLocked} value={profile.stop_pct_of_price ?? ""} placeholder={stopLocked ? "kosong (profil standard)" : ""} onChange={(e) => onChange("stop_pct_of_price", e.target.value)} />
      </label>
    </section>
  );
}
