import { Spinner } from "./Panel";

export function Emblem({ motif, status }: { motif: string; status: string }) {
  const pace = status === "checking" ? "fast" : status === "connected" ? "steady" : status === "not_configured" ? "still" : "slow";
  return (
    <span className={`emblem-frame emblem-${status} pace-${pace}`}>
      <svg className={`emblem motif-${motif}`} width="48" height="48" viewBox="0 0 48 48" aria-hidden>
        {motif === "spark" && (
          <polyline className="em-draw dash-part" points="4,32 12,28 18,16 26,34 32,12 40,22 46,18" fill="none" stroke="currentColor" strokeWidth="1.8" />
        )}
        {motif === "sphere" && (
          <g className="spin-part">
            <circle cx="24" cy="24" r="11" fill="none" stroke="currentColor" />
            <ellipse cx="24" cy="24" rx="11" ry="4" fill="none" stroke="currentColor" />
            <circle cx="24" cy="13" r="1.8" fill="currentColor" />
            <circle cx="34" cy="28" r="1.4" fill="currentColor" />
            <circle cx="15" cy="29" r="1.2" fill="currentColor" />
          </g>
        )}
        {motif === "clock" && (
          <>
            <circle cx="24" cy="24" r="13" fill="none" stroke="currentColor" />
            <g className="spin-part">
              <line x1="24" y1="24" x2="24" y2="13" stroke="currentColor" strokeWidth="1.8" />
            </g>
            <circle cx="24" cy="24" r="1.6" fill="currentColor" />
          </>
        )}
        {motif === "bars" && (
          <>
            <rect className="bar-part" x="10" y="28" width="5" height="10" fill="currentColor" />
            <rect className="bar-part" x="18" y="20" width="5" height="18" fill="currentColor" />
            <rect className="bar-part" x="26" y="12" width="5" height="26" fill="currentColor" />
            <rect className="bar-part" x="34" y="18" width="5" height="20" fill="currentColor" />
          </>
        )}
        {motif === "ripple" && (
          <>
            <circle className="ripple-part" cx="24" cy="24" r="5" fill="none" stroke="currentColor" />
            <circle className="ripple-part" cx="24" cy="24" r="10" fill="none" stroke="currentColor" />
            <circle className="ripple-part" cx="24" cy="24" r="15" fill="none" stroke="currentColor" />
          </>
        )}
        {motif === "led" && (
          <>
            <circle className="lamp" cx="14" cy="16" r="3.5" fill="currentColor" />
            <rect className="bar-part" x="22" y="28" width="4" height="8" fill="currentColor" />
            <rect className="bar-part" x="28" y="18" width="4" height="18" fill="currentColor" />
            <rect className="bar-part" x="34" y="12" width="4" height="24" fill="currentColor" />
          </>
        )}
        {motif === "branch" && (
          <path className="dash-part" d="M6 36 C16 36 16 14 28 14 C36 14 36 26 44 22" fill="none" stroke="currentColor" strokeWidth="1.8" />
        )}
        {motif === "orbit" && (
          <>
            <ellipse cx="24" cy="24" rx="15" ry="6" fill="none" stroke="currentColor" />
            <ellipse cx="24" cy="24" rx="6" ry="15" fill="none" stroke="currentColor" />
            <g className="spin-part">
              <circle cx="39" cy="24" r="2.2" fill="currentColor" />
            </g>
          </>
        )}
      </svg>
      {status === "checking" && <span className="emblem-cover"><Spinner size="sm" /></span>}
    </span>
  );
}
