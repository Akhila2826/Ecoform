"""GenAI layer: personalised eco-advice and a farmer chat assistant.

Uses the Anthropic Claude API when ANTHROPIC_API_KEY is set. Without a key (or if the
call fails) it falls back to a deterministic rule-based answer, so the app always works.
The model is *grounded*: it only receives the farmer's inputs, the computed footprint and
the verified crop dataset, and is told not to invent numbers.
"""
import os
from .advisors import reduction_tips

MODEL = os.getenv("ECOFARM_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are EcoBot, a friendly agricultural sustainability advisor for small and medium farmers "
    "in India. Use simple, short sentences and practical, low-cost actions. Base every answer on "
    "the FARM DATA provided. Never invent emission numbers - quote only the figures given. "
    "If asked something outside farming or sustainability, politely steer back. For pesticide, "
    "dosage or legal questions, advise consulting the local agricultural extension officer."
)


def _client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except Exception:
        return None


def ai_available() -> bool:
    return _client() is not None


def build_context(farmer, result, companions, pollinators) -> str:
    comp = "; ".join(f"{c['name']} ({c['benefit']})" for c in companions) or "none listed"
    poll = "; ".join(f"{p['plant']} ({p['attracts']}, blooms {p['bloom']})" for p in pollinators) or "none listed"
    return (
        f"FARM DATA\nFarmer: {farmer.name}\nCrop: {farmer.crop_type}\nLand: {farmer.land_area:.2f} ha\n"
        f"Fertilizer: {farmer.fertilizer_used:.0f} kg {farmer.fertilizer_type}\n"
        f"Irrigation: {farmer.irrigation_hours:.0f} h/season, {farmer.pump_type} pump ({farmer.pump_kw} kW)\n"
        f"Machinery diesel: {farmer.machinery_diesel:.0f} L\n"
        f"Footprint (kg CO2e): crop {result.crop}, fertilizer {result.fertilizer}, irrigation {result.irrigation}, "
        f"machinery {result.machinery}; total {result.total}; per hectare {result.per_hectare}\n"
        f"Eco-score: {result.eco_score}/100 ({result.rating})\n"
        f"Companion crops: {comp}\nPollinator plants: {poll}"
    )


def _fallback_advice(farmer, result, companions, pollinators) -> str:
    lines = [f"**Eco-score: {result.eco_score}/100 ({result.rating}).** "
             f"Your farm emits about {result.per_hectare:,.0f} kg CO2e per hectare this season.", "",
             "**How to lower emissions:**"]
    lines += [f"- {t}" for t in reduction_tips(result, farmer)]
    if companions:
        lines += ["", f"**Companion crops for {farmer.crop_type}:** " + ", ".join(c["name"] for c in companions) + "."]
    if pollinators:
        lines += ["", "**Plants for bees and butterflies:** " + ", ".join(p["plant"] for p in pollinators) + "."]
    return "\n".join(lines)


def generate_advice(farmer, result, companions, pollinators, language: str = "English") -> tuple[str, str]:
    """Return (advice_markdown, source) where source is 'AI' or 'rule-based'."""
    client = _client()
    if client is None:
        return _fallback_advice(farmer, result, companions, pollinators), "rule-based"
    prompt = (
        f"{build_context(farmer, result, companions, pollinators)}\n\n"
        f"Write a short personalised action plan in {language} with: (1) a 2-sentence summary of how "
        "the farm is doing, (2) the top 3 actions to cut emissions, ranked by impact, (3) how to use the "
        "companion crops and pollinator plants, (4) one encouraging closing line. Use Markdown, max 250 words."
    )
    try:
        msg = client.messages.create(model=MODEL, max_tokens=700, system=SYSTEM_PROMPT,
                                     messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        if text:
            return text, "AI"
    except Exception:
        pass
    return _fallback_advice(farmer, result, companions, pollinators), "rule-based"


def chat(question: str, history: list[dict], farmer, result, companions, pollinators) -> str:
    """Answer a farmer's follow-up question, grounded in their farm data."""
    client = _client()
    if client is None:
        return ("AI chat needs an `ANTHROPIC_API_KEY` (see README). Meanwhile, here is your rule-based plan:\n\n"
                + _fallback_advice(farmer, result, companions, pollinators))
    system = SYSTEM_PROMPT + "\n\n" + build_context(farmer, result, companions, pollinators)
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-8:]]
    messages.append({"role": "user", "content": question})
    try:
        msg = client.messages.create(model=MODEL, max_tokens=600, system=system, messages=messages)
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip() or "Sorry, I have no answer."
    except Exception as exc:
        return f"Sorry, the AI service is unavailable right now ({type(exc).__name__}). Please try again."
