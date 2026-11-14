"""Panggilan ringan ke penyedia. Respons error tidak mengembalikan rahasia."""
import json

import httpx

from dashboard_api.services.env_io import read_values
from dashboard_api.services.state import read_account, write_account


def _scrub(text: str, secrets: list[str]) -> str:
    clean = text or ""
    for secret in secrets:
        if secret:
            clean = clean.replace(secret, "••••")
    return clean[:240]


def _remember(ok: bool, message: str, tokens: int = 0):
    account = read_account()
    account["grok_last_ok"] = ok
    account["grok_last_message"] = message
    if tokens:
        account["grok_tokens_today"] = int(account.get("grok_tokens_today") or 0) + int(tokens)
    write_account({
        "virtual_capital": account["virtual_capital"],
        "equity": account["equity"],
        "peak": account["peak"],
        "session_start": account["session_start"],
        "positions": account["positions"],
        "server_offset_hours": account["server_offset_hours"],
        "mt5_connected": account["mt5_connected"],
        "mt5_message": account["mt5_message"],
        "grok_tokens_today": account["grok_tokens_today"],
        "grok_last_ok": account["grok_last_ok"],
        "grok_last_message": account["grok_last_message"],
        "updated_at": account.get("updated_at"),
    })


async def test_slot(slot: str):
    values = read_values()
    secret = values.get(slot, "")
    if not secret:
        return {"ok": False, "message": "Slot masih kosong"}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            if slot == "XAI_API_KEY":
                response = await client.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {secret}"},
                )
                if response.status_code == 200:
                    _remember(True, "Koneksi xAI berhasil")
                    return {"ok": True, "message": "Koneksi xAI berhasil"}
                _remember(False, f"xAI menolak permintaan ({response.status_code})")
                return {"ok": False, "message": f"xAI menolak permintaan ({response.status_code})"}
            if slot == "TELEGRAM_BOT_TOKEN":
                response = await client.get(f"https://api.telegram.org/bot{secret}/getMe")
                if response.status_code == 200:
                    try:
                        payload = response.json()
                    except json.JSONDecodeError:
                        payload = {}
                    if payload.get("ok"):
                        return {"ok": True, "message": "Bot Telegram merespons"}
                return {"ok": False, "message": f"Telegram menolak token ({response.status_code})"}
            if slot == "TELEGRAM_CHAT_ID":
                token = values.get("TELEGRAM_BOT_TOKEN", "")
                if not token:
                    return {"ok": False, "message": "Isi TELEGRAM_BOT_TOKEN dulu"}
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getChat",
                    params={"chat_id": secret},
                )
                if response.status_code == 200:
                    return {"ok": True, "message": "Chat Telegram terjangkau"}
                return {"ok": False, "message": f"Chat tidak terjangkau ({response.status_code})"}
    except httpx.HTTPError:
        return {"ok": False, "message": "Gagal menghubungi penyedia"}
    return {"ok": False, "message": "Slot tidak didukung"}


def render_prompt(template: str, sample: dict):
    text = template
    for key, value in sample.items():
        text = text.replace("{" + key + "}", json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
    return text


def parse_verdict(raw):
    """Gagal parse = reject. score_adjust hanya boleh -10..0. Field ekstra ditolak."""
    rejected = {"ok": False, "verdict": "reject", "parsed": None}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return rejected
    if not isinstance(raw, dict):
        return rejected
    allowed = {"signal_id", "verdict", "score_adjust", "reasons", "risk_flags", "confidence"}
    if set(raw) - allowed or not allowed <= set(raw):
        return rejected
    if raw["verdict"] not in {"accept", "reduce", "reject"}:
        return rejected
    adjust = raw["score_adjust"]
    if isinstance(adjust, bool) or not isinstance(adjust, int) or not -10 <= adjust <= 0:
        return rejected
    reasons = raw["reasons"]
    flags = raw["risk_flags"]
    known = {"news", "low_liquidity", "htf_conflict", "overextended", "correlation", "spread", "other"}
    if not isinstance(reasons, list) or len(reasons) > 5 or any(not isinstance(item, str) or len(item) > 200 for item in reasons):
        return rejected
    if not isinstance(flags, list) or len(flags) > 6 or any(item not in known for item in flags):
        return rejected
    confidence = raw["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        return rejected
    if not isinstance(raw["signal_id"], str) or not raw["signal_id"]:
        return rejected
    return {"ok": True, "verdict": raw["verdict"], "parsed": raw}


async def test_prompt(model: str, temperature: float, max_tokens: int, timeout_sec: int, prompt: str, schema: dict):
    from dashboard_api.services.costs import BudgetExceeded, budget_guard
    try:
        budget_guard()
    except BudgetExceeded as exc:
        return {"ok": False, "message": str(exc), "raw": "", "parsed": None, "tokens": 0}
    values = read_values()
    secret = values.get("XAI_API_KEY", "")
    if not secret:
        return {"ok": False, "message": "XAI_API_KEY belum terisi", "raw": "", "parsed": None, "tokens": 0}
    sample = {
        "symbol": "EURUSDm",
        "zones": [{"type": "order block", "score": 72}],
        "dxy_context": "melemah",
        "whales": "volume meningkat, palsu",
        "debate": "contoh debat",
        "risk_profile": "standard",
        "capital": "95",
    }
    user = "Contoh input palsu, bukan sinyal live:\n" + json.dumps(sample, ensure_ascii=False)
    system = render_prompt(prompt, sample)
    body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                json=body,
            )
    except httpx.HTTPError:
        return {"ok": False, "message": "Gagal menghubungi xAI", "raw": "", "parsed": None, "tokens": 0}
    if response.status_code != 200:
        return {
            "ok": False,
            "message": f"xAI menolak ({response.status_code})",
            "raw": "",
            "parsed": None,
            "tokens": 0,
        }
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return {"ok": False, "message": "Respons bukan JSON", "raw": "", "parsed": None, "tokens": 0}
    raw = ""
    try:
        raw = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raw = ""
    raw = _scrub(str(raw), [secret])
    parsed = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    required = schema.get("required") if isinstance(schema, dict) else []
    missing = []
    if isinstance(parsed, dict) and isinstance(required, list):
        missing = [key for key in required if key not in parsed]
    tokens = 0
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    if isinstance(usage.get("total_tokens"), int):
        tokens = usage["total_tokens"]
    _remember(True, "Tes prompt selesai", tokens)
    from dashboard_api.services.costs import record
    record("CORE", model, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or tokens))
    return {
        "ok": parsed is not None and not missing,
        "message": "Terurai" if parsed is not None and not missing else "Respons mentah tidak sesuai skema",
        "raw": raw[:8000],
        "parsed": parsed,
        "missing_fields": missing,
        "tokens": tokens,
    }
