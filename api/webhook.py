"""FastAPI webhook for Twilio WhatsApp Sandbox.

Flow: farmer sends Marathi voice note / text on WhatsApp
  -> Twilio POSTs here -> immediate ack (Twilio times out at ~15s)
  -> background: ASR (if voice) -> agent tool-loop -> reply via Twilio REST
  -> if a PMFBY claim was drafted, it is sent as a follow-up message.

Run:   uvicorn api.webhook:app --port 8000
Expose: ngrok http 8000   -> set the URL + /whatsapp in Twilio sandbox config.
"""
import sys
import uuid
from pathlib import Path

import requests
from fastapi import BackgroundTasks, FastAPI, Form
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.orchestrator import run_agent_sync  # noqa: E402
from alerts.whatsapp import send_whatsapp  # noqa: E402
from asr.marathi_asr import transcribe  # noqa: E402
from mcp_server.tools import memory  # noqa: E402
from mcp_server.tools.claim_pdf import render_claim_pdf  # noqa: E402
from mcp_server.tools.common import PROJECT_ROOT, get_env  # noqa: E402

# public directory Twilio can fetch generated PDFs from
FILES_DIR = PROJECT_ROOT / "data" / "public_files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

# supportive covering text per language — NO FSI/CRITICAL, instructional only.
# Keyed by the language the agent already detected (result["language"]).
CLAIM_COVER = {
    "Marathi": "📄 हा तुमचा पीक विमा दावा अर्ज आहे. तुम्ही तो जतन करून कृषी कार्यालयात सादर करू शकता.",
    "Hindi": "📄 यह आपका फसल बीमा दावा आवेदन है। आप इसे सहेजकर कृषि कार्यालय में जमा कर सकते हैं।",
    "English": "📄 This is your crop-insurance (PMFBY) claim form. You can save it and submit it at the Krishi (agriculture) office.",
}

app = FastAPI(title="KisaanRaksha WhatsApp Webhook")
app.mount("/files", StaticFiles(directory=str(FILES_DIR)), name="files")


def _public_base_url() -> str | None:
    """Public base URL for serving files: PUBLIC_BASE_URL env, else ngrok API."""
    base = get_env("PUBLIC_BASE_URL")
    if base:
        return base.rstrip("/")
    try:  # auto-detect the running ngrok tunnel
        r = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
        tunnels = r.json().get("tunnels", [])
        https = [t["public_url"] for t in tunnels if t.get("public_url", "").startswith("https")]
        if https:
            return https[0].rstrip("/")
    except Exception:
        pass
    return None

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


def _deliver_claim(from_number: str, result: dict) -> None:
    """Send the PMFBY claim to the FARMER as a PDF + covering text in their
    language. Falls back to plain text if PDF generation or media send fails.
    Farmer path only — never includes the FSI number or CRITICAL label.
    """
    lang = result.get("language", "Marathi")
    cover = CLAIM_COVER.get(lang, CLAIM_COVER["Marathi"])
    claim = result.get("claim") or {}
    claim_text = claim.get("claim_letter_marathi") or _latest_claim_text(from_number)
    if not claim_text:
        return

    base = _public_base_url()
    try:
        if not claim.get("evidence") or not base:
            raise RuntimeError(
                "no evidence payload" if not claim.get("evidence")
                else "no public base URL (PUBLIC_BASE_URL unset and ngrok not found)")
        name = f"pmfby_claim_{uuid.uuid4().hex[:10]}.pdf"
        render_claim_pdf(claim_text, claim["evidence"], FILES_DIR / name,
                         simulation=bool(result.get("simulation")))
        media_url = f"{base}/files/{name}"
        res = send_whatsapp(from_number, cover, media_url=media_url)
        if res.get("error"):
            raise RuntimeError(res["error"])
        return
    except Exception as e:
        print(f"[webhook] PDF claim delivery failed for {from_number}, "
              f"falling back to text: {e}", file=sys.stderr)

    # fallback: farmer still always gets the claim as plain text
    send_whatsapp(from_number, cover + "\n\n" + claim_text)


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
            _deliver_claim(from_number, result)
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
