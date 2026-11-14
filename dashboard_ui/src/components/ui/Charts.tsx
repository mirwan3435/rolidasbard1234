function pathOf(values: number[], width: number, height: number) {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values.map((value, index) => {
    const x = values.length === 1 ? 0 : (index / (values.length - 1)) * width;
    const y = height - ((value - min) / span) * (height - 4) - 2;
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

export function Sparkline({ values }: { values: number[] }) {
  return (
    <svg width="88" height="28" aria-hidden>
      <path d={pathOf(values, 88, 28)} fill="none" stroke="var(--accent)" strokeWidth="1.4" />
    </svg>
  );
}

export function AreaChart({ values, label }: { values: number[]; label: string }) {
  const d = pathOf(values, 320, 90);
  return (
    <svg viewBox="0 0 320 90" width="100%" height="90" role="img" aria-label={label}>
      <path d={`${d} L320 90 L0 90 Z`} fill="rgba(89,240,139,.12)" />
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth="1.6" />
    </svg>
  );
}

export function DrawdownChart({ values, label }: { values: number[]; label: string }) {
  return (
    <svg viewBox="0 0 320 70" width="100%" height="70" role="img" aria-label={label}>
      <path d={pathOf(values, 320, 70)} fill="none" stroke="var(--danger)" strokeWidth="1.6" />
    </svg>
  );
}

export function Bars({ rows, label }: { rows: { label: string; value: number }[]; label: string }) {
  const max = Math.max(1, ...rows.map((row) => Math.abs(row.value)));
  return (
    <svg viewBox={`0 0 320 ${Math.max(40, rows.length * 18)}`} width="100%" role="img" aria-label={label}>
      {rows.map((row, index) => {
        const width = (Math.abs(row.value) / max) * 180;
        return (
          <g key={row.label} transform={`translate(0 ${index * 18})`}>
            <text x="0" y="12" fill="var(--muted)" fontSize="10">{row.label}</text>
            <rect x="92" y="3" width={width} height="10" fill={row.value >= 0 ? "var(--accent)" : "var(--danger)"} />
          </g>
        );
      })}
    </svg>
  );
}

export function Candles({ rows }: { rows: { o: number; h: number; l: number; c: number }[] }) {
  if (rows.length === 0) return null;
  const highs = rows.map((row) => row.h);
  const lows = rows.map((row) => row.l);
  const max = Math.max(...highs);
  const min = Math.min(...lows);
  const span = max - min || 1;
  const y = (price: number) => 8 + ((max - price) / span) * 64;
  return (
    <svg viewBox="0 0 220 80" width="220" height="80" aria-hidden>
      {rows.map((row, index) => {
        const x = 16 + index * 32;
        const up = row.c >= row.o;
        return (
          <g key={index}>
            <line x1={x} x2={x} y1={y(row.h)} y2={y(row.l)} stroke={up ? "var(--accent)" : "var(--danger)"} />
            <rect x={x - 5} y={Math.min(y(row.o), y(row.c))} width="10" height={Math.max(2, Math.abs(y(row.o) - y(row.c)))} fill={up ? "var(--accent)" : "var(--danger)"} />
          </g>
        );
      })}
    </svg>
  );
}
