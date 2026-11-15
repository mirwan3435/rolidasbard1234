import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { bootstrap } from "./api/client";
import { Layout } from "./components/Layout";
import { Splash } from "./components/Splash";
import { ConfigPage } from "./pages/Config";
import { HealthPage } from "./pages/Health";
import { KeysPage } from "./pages/Keys";
import { LogPage } from "./pages/Log";
import { PaperPage } from "./pages/Paper";
import { RiskPage } from "./pages/Risk";
import { SettingsPage } from "./pages/Settings";
import { SkillsPage } from "./pages/Skills";
import { SymbolsPage } from "./pages/Symbols";
import { GlassFilter } from "./components/ui/GlassFilter";
import { Spinner } from "./components/ui/Panel";
import { useI18n } from "./i18n";
import { WorkflowPage } from "./pages/Workflow";
const LabPage = lazy(() => import("./pages/Lab"));
const ResearchPage = lazy(() => import("./pages/Research"));
const KnowledgePage = lazy(() => import("./pages/Knowledge"));
const RoomPage = lazy(() => import("./pages/Room"));
const DecisionsPage = lazy(() => import("./pages/Decisions"));
const CostsPage = lazy(() => import("./pages/Costs"));
const MachinePage = lazy(() => import("./pages/Machine"));

export default function App() {
  const { t } = useI18n();
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    setFailed(false);
    bootstrap()
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  let body;
  if (failed) {
    body = (
      <div className="p-8 max-w-2xl">
        <h1 className="text-xl font-semibold">{t("shell.backend")}</h1>
        <p className="mt-3">{t("shell.runHint")}</p>
        <pre className="mono mt-2">.\scripts\run_dashboard.ps1</pre>
        <p className="mt-3 text-sm text-muted">{t("shell.separate")}</p>
        <button className="btn primary mt-4" type="button" onClick={() => setAttempt((n) => n + 1)}>
          {t("shell.retry")}
        </button>
      </div>
    );
  } else if (!ready) {
    body = <div className="p-8"><Spinner /></div>;
  } else {
    body = (
    <Splash>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<WorkflowPage />} />
        <Route path="/simbol" element={<SymbolsPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/paper" element={<PaperPage />} />
        <Route path="/kunci" element={<KeysPage />} />
        <Route path="/skill" element={<SkillsPage />} />
        <Route path="/config" element={<ConfigPage />} />
        <Route path="/log" element={<LogPage />} />
        <Route path="/kesehatan" element={<HealthPage />} />
        <Route path="/pengaturan" element={<SettingsPage />} />
        <Route path="/lab" element={<Suspense fallback={<Spinner />}><LabPage /></Suspense>} />
        <Route path="/riset" element={<Suspense fallback={<Spinner />}><ResearchPage /></Suspense>} />
        <Route path="/kennisbank" element={<Suspense fallback={<Spinner />}><KnowledgePage /></Suspense>} />
        <Route path="/agentkamer" element={<Suspense fallback={<Spinner />}><RoomPage /></Suspense>} />
        <Route path="/keputusan" element={<Suspense fallback={<Spinner />}><DecisionsPage /></Suspense>} />
        <Route path="/biaya" element={<Suspense fallback={<Spinner />}><CostsPage /></Suspense>} />
        <Route path="/mesin" element={<Suspense fallback={<Spinner />}><MachinePage /></Suspense>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </Splash>
    );
  }

  return (
    <>
      <GlassFilter />
      {body}
    </>
  );
}
