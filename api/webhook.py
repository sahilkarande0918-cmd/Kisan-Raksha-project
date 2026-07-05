"""FastAPI webhook for Twilio WhatsApp Sandbox.

Flow: farmer sends Marathi voice note / text on WhatsApp
  -> Twilio POSTs here -> immediate ack (Twilio times out at ~15s)
  -> background: ASR (if voice) -> agent tool-loop -> reply via Twilio REST
  -> if a PMFBY claim was drafted, it is sent as a follow-up message.

Run:   uvicorn api.webhook:app --port 8000
Expose: ngrok http 8000   -> set the URL + /whatsapp in Twilio sandbox config.
"""
import sys
from pathlib import Path

import requests
from fastapi import BackgroundTasks, FastAPI, Form
from fastapi.responses import PlainTextResponse, Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.orchestrator import run_agent_sync  # noqa: E402
from alerts.whatsapp import send_whatsapp  # noqa: E402
from asr.marathi_asr import transcribe  # noqa: E402
from mcp_server.tools import memory  # noqa: E402
from mcp_server.tools.common import get_env  # noqa: E402

app = FastAPI(title="KisaanRaksha WhatsApp Webhook")

ACK_TWIML = (
    '<?xml version="1.0" encoding="UTF-8"?><Response><Message>'
    "🌾 किसानरक्षा: तुमचा संदेश मिळाला. माहिती तपासत आहोत, थोड्या वेळात उत्तर देतो..."
    "</Message></Response>"
)


def _download_media(url: str) -> bytes:
    # Twilio media URLs need account auth
    r = requests.get(url, auth=(get_env("TWILIO_ACCOUNT_SID"), get_env("TWILIO_AUTH_TOKEN")),
                     timeout=30)
    r.raise_for_status()
    return r.content


def _latest_claim_text(phone: str) -> str | None:
    hist = memory.get_farmer_history(phone, limit=1)
    if hist.get("claims"):
        # claims list has metadata only; fetch full text
        import sqlite3
        from mcp_server.tools.common import DB_PATH
        with sqlite3.connect(DB_PATH) as c:
            row = c.execute(
                "SELECT claim_text FROM claims WHERE farmer_id=? ORDER BY id DESC LIMIT 1",
                (memory.farmer_id_from_phone(phone),)).fetchone()
        return row[0] if row else None
    return None


def _process(from_number: str, text: str | None, media_url: str | None) -> None:
    try:
        if media_url:
            audio = _download_media(media_url)
            text = transcribe(audio)
            send_whatsapp(from_number, f"📝 आम्हाला समजले: {text}")
        if not text:
            send_whatsapp(from_number, "कृपया संदेश किंवा आवाज संदेश पाठवा.")
            return
        result = run_agent_sync(text, from_number)
        send_whatsapp(from_number, result["reply"])
        if "draft_pmfby_claim" in result.get("actions", []):
            claim = _latest_claim_text(from_number)
            if claim:
                send_whatsapp(from_number, "📄 तुमचा PMFBY विमा दावा मसुदा:\n\n" + claim)
    except Exception as e:
        try:
            send_whatsapp(from_number, "क्षमस्व, तांत्रिक अडचण आली. कृपया पुन्हा प्रयत्न करा.")
        finally:
            print(f"[webhook] processing error for {from_number}: {e}", file=sys.stderr)


@app.post("/whatsapp")
async def whatsapp(background: BackgroundTasks,
                   From: str = Form(""),
                   Body: str = Form(""),
                   NumMedia: str = Form("0"),
                   MediaUrl0: str = Form(""),
                   MediaContentType0: str = Form("")) -> Response:
    is_audio = NumMedia not in ("", "0") and MediaContentType0.startswith("audio")
    background.add_task(_process, From.replace("whatsapp:", ""),
                        Body or None, MediaUrl0 if is_audio else None)
    return Response(content=ACK_TWIML, media_type="application/xml")


@app.get("/health")
async def health() -> PlainTextResponse:
    return PlainTextResponse("ok")
