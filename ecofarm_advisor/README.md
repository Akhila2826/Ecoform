# 🌿 EcoFarm Advisor

A GenAI-powered smart-farming web app (Python + Streamlit). Farmers enter farm details, get a
carbon-footprint estimate and eco-score, companion-crop and pollinator-plant suggestions,
a personalised AI action plan, a chat assistant (EcoBot) and a downloadable PDF eco-report.

## Features (from the project deck)
| Deck item | Implementation |
|---|---|
| Carbon footprint calculator (land, fertilizer, irrigation, machinery) | `ecofarm/eco_calculator.py` |
| Companion crop suggestions | `CompanionCropAdvisor` in `ecofarm/advisors.py` |
| Pollinator-friendly plants | `PollinatorAdvisor` in `ecofarm/advisors.py` |
| Eco-report with eco-score | Dashboard + PDF (`ecofarm/report.py`) |
| Streamlit dashboard, charts (Altair) | `app.py` |
| Data storage for session tracking / reuse | SQLite `user_inputs` + `eco_reports` (`ecofarm/database.py`) |
| `crop_pollinator_data.json` | `data/crop_pollinator_data.json` (12 crops) |
| **GenAI** | `ecofarm/ai_advisor.py` – Claude generates the action plan (multi-language) and answers follow-up questions, grounded on the farm data; falls back to rules when offline |

## Class design (matches the deck)
`Farmer` → `EcoCalculator` → `CompanionCropAdvisor`, `PollinatorAdvisor`, `DatabaseManager`.

## Architecture
```
Streamlit UI (app.py)
   ├─ Farmer (models.py)  ──► EcoCalculator ──► eco-score
   ├─ CompanionCropAdvisor / PollinatorAdvisor ◄── crop_pollinator_data.json
   ├─ ai_advisor.py (Claude API, rule-based fallback)
   ├─ DatabaseManager ──► SQLite (data/ecofarm.db)
   └─ report.py ──► PDF eco-report
```

## Run
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional: add ANTHROPIC_API_KEY for GenAI features
streamlit run app.py
```
Run the tests: `python tests/test_core.py` (or `pytest`).

## How the footprint is calculated
`total = crop_base × area + fertilizer_kg × factor + pump_hours × (kW × grid_factor | L/h × diesel_factor) + diesel_L × 2.68`
`eco_score = 100 × (1 − kg CO2e per ha / 4000)`, clamped to 0–100.
Factors are indicative averages kept in `eco_calculator.py` / the JSON file so experts can update them.

## Notes
- GenAI is *grounded*: the model only sees the farmer's data, computed figures and dataset, and is told not to invent numbers.
- The PDF uses English text (default PDF fonts); other languages show in the app.
- Extend: add crops to the JSON file; no code change needed.
