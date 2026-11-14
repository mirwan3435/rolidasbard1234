type Props = { state?: "idle" | "thinking" | "active" | "error" | "disabled"; size?: number; color?: string };

export function GrokMark({ state = "idle", size = 28, color = "currentColor" }: Props) {
  return (
    <svg className={`grok-mark grok-${state}`} width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="16" r="11" fill="none" stroke={color} strokeWidth="1.6" />
      <path d="M8 24 L24 8" stroke={color} strokeWidth="1.6" />
      <circle className="grok-dot" cx="24" cy="8" r="2" fill={color} />
    </svg>
  );
}
