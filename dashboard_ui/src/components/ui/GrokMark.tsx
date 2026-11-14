type Props = { state?: "idle" | "thinking" | "active" | "error" | "disabled"; size?: number; color?: string };

export function GrokMark({ state = "idle", size = 28, color = "currentColor" }: Props) {
  return (
    <svg className={`grok-mark grok-${state}`} width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <circle className="grok-ring" cx="16" cy="16" r="11" fill="none" stroke={color} strokeWidth="1.6" />
      <path className="grok-arc" d="M16 5 A11 11 0 0 1 27 16" fill="none" stroke={color} strokeWidth="1.8" />
      <path d="M8 24 L24 8" stroke={color} strokeWidth="1.6" />
      <g className="grok-orbit">
        <circle className="grok-dot" cx="27" cy="16" r="2" fill={color} />
        <circle cx="16" cy="5" r="1.3" fill={color} />
      </g>
    </svg>
  );
}
