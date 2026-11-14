function uiLang() {
  return localStorage.getItem("dashboard-lang") === "en" ? "en" : "id";
}

export function ageLabel(sec?: number | null) {
  const en = uiLang() === "en";
  if (sec == null) return en ? "none" : "belum ada";
  if (sec < 5) return en ? "just now" : "baru saja";
  if (sec < 60) return `${Math.round(sec)} ${en ? "s" : "dtk"}`;
  return `${Math.round(sec / 60)} ${en ? "m" : "mnt"}`;
}

export function fmtTime(iso?: string | null, timeZone = "Asia/Makassar") {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(uiLang() === "en" ? "en-US" : "id-ID", {
    timeZone,
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function money(value?: number | null) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(uiLang() === "en" ? "en-US" : "id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function statusLabel(status?: string) {
  const map: Record<string, string> = {
    ok: "ok",
    warn: uiLang() === "en" ? "watch" : "waspada",
    error: "error",
    running: uiLang() === "en" ? "running" : "jalan",
    idle: uiLang() === "en" ? "idle" : "diam",
    disabled: uiLang() === "en" ? "off" : "mati",
  };
  return map[status || ""] || status || "—";
}

export function statusColor(status?: string) {
  const map: Record<string, string> = {
    ok: "var(--ok)",
    warn: "var(--warn)",
    error: "var(--bad)",
    running: "var(--run)",
    idle: "var(--idle)",
    disabled: "var(--idle)",
  };
  return map[status || ""] || "var(--idle)";
}

export function download(filename: string, content: string, type = "text/plain") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function lineDiff(before: string, after: string) {
  const left = before.split("\n");
  const right = after.split("\n");
  const rows: { kind: "same" | "add" | "del"; text: string }[] = [];
  const max = Math.max(left.length, right.length);
  for (let i = 0; i < max; i += 1) {
    if (left[i] === right[i]) rows.push({ kind: "same", text: right[i] ?? "" });
    else {
      if (left[i] !== undefined) rows.push({ kind: "del", text: left[i] });
      if (right[i] !== undefined) rows.push({ kind: "add", text: right[i] });
    }
  }
  return rows;
}
