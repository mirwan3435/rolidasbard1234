const PATHS: Record<string, JSX.Element> = {
  "/": (
    <>
      <circle cx="6" cy="7" r="2" />
      <circle cx="18" cy="6" r="2" />
      <circle cx="8" cy="17" r="2" />
      <path d="M8 7 h8 M7.4 9.2 8.6 15 M16.2 7.6 9.6 15.4" />
    </>
  ),
  "/simbol": (
    <>
      <path d="M4 18 V8 M4 18 h16" />
      <path d="M7 14 l3-4 3 3 4-6" />
    </>
  ),
  "/skill": (
    <>
      <path d="M12 4 5 8 v8 l7 4 7-4 V8 Z" />
      <path d="M12 12 5 8 M12 12 l7-4 M12 12 v8" />
    </>
  ),
  "/agentkamer": (
    <>
      <rect x="4" y="4" width="6" height="6" rx="1" />
      <rect x="14" y="4" width="6" height="6" rx="1" />
      <rect x="4" y="14" width="6" height="6" rx="1" />
      <rect x="14" y="14" width="6" height="6" rx="1" />
    </>
  ),
  "/keputusan": (
    <>
      <path d="M8 4 h8 l3 3 v13 H8 Z" />
      <path d="M10 12 l2 2 4-4" />
    </>
  ),
  "/risk": (
    <>
      <path d="M12 3 5 6 v6 c0 4 3 6.5 7 8 4-1.5 7-4 7-8 V6 Z" />
    </>
  ),
  "/paper": (
    <>
      <path d="M8 3 h7 l4 4 v14 H8 Z" />
      <path d="M15 3 v4 h4 M10 12 h6 M10 16 h6" />
    </>
  ),
  "/biaya": (
    <>
      <ellipse cx="12" cy="8" rx="6" ry="2.5" />
      <path d="M6 8 v8 c0 1.4 2.7 2.5 6 2.5 s6-1.1 6-2.5 V8" />
    </>
  ),
  "/config": (
    <>
      <path d="M4 8 h16 M4 16 h16" />
      <circle cx="9" cy="8" r="2" />
      <circle cx="15" cy="16" r="2" />
    </>
  ),
  "/log": (
    <>
      <path d="M6 6 h12 M6 12 h12 M6 18 h8" />
    </>
  ),
  "/kesehatan": (
    <>
      <path d="M3 12 h4 l2-5 3 10 2-5 h7" />
    </>
  ),
  "/mesin": (
    <>
      <rect x="5" y="5" width="14" height="10" rx="1.5" />
      <path d="M9 19 h6 M12 15 v4" />
    </>
  ),
  "/kunci": (
    <>
      <circle cx="9" cy="11" r="3.5" />
      <path d="M12 12.5 19 12.5 M16.5 12.5 V16" />
    </>
  ),
  "/pengaturan": (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.5 v2.2 M12 18.3 V20.5 M3.5 12 h2.2 M18.3 12 H20.5 M5.8 5.8 l1.6 1.6 M16.6 16.6 l1.6 1.6 M18.2 5.8 l-1.6 1.6 M7.4 16.6 5.8 18.2" />
    </>
  ),
  "/lab": (
    <>
      <path d="M9 3 v6 L5 18 a4 4 0 0 0 3.5 3 h7 A4 4 0 0 0 19 18 L15 9 V3" />
      <path d="M8 3 h8" />
    </>
  ),
  "/riset": (
    <>
      <circle cx="11" cy="11" r="5" />
      <path d="M15 15 l5 5" />
    </>
  ),
  "/kennisbank": (
    <>
      <path d="M5 5 h6 a4 4 0 0 1 4 4 v11 H7 a3 3 0 0 0-2 2 Z" />
      <path d="M19 5 h-6 a4 4 0 0 0-4 4" />
    </>
  ),
};

export function NavIcon({ to }: { to: string }) {
  return (
    <svg className="nav-ico" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {PATHS[to] || <circle cx="12" cy="12" r="6" />}
    </svg>
  );
}
