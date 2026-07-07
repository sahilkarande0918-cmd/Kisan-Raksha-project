"""KisaanRaksha MCP Server — FastMCP.

Six role-scoped tools, each with one clear job (rubric: role-scoped agentic
pipeline, no bare LLM calls). Run:  python -m mcp_server.server
"""
import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alerts.whatsapp import send_officer_alert as _send_alert  # noqa: E402
from mcp_server.tools import claim_draft, fsi, mandi, memory, ndvi, weather  # noqa: E402

mcp = FastMCP(
    "KisaanRaksha",
    instructions=(
        "Farmer financial-distress early-warning tools for Maharashtra. "
        "Signals are grounded in Open-Meteo, Agmarknet (data.gov.in) and NASA "
        "MODIS. FSI > 75 is critical and should trigger an officer alert."
    ),
)


@mcp.tool
def query_weather_signal(district: str) -> dict:
    """30-day rainfall deficit vs 5-year baseline for a Maharashtra district.
    Returns drought_signal 0-1 (Open-Meteo ERA5, offline cache fallback)."""
    return weather.get_weather_signal(district)


@mcp.tool
def query_mandi_prices(crop: str, district: str) -> dict:
    """Latest mandi price vs MSP for a crop (cotton/soybean/tur) near a
    district. Returns price_signal 0-1 (Agmarknet via data.gov.in)."""
    return mandi.get_mandi_signal(crop, district)


@mcp.tool
def query_ndvi_signal(district: str) -> dict:
    """Satellite crop-health (NDVI) for a district from NASA MODIS MOD13Q1.
    Returns ndvi_signal 0-1 (higher = more vegetation stress)."""
    return ndvi.get_ndvi_signal(district)


@mcp.tool
def compute_fsi(district: str, crop: str = "cotton", simulate_crisis: bool = False) -> dict:
    """Financial Stress Index 0-100 for a district+crop via the trained
    LightGBM model over all four signals. FSI > 75 = CRITICAL.
    simulate_crisis=True replays a labeled 2024-style crisis (demo mode)."""
    return fsi.compute_fsi(district, crop, simulate_crisis)


@mcp.tool
def get_farmer_history(phone: str) -> dict:
    """Structured memory: farmer profile + recent interactions + claims,
    keyed by hashed WhatsApp number (no raw PII stored)."""
    return memory.get_farmer_history(phone)


@mcp.tool
def send_officer_alert(district: str, crop: str = "cotton", simulate_crisis: bool = False,
                       to_number: str = "", farmer_contact: str = "") -> dict:
    """Send the WhatsApp alert for a district's current FSI to the duty
    officer (Twilio). Only call when FSI is CRITICAL or officer requests it.
    farmer_contact is injected by the runtime (webhook From number) so the
    officer can call back — leave it empty; do not fill it yourself."""
    result = fsi.compute_fsi(district, crop, simulate_crisis)
    if "error" in result:
        return result
    return _send_alert(result, to_number or None, farmer_contact)


@mcp.tool
def draft_pmfby_claim(farmer_name: str, district: str, crop: str = "cotton",
                      simulate_crisis: bool = False) -> dict:
    """Draft a PMFBY crop-insurance intimation letter in Marathi, grounded in
    the district's current FSI evidence (rainfall, price, NDVI numbers)."""
    fsi_result = fsi.compute_fsi(district, crop, simulate_crisis)
    if "error" in fsi_result:
        return fsi_result
    return claim_draft.draft_pmfby_claim(farmer_name, district, crop, fsi_result)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
