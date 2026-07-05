"""Marathi speech-to-text.

Primary (demo path): Groq-hosted Whisper large-v3 — free tier, ~1s latency,
strong Marathi support. Optional offline path: AI4Bharat IndicConformer via
HF token (install torch + transformers, set ASR_BACKEND=ai4bharat) — kept for
the offline-first story and data-sovereignty deployment.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import get_env  # noqa: E402


def transcribe_groq(audio_bytes: bytes, filename: str = "note.ogg") -> str:
    from groq import Groq
    client = Groq(api_key=get_env("GROQ_API_KEY"))
    # no forced language: Whisper auto-detects (Marathi, Hindi, ...), so the
    # agent can reply in whatever language the farmer actually spoke
    resp = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        response_format="text",
    )
    return resp.strip() if isinstance(resp, str) else str(resp).strip()


def transcribe_ai4bharat(audio_bytes: bytes) -> str:
    """Offline AI4Bharat path (requires: pip install torch transformers soundfile)."""
    import soundfile as sf
    import torch
    from transformers import AutoModelForCTC, AutoProcessor

    model_id = "ai4bharat/indicwav2vec_v1_marathi"
    processor = AutoProcessor.from_pretrained(model_id, token=get_env("HF_TOKEN") or None)
    model = AutoModelForCTC.from_pretrained(model_id, token=get_env("HF_TOKEN") or None)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    speech, sr = sf.read(path)
    inputs = processor(speech, sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)
    return processor.batch_decode(ids)[0]


def transcribe(audio_bytes: bytes, filename: str = "note.ogg") -> str:
    """Transcribe Marathi audio -> text using the configured backend."""
    backend = get_env("ASR_BACKEND", "groq").lower()
    if backend == "ai4bharat":
        try:
            return transcribe_ai4bharat(audio_bytes)
        except Exception:
            pass  # fall through to hosted Whisper
    return transcribe_groq(audio_bytes, filename)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        print(transcribe(Path(sys.argv[1]).read_bytes(), Path(sys.argv[1]).name))
    else:
        print("usage: python asr/marathi_asr.py <audio-file>")
