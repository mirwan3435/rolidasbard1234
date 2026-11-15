import type { CSSProperties } from "react";
import raw from "../../assets/emblem.svg?raw";

export type EmblemState = "idle" | "working" | "error" | "success";

function fromStatus(status: string): EmblemState {
  if (status === "checking" || status === "working" || status === "connected") return status === "connected" ? "success" : "working";
  if (status === "error" || status === "disconnected") return "error";
  return "idle";
}

export function Emblem({
  size = 32,
  state = "idle",
  status,
  tone,
  breathe = false,
  alarm = false,
}: {
  size?: number;
  state?: EmblemState;
  status?: string;
  tone?: string;
  breathe?: boolean;
  alarm?: boolean;
  motif?: string;
}) {
  const visual = status ? fromStatus(status) : state;
  const markup = raw.replace("<svg", `<svg width="${size}" height="${size}"`);
  const style = tone ? ({ "--emblem-color": tone } as CSSProperties) : undefined;
  return (
    <span className={`mark${alarm ? " mark-alarm" : ""}`} data-state={visual} data-breathe={breathe ? "true" : undefined} style={{ width: size, height: size, ...style }} aria-hidden>
      <span className="mark-logo" dangerouslySetInnerHTML={{ __html: markup }} />
      <svg className="mark-check" viewBox="0 0 32 32" width={size} height={size}>
        <path d="M9 17 l5 5 l10-12" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}
