let token = "";

export async function bootstrap() {
  const response = await fetch("/api/bootstrap", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Bootstrap ditolak");
  const data = await response.json();
  token = data.token;
  return data as { token: string; mode: string };
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("X-Dashboard-Token", token);
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    const detail = (data as { detail?: unknown })?.detail;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail ?? response.statusText);
    throw new Error(message);
  }
  return data as T;
}

export function sessionToken() {
  return token;
}

export function openEvents(onEvent: (event: Record<string, unknown>) => void, filter: Record<string, string> = {}) {
  const params = new URLSearchParams();
  Object.entries(filter).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/api/ws/events?${params.toString()}`);
  socket.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data));
    } catch {
      /* baris rusak diabaikan di server; ini cadangan */
    }
  };
  return socket;
}
