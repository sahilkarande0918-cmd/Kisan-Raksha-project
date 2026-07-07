"""KisaanRaksha agent orchestrator — LLM tool-calling loop over the MCP server.

The LLM never answers from thin air: every fact comes from an MCP tool call
(rubric: no bare LLM calls; role-scoped pipeline). Tool schemas are read from
the FastMCP server itself, so the agent and server can't drift apart.

Providers: Groq llama-3.3-70b (OpenAI-compatible tool calling, free tier) runs
the loop; Gemini is used by lower-level tools (claim letters) when available.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastmcp import Client  # noqa: E402
from groq import Groq  # noqa: E402

from mcp_server.server import mcp  # noqa: E402
from mcp_server.tools import memory  # noqa: E402
from mcp_server.tools.common import get_env  # noqa: E402

MODEL = "llama-3.3-70b-versatile"
MAX_TURNS = 8

SYSTEM = """You are KisaanRaksha (किसानरक्षा), an early-warning assistant for
Maharashtra farmers, reached via WhatsApp. The user is usually a farmer
writing/speaking in Marathi.

Rules:
- ALWAYS gather facts via tools; never invent weather, price or FSI numbers.
- Typical flow for a distress/status query: compute_fsi for the farmer's
  district+crop (this internally uses weather, mandi and satellite signals).
  Use the individual signal tools only when the farmer asks specifically.
- If FSI level is CRITICAL: call send_officer_alert, then draft_pmfby_claim
  with the farmer's name (use "____" if unknown).
- If farmer history shows a known district/crop, use them without re-asking.
- FINAL reply: answer in the SAME language the farmer used (Marathi default;
  Hindi in Hindi, English in English — always simple and warm), max ~120
  words. Never mix Latin characters inside Devanagari words. State the
  key numbers (FSI, rainfall deficit, price vs MSP). If an alert was sent or
  a claim drafted, say so clearly. Never promise money; suggest contacting
  the taluka Krishi office. If crisis indicators are severe, include the
  Kisan helpline 1800-233-4000.
- If a demo/test message says 'demo' or 'चाचणी', pass simulate_crisis=true
  to tools and keep the simulation label visible."""


def _detect_language(text: str) -> str:
    """Heuristic Marathi/Hindi/English detection for reply-language routing."""
    marathi_markers = ("आहे", "मी ", "माझ", "काय", "करू", "झाल", "होत", "पिक", "शेतकरी आहे", "नाही")
    hindi_markers = ("है", "हूँ", "हूं", "मैं", "मेरी", "मेरा", "क्या", "करूँ", "करूं", "नहीं", "किसान हूँ")
    if not any("ऀ" <= ch <= "ॿ" for ch in text):
        return "English"
    h = sum(m in text for m in hindi_markers)
    m = sum(m in text for m in marathi_markers)
    return "Hindi" if h > m else "Marathi"


def _mcp_tools_to_openai(tools) -> list[dict]:
    return [{
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description or "",
            "parameters": t.inputSchema,
        },
    } for t in tools]


async def run_agent(user_message: str, phone: str = "unknown") -> dict:
    """One full agent turn: memory -> tool loop -> Marathi reply -> memory."""
    history = memory.get_farmer_history(phone)
    client = Groq(api_key=get_env("GROQ_API_KEY"))
    actions, last_fsi = [], {}

    async with Client(mcp) as mcp_client:
        tools = _mcp_tools_to_openai(await mcp_client.list_tools())
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "system", "content": f"Farmer memory (from get_farmer_history): {json.dumps(history, ensure_ascii=False)}"},
            {"role": "system", "content": f"IMPORTANT: the farmer wrote in {_detect_language(user_message)}. Your FINAL reply MUST be in {_detect_language(user_message)}."},
            {"role": "user", "content": user_message},
        ]
        for _ in range(MAX_TURNS):
            resp = client.chat.completions.create(
                model=MODEL, messages=messages, tools=tools, tool_choice="auto",
                temperature=0.3)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                reply = (msg.content or "").strip()
                break
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    if tc.function.name == "send_officer_alert":
                        # deterministic injection: the raw callback number goes
                        # into the live alert only — the LLM never sees it, and
                        # this overwrites anything the model may have invented
                        args["farmer_contact"] = "" if phone == "unknown" else phone
                    result = await mcp_client.call_tool(tc.function.name, args)
                    payload = result.data if hasattr(result, "data") else str(result)
                except Exception as e:
                    payload = {"error": str(e)}
                actions.append(tc.function.name)
                if tc.function.name == "compute_fsi" and isinstance(payload, dict):
                    last_fsi = payload
                if tc.function.name == "draft_pmfby_claim" and isinstance(payload, dict) \
                        and payload.get("claim_letter_marathi"):
                    memory.log_claim(phone, payload["evidence"]["district"],
                                     last_fsi.get("crop", "cotton"),
                                     payload["claim_letter_marathi"])
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(payload, ensure_ascii=False, default=str)})
        else:
            reply = "क्षमस्व, सध्या माहिती मिळवण्यात अडचण येत आहे. कृपया पुन्हा प्रयत्न करा."

    memory.log_interaction(
        phone, user_message,
        last_fsi.get("district") or history.get("district"),
        last_fsi.get("crop") or history.get("crop"),
        last_fsi.get("fsi"), last_fsi.get("level"), actions)
    return {"reply": reply, "actions": actions, "fsi": last_fsi.get("fsi"),
            "level": last_fsi.get("level")}


def run_agent_sync(user_message: str, phone: str = "unknown") -> dict:
    return asyncio.run(run_agent(user_message, phone))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    msg = sys.argv[1] if len(sys.argv) > 1 else \
        "नमस्कार, मी अमरावतीचा शेतकरी आहे. माझं कापसाचं पीक चांगलं नाही, पाऊसही कमी झाला. मला काय करावं? (चाचणी demo)"
    out = run_agent_sync(msg, "+919999000001")
    print("ACTIONS:", out["actions"], "| FSI:", out["fsi"], out["level"])
    print("REPLY:\n", out["reply"])
