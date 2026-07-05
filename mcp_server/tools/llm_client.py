"""Single LLM entry point — Gemini first, automatic Groq fallback.

Both are free tiers. Gemini free tier quota can exhaust (429), so every call
transparently falls back to Groq Llama-3.3-70B. Returns (text, provider).
"""
from .common import get_env

GEMINI_MODEL = "gemini-2.0-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _try_gemini(prompt: str, system: str | None) -> str:
    from google import genai
    client = genai.Client(api_key=get_env("GEMINI_API_KEY"))
    contents = f"{system}\n\n{prompt}" if system else prompt
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
    if not resp.text:
        raise RuntimeError("empty Gemini response")
    return resp.text


def _try_groq(prompt: str, system: str | None) -> str:
    from groq import Groq
    client = Groq(api_key=get_env("GROQ_API_KEY"))
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}]
    resp = client.chat.completions.create(model=GROQ_MODEL, messages=messages, temperature=0.4)
    return resp.choices[0].message.content or ""


def generate(prompt: str, system: str | None = None) -> tuple[str, str]:
    """Generate text; returns (text, provider_used)."""
    try:
        return _try_gemini(prompt, system), f"gemini:{GEMINI_MODEL}"
    except Exception:
        return _try_groq(prompt, system), f"groq:{GROQ_MODEL}"
