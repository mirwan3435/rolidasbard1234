import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import en from "./en";
import id, { type DictKey } from "./id";

const dictionaries = { id, en };

function missingKeys() {
  const a = Object.keys(id);
  const b = Object.keys(en);
  if (a.length !== b.length || a.some((key) => !(key in en))) {
    throw new Error("Kamus id/en tidak sama");
  }
}
missingKeys();

type Lang = "id" | "en";
const Ctx = createContext<{ lang: Lang; setLang: (lang: Lang) => void; t: (key: DictKey) => string }>({
  lang: "id",
  setLang: () => undefined,
  t: (key) => id[key],
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => (localStorage.getItem("dashboard-lang") === "en" ? "en" : "id"));
  const setLang = (next: Lang) => {
    localStorage.setItem("dashboard-lang", next);
    setLangState(next);
  };
  useEffect(() => {
    document.documentElement.lang = lang === "id" ? "id" : "en";
  }, [lang]);
  const value = useMemo(() => ({
    lang,
    setLang,
    t: (key: DictKey) => dictionaries[lang][key] || id[key] || key,
  }), [lang]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n() {
  return useContext(Ctx);
}
