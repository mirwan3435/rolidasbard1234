import { useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  BookOpen,
  Brain,
  Coins,
  Cpu,
  FileText,
  FlaskConical,
  HeartPulse,
  Home,
  KeyRound,
  LayoutGrid,
  LineChart,
  ListChecks,
  ScrollText,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  Sun,
  type LucideIcon,
} from "lucide-react";
import { useI18n } from "../i18n";
import { applyTheme, readTheme } from "../lib/theme";

const ICONS: Record<string, LucideIcon> = {
  "/": Home,
  "/simbol": LineChart,
  "/skill": Brain,
  "/agentkamer": LayoutGrid,
  "/keputusan": ListChecks,
  "/risk": Shield,
  "/paper": FileText,
  "/biaya": Coins,
  "/config": SlidersHorizontal,
  "/log": ScrollText,
  "/kesehatan": HeartPulse,
  "/mesin": Cpu,
  "/kunci": KeyRound,
  "/pengaturan": Settings,
  "/lab": FlaskConical,
  "/riset": Search,
  "/kennisbank": BookOpen,
};

export type SideItem = { to: string; label: string; badge?: number };

const itemClass = (active: boolean) =>
  `group relative flex h-11 w-11 items-center justify-center rounded-full transition-all duration-300 ${
    active
      ? "bg-steel-200 text-navy-950 shadow-[0_0_20px_rgba(185,205,230,0.7)]"
      : "text-white/60 hover:text-white"
  }`;

function Mark({ to, badge, size }: { to: string; badge?: number; size: number }) {
  const Icon = ICONS[to] || Home;
  return (
    <>
      <Icon size={size} />
      {badge ? <span className="absolute -right-1 -top-1 rounded-full bg-orange-400 px-1 text-[10px] font-semibold text-navy-950">{badge}</span> : null}
    </>
  );
}

function JarvisLogo() {
  const box = useRef<HTMLDivElement>(null);
  const [shift, setShift] = useState({ x: 0, y: 0 });
  function follow(event: React.MouseEvent) {
    const rect = box.current?.getBoundingClientRect();
    if (!rect) return;
    const x = ((event.clientX - (rect.left + rect.width / 2)) / rect.width) * 5;
    const y = ((event.clientY - (rect.top + rect.height / 2)) / rect.height) * 5;
    setShift({ x: Math.max(-5, Math.min(5, x)), y: Math.max(-5, Math.min(5, y)) });
  }
  return (
    <div
      ref={box}
      data-splash-target
      onMouseMove={follow}
      onMouseLeave={() => setShift({ x: 0, y: 0 })}
      className="relative flex h-16 w-16 shrink-0 items-center justify-center"
    >
      <span className="jarvis-float pointer-events-none absolute h-10 w-10 rounded-full bg-steel-300/70 blur-md" />
      <div
        className="liquid-mark relative flex h-16 w-16 items-center justify-center rounded-full text-white transition-transform duration-200 ease-out"
        style={{ transform: `translate(${shift.x}px, ${shift.y}px)` }}
      >
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden>
          <circle cx="16" cy="16" r="11" stroke="currentColor" strokeWidth="1.6" />
          <path d="M10 22 L22 10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="22.5" cy="16" r="1.5" fill="currentColor" />
        </svg>
      </div>
    </div>
  );
}

export function Sidebar({ items, onNavigate }: { items: SideItem[]; onNavigate: (event: React.MouseEvent<HTMLAnchorElement>, to: string) => void }) {
  const { t } = useI18n();
  return (
    <div className="fixed left-4 top-4 bottom-4 z-50 hidden w-16 flex-col items-center gap-3 md:flex">
      <JarvisLogo />
      <aside className="liquidGlass-wrapper flex min-h-0 w-16 flex-1 flex-col items-center justify-between rounded-full bg-navy-950 py-4">
        <div className="liquidGlass-effect" />
        <nav className="relative z-[1] flex min-h-0 w-full flex-1 flex-col items-center gap-3 overflow-y-auto py-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
          {items.map(({ to, label, badge }) => (
            <NavLink key={to} to={to} end={to === "/"} aria-label={label} title={label} onClick={(event) => onNavigate(event, to)} className={({ isActive }) => itemClass(isActive)}>
              <Mark to={to} badge={badge} size={22} />
              <span className="pointer-events-none absolute left-14 whitespace-nowrap rounded-lg bg-navy-950 px-3 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
                {label}
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="relative z-[1] flex flex-col items-center gap-3 text-white/60">
          <button type="button" className="flex h-11 w-11 items-center justify-center rounded-full hover:text-white" aria-label={t("settings.theme")} onClick={() => applyTheme(readTheme() === "light" ? "dark" : "light")}><Sun size={22} /></button>
        </div>
      </aside>
    </div>
  );
}

export function BottomNav({ items, onNavigate }: { items: SideItem[]; onNavigate: (event: React.MouseEvent<HTMLAnchorElement>, to: string) => void }) {
  return (
    <nav className="fixed bottom-3 left-3 right-3 z-50 flex items-center justify-around rounded-full bg-navy-950 py-3 md:hidden">
      {items.slice(0, 5).map(({ to, label }) => (
        <NavLink key={to} to={to} end={to === "/"} aria-label={label} onClick={(event) => onNavigate(event, to)} className={({ isActive }) => (isActive ? "text-steel-200" : "text-white/60 hover:text-white")}>
          <Mark to={to} size={20} />
        </NavLink>
      ))}
    </nav>
  );
}
