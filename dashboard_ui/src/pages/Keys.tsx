import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import { StatusDot } from "../components/ui/Panel";

type Slot = { slot: string; filled: boolean; last4: string; required: boolean };

const LABELS: Record<string, string> = {
  XAI_API_KEY: "xAI (wajib untuk Grok)",
  TELEGRAM_BOT_TOKEN: "Token bot Telegram (opsional)",
  TELEGRAM_CHAT_ID: "Chat ID Telegram (opsional)",
};

type Connection = { id: string; label: string; status: string; detail: string; checked_at: string };

export function KeysPage() {
  const { t } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["keys"], queryFn: () => api<{ slots: Slot[] }>("/api/keys") });
  const links = useQuery({ queryKey: ["connections"], queryFn: () => api<{ connections: Connection[] }>("/api/connections") });
  return (
    <div className="space-y-4 max-w-3xl">
      <section className="card p-4">
        <h2 className="font-semibold mb-2">{t("keys.connections")}</h2>
        <div className="grid grid-cols-2 gap-2">
          {(links.data?.connections || []).map((item) => (
            <article key={item.id} className="card p-2">
              <div className="flex items-center gap-2"><StatusDot status={item.status} /><strong>{item.label}</strong></div>
              <p className="text-sm text-muted">{item.detail}</p>
              <button className="btn mt-2" onClick={async () => { await api(`/api/connections/${item.id}/check`, { method: "POST" }); links.refetch(); }}>{t("keys.check")}</button>
            </article>
          ))}
        </div>
      </section>
      <p className="text-sm text-muted">Write-only. Nilai tersimpan tidak pernah dikirim balik ke browser, hanya status dan 4 karakter terakhir.</p>
      {(query.data?.slots || []).map((slot) => (
        <SlotCard key={slot.slot} slot={slot} onSaved={() => client.invalidateQueries({ queryKey: ["keys"] })} />
      ))}
    </div>
  );
}

function SlotCard({ slot, onSaved }: { slot: Slot; onSaved: () => void }) {
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
      setMessage("Tersimpan.");
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
      <h2 className="font-semibold">{LABELS[slot.slot] || slot.slot}</h2>
      <p>Status: {slot.filled ? `Terisi ••••${slot.last4}` : "Kosong"}</p>
      <label className="text-sm" htmlFor={slot.slot}>Nilai baru</label>
      <div className="flex gap-2">
        <input id={slot.slot} className="field" type={show ? "text" : "password"} autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)} />
        <button className="btn" type="button" onClick={() => setShow((v) => !v)}>{show ? "Sembunyikan" : "Tampilkan"}</button>
      </div>
      <p className="text-xs text-muted">Tampilkan hanya berlaku untuk teks yang sedang diketik.</p>
      <div className="flex gap-2">
        <button className="btn primary" disabled={busy || value.trim().length < 8} onClick={save}>Simpan</button>
        <button className="btn" disabled={busy || !slot.filled} onClick={test}>Tes koneksi</button>
      </div>
      {message && <p>{message}</p>}
    </section>
  );
}
