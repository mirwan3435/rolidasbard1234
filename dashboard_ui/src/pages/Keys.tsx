import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import { Emblem } from "../components/ui/Emblem";
import { Panel, StatusDot } from "../components/ui/Panel";

type Slot = { slot: string; filled: boolean; last4: string; required: boolean };

type Connection = { id: string; label: string; status: string; detail: string; checked_at: string; motif?: string; source?: "real" | "sample" };

export function KeysPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["keys"], queryFn: () => api<{ slots: Slot[] }>("/api/keys") });
  const links = useQuery({ queryKey: ["connections"], queryFn: () => api<{ connections: Connection[] }>("/api/connections") });
  const [checking, setChecking] = useState<string | null>(null);
  async function check(id: string) {
    setChecking(id);
    try {
      await api(`/api/connections/${id}/check`, { method: "POST" });
      await links.refetch();
    } finally {
      setChecking(null);
    }
  }
  return (
    <div className="space-y-4 max-w-3xl">
      <Panel title={t("keys.connections")} source="real">
        <div className="grid grid-cols-2 gap-2">
          {(links.data?.connections || []).map((item) => (
            <article key={item.id} className="card p-2">
              <div className="flex items-center gap-2">
                <Emblem key={item.checked_at} size={40} state={checking === item.id ? "working" : item.status === "connected" ? "success" : item.status === "disconnected" || item.status === "error" ? "error" : "idle"} />
                <StatusDot status={item.status} />
                <strong>{item.label}</strong>
              </div>
              <p className="text-sm text-muted">{item.detail}</p>
              <p className="text-xs text-muted">{item.checked_at}</p>
              <button className="btn mt-2" onClick={() => check(item.id)}>{t("keys.check")}</button>
              {item.id === "telegram" && <button className="btn mt-2 ml-2" onClick={async () => { await api("/api/connections/telegram/test", { method: "POST" }); links.refetch(); }}>{t("keys.sendTest")}</button>}
            </article>
          ))}
        </div>
        <p className="text-xs text-muted mt-2">{t("keys.mt5Slot")}</p>
      </Panel>
      <p className="text-sm text-muted">{t("keys.writeOnly")}</p>
      {(query.data?.slots || []).map((slot) => (
        <SlotCard key={slot.slot} slot={slot} onSaved={() => client.invalidateQueries({ queryKey: ["keys"] })} />
      ))}
    </div>
  );
}

function SlotCard({ slot, onSaved }: { slot: Slot; onSaved: () => void }) {
  const { t } = useI18n();
  const labels: Record<string, string> = { XAI_API_KEY: t("keys.xai"), TELEGRAM_BOT_TOKEN: t("keys.telegramToken"), TELEGRAM_CHAT_ID: t("keys.telegramChat") };
  const [value, setValue] = useState("");
  const [show, setShow] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await api(`/api/keys/${slot.slot}`, { method: "PUT", body: JSON.stringify({ value }) });
      setValue("");
      setShow(false);
      setMessage(t("common.saved"));
      onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Gagal menyimpan");
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ ok: boolean; message: string }>(`/api/keys/${slot.slot}/test`, { method: "POST" });
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Tes gagal");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card p-4 space-y-2">
      <h2 className="font-semibold">{labels[slot.slot] || slot.slot}</h2>
      <p>Status: {slot.filled ? `${t("keys.statusFilled")} ••••${slot.last4}` : t("keys.statusEmpty")}</p>
      <label className="text-sm" htmlFor={slot.slot}>{t("keys.newValue")}</label>
      <div className="flex gap-2">
        <input id={slot.slot} className="field" type={show ? "text" : "password"} autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)} />
        <button className="btn" type="button" onClick={() => setShow((v) => !v)}>{show ? t("keys.hide") : t("keys.show")}</button>
      </div>
      <p className="text-xs text-muted">{t("keys.showHint")}</p>
      <div className="flex gap-2">
        <button className="btn primary" disabled={busy || value.trim().length < 8} onClick={save}>{t("common.save")}</button>
        <button className="btn" disabled={busy || !slot.filled} onClick={test}>{t("keys.test")}</button>
      </div>
      {message && <p>{message}</p>}
    </section>
  );
}
