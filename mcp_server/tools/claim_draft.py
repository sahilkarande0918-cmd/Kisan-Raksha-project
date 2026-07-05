"""PMFBY (Pradhan Mantri Fasal Bima Yojana) claim-letter drafter — Marathi.

Uses the live/simulated FSI evidence to ground the letter: rainfall deficit,
price gap, NDVI — actual numbers, not generic text. LLM via Gemini→Groq.
"""
from datetime import date

from .common import crop_calendar, find_district
from .llm_client import generate

SYSTEM = (
    "You draft formal crop-insurance intimation letters in Marathi for Maharashtra "
    "farmers under PMFBY (प्रधानमंत्री पीक विमा योजना). Output ONLY the letter text "
    "in Marathi (Devanagari). Formal but simple language a farmer can read aloud. "
    "Include: addressee (तालुका कृषी अधिकारी), subject line, farmer details "
    "placeholder, crop-loss evidence with the exact numbers given, request for "
    "survey under PMFBY section for localized calamity, date, signature block. "
    "Do NOT invent numbers not provided. The 'fsi' value is a financial-stress "
    "index (0-100) computed by an early-warning system — do NOT present it as "
    "a crop-loss percentage; cite it as 'आर्थिक तणाव निर्देशांक' if at all. "
    "Use the exact Marathi district spelling given in 'district_mr'. NEVER mix "
    "Latin/English letters inside Devanagari words — every word must be pure "
    "Devanagari or pure Latin (e.g. NDVI, PMFBY may stay Latin)."
)

# correct Marathi spellings for target districts (avoids LLM transliteration errors)
DISTRICT_MR = {
    "Amravati": "अमरावती", "Yavatmal": "यवतमाळ", "Akola": "अकोला",
    "Buldhana": "बुलढाणा", "Washim": "वाशिम", "Wardha": "वर्धा",
    "Nagpur": "नागपूर", "Chandrapur": "चंद्रपूर",
    "Chhatrapati Sambhajinagar": "छत्रपती संभाजीनगर", "Jalna": "जालना",
    "Beed": "बीड", "Latur": "लातूर", "Dharashiv": "धाराशिव",
    "Nanded": "नांदेड", "Parbhani": "परभणी", "Hingoli": "हिंगोली",
}


def draft_pmfby_claim(farmer_name: str, district: str, crop: str, fsi_result: dict) -> dict:
    """Draft a grounded PMFBY claim letter in Marathi from FSI evidence."""
    d = find_district(district)
    if not d:
        return {"error": f"Unknown district: {district}"}
    cal = crop_calendar()["crops"]
    crop_key = crop.strip().lower()
    crop_mr = cal.get(crop_key, {}).get("name_mr", crop)
    sig = fsi_result.get("signals", {})

    evidence = {
        "farmer_name": farmer_name or "____________",
        "district": d["name"],
        "district_mr": DISTRICT_MR.get(d["name"], d["name"]),
        "crop": f"{crop_key} ({crop_mr})",
        "date": date.today().strftime("%d/%m/%Y"),
        "fsi": fsi_result.get("fsi"),
        "rain_deficit_pct": sig.get("drought", {}).get("deficit_pct"),
        "market_price_rs_qtl": sig.get("price", {}).get("market_price"),
        "msp_rs_qtl": sig.get("price", {}).get("msp"),
        "ndvi": sig.get("ndvi", {}).get("latest_ndvi"),
    }
    prompt = (
        "Draft the PMFBY intimation letter with these facts:\n"
        + "\n".join(f"- {k}: {v}" for k, v in evidence.items() if v is not None)
        + "\n\nMention that satellite vegetation index (NDVI) and rainfall records "
          "support the loss claim and can be verified."
    )
    text, provider = generate(prompt, SYSTEM)
    return {
        "claim_letter_marathi": text.strip(),
        "evidence": evidence,
        "scheme": "PMFBY",
        "llm_provider": provider,
    }


if __name__ == "__main__":
    import json
    import sys
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252
    from .fsi import compute_fsi
    fsi = compute_fsi("Amravati", "cotton", simulate_crisis=True)
    out = draft_pmfby_claim("रमेश पाटील", "Amravati", "cotton", fsi)
    print(out.get("llm_provider"))
    print(out.get("claim_letter_marathi", out)[:800])
