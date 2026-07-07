"""Twilio WhatsApp sender — officer alerts + farmer replies.

Uses the Twilio Sandbox (free trial credit). Long texts are chunked to stay
under WhatsApp's 1600-char message limit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import get_env  # noqa: E402

MAX_LEN = 1500


def _client():
    from twilio.rest import Client
    return Client(get_env("TWILIO_ACCOUNT_SID"), get_env("TWILIO_AUTH_TOKEN"))


def send_whatsapp(to: str, body: str) -> dict:
    """Send a WhatsApp message via Twilio sandbox. `to` = E.164 number."""
    if not to:
        return {"error": "no destination number configured"}
    to = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    sender = get_env("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    client = _client()
    sids = []
    chunks = [body[i:i + MAX_LEN] for i in range(0, len(body), MAX_LEN)] or [""]
    for chunk in chunks:
        msg = client.messages.create(from_=sender, to=to, body=chunk)
        sids.append(msg.sid)
    return {"sent": True, "to": to, "message_sids": sids, "chunks": len(chunks)}


def format_officer_alert(fsi_result: dict, farmer_contact: str = "") -> str:
    """Compose the officer alert message from an FSI result.

    Only states facts the system actually derived — no invented counts.
    Farmer-count integration is a pilot deliverable (Krishi Vibhag loan roster).
    farmer_contact: raw callback number, transient — appears in this live
    message only, never persisted (storage uses hashed IDs, see memory.py).
    """
    sig = fsi_result.get("signals", {})
    price = sig.get("price", {})
    drought = sig.get("drought", {})
    repay = sig.get("repayment_proximity", 0)
    repay_status = "ACTIVE" if repay >= 1.0 else ("APPROACHING" if repay > 0 else "not current")
    lines = [
        f"⚠️ KisaanRaksha Alert: {fsi_result.get('district')} ({fsi_result.get('region')})",
        f"FSI = {fsi_result.get('fsi')} ({fsi_result.get('level')})",
        f"Crop: {fsi_result.get('crop')}",
        f"Rainfall deficit: {drought.get('deficit_pct')}%",
        f"Market price: Rs.{price.get('market_price')}/qtl "
        f"({price.get('gap_below_msp_pct')}% below MSP Rs.{price.get('msp')})",
        f"NDVI (satellite): {sig.get('ndvi', {}).get('latest_ndvi')}",
        f"Loan-repayment window: {repay_status}",
        "Action: proactive outreach + PMFBY survey recommended.",
    ]
    if farmer_contact:
        lines.insert(3, f"Farmer contact (callback): {farmer_contact}")
    if fsi_result.get("mode"):
        lines.append(f"[{fsi_result['mode']}]")
    return "\n".join(lines)


def send_officer_alert(fsi_result: dict, to: str | None = None,
                       farmer_contact: str = "") -> dict:
    dest = to or get_env("OFFICER_WHATSAPP_TO")
    body = format_officer_alert(fsi_result, farmer_contact)
    result = send_whatsapp(dest, body)
    result["alert_body"] = body
    return result


if __name__ == "__main__":
    from mcp_server.tools.fsi import compute_fsi
    r = compute_fsi("Amravati", "cotton", simulate_crisis=True)
    print(format_officer_alert(r))
    if len(sys.argv) > 1:  # pass a number to actually send
        print(send_whatsapp(sys.argv[1], format_officer_alert(r)))
