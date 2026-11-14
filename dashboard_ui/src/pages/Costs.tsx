import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Panel } from "../components/ui/Panel";
import { useI18n } from "../i18n";

type Costs = { tokens_today: number; calls_today: number; tokens_7d: number; usd_today: number | null; prices_set: boolean; price_note: string; token_budget: number; by_agent: Record<string, number>; source: "real" | "sample" };

export default function CostsPage() {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["costs-page"], queryFn: () => api<Costs>("/api/costs") });
  const data = query.data;
  if (!data) return <Panel title={t("costs.title")}><p>{t("common.loading")}</p></Panel>;
  return (
    <Panel title={t("costs.title")} source={data.source}>
      {!data.prices_set && <div className="banner warn mb-2">{data.price_note || t("costs.priceNote")}</div>}
      <p>Hari ini {data.tokens_today} token · {data.calls_today} panggilan · 7 hari {data.tokens_7d}</p>
      <p>Budget {data.tokens_today}/{data.token_budget}{data.usd_today != null ? ` · $${data.usd_today}` : ""}</p>
      <ul>{Object.entries(data.by_agent).map(([name, tokens]) => <li key={name}>{name}: {tokens}</li>)}</ul>
    </Panel>
  );
}
