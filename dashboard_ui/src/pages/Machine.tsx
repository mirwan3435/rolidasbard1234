import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Machine = { cpu_pct: number; ram_pct: number; disk_free_gb: number; python: string; uptime_sec: number; source: "real" | "sample" };

export default function MachinePage() {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["machine"], queryFn: () => api<Machine>("/api/machines"), refetchInterval: 2000 });
  const data = query.data;
  if (!data) return <Panel title={t("machine.title")}><p>{t("common.loading")}</p></Panel>;
  return (
    <Panel title={t("machine.title")} source={data.source}>
      <p>CPU {data.cpu_pct.toFixed(0)}% · RAM {data.ram_pct.toFixed(0)}% · disk kosong {data.disk_free_gb} GB</p>
      <p>Python {data.python} · uptime {Math.round(data.uptime_sec / 3600)} jam</p>
      <div className="h-2 mt-2" style={{ background: "var(--surface-2)" }}><div style={{ width: `${Math.min(100, data.cpu_pct)}%`, height: 8, background: "var(--accent)" }} /></div>
    </Panel>
  );
}
