import { useEffect, useState } from "react";
import { api, sessionToken } from "../api/client";
import { Sparkline } from "../components/ui/Charts";
import { KpiCard, Panel, Spinner } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Machine = {
  cpu_pct: number; ram_pct: number; disk_free_gb: number; disk_pct: number; python: string; node: string | null;
  uptime_sec: number; port_8765: string; port_5173: string; terminal64: boolean;
  xai: { status: string; latency_ms: number | null }; history?: { cpu: number; ram: number }[]; source: "real" | "sample";
};

export default function MachinePage() {
  const { t } = useI18n();
  const [data, setData] = useState<Machine | null>(null);
  useEffect(() => {
    let stop = false;
    api<Machine>("/api/machines").then((row) => { if (!stop) setData(row); }).catch(() => undefined);
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${location.host}/api/ws/machine?token=${encodeURIComponent(sessionToken())}`);
    socket.onmessage = (message) => {
      try { setData(JSON.parse(message.data)); } catch { /* abaikan bingkai rusak */ }
    };
    return () => { stop = true; socket.close(); };
  }, []);
  if (!data) return <Panel title={t("machine.title")}><Spinner /></Panel>;
  const hours = Math.floor(data.uptime_sec / 3600);
  return (
    <Panel title={t("machine.title")} source={data.source}>
      <div className="grid grid-cols-4 gap-2">
        <KpiCard label={t("machine.cpu")} value={`${data.cpu_pct.toFixed(0)}%`} />
        <KpiCard label={t("machine.ram")} value={`${data.ram_pct.toFixed(0)}%`} />
        <KpiCard label={t("machine.disk")} value={`${data.disk_free_gb} GB`} />
        <KpiCard label={t("machine.uptime")} value={`${hours} h`} />
      </div>
      <div className="flex gap-4 mt-3">
        <Sparkline values={(data.history || []).map((row) => row.cpu)} />
        <Sparkline values={(data.history || []).map((row) => row.ram)} />
      </div>
      <table className="table mt-3">
        <tbody>
          <tr><td>Python</td><td>{data.python}</td></tr>
          <tr><td>Node</td><td>{data.node || t("machine.nodeMissing")}</td></tr>
          <tr><td>{t("machine.ports")}</td><td>8765 {data.port_8765} · 5173 {data.port_5173}</td></tr>
          <tr><td>{t("machine.terminal")}</td><td>{data.terminal64 ? t("machine.present") : t("machine.absent")}</td></tr>
          <tr><td>xAI</td><td>{data.xai.status}{data.xai.latency_ms != null ? ` · ${data.xai.latency_ms} ms` : ""}</td></tr>
        </tbody>
      </table>
    </Panel>
  );
}
