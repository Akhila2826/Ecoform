"""EcoFarm Advisor - Streamlit frontend.  Run:  streamlit run app.py"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import altair as alt
import pandas as pd
import streamlit as st

from ecofarm import ai_advisor
from ecofarm.advisors import CompanionCropAdvisor, PollinatorAdvisor, load_crop_data
from ecofarm.database import DatabaseManager
from ecofarm.eco_calculator import EcoCalculator
from ecofarm.models import ACRE_TO_HA, FERTILIZER_TYPES, PUMP_TYPES, Farmer
from ecofarm.report import build_pdf

st.set_page_config(page_title="EcoFarm Advisor", page_icon="🌿", layout="wide")


@st.cache_data
def get_crop_data() -> dict:
    return load_crop_data()


@st.cache_resource
def get_db() -> DatabaseManager:
    return DatabaseManager()


crop_data = get_crop_data()
db = get_db()
companion_advisor = CompanionCropAdvisor(crop_data)
pollinator_advisor = PollinatorAdvisor(crop_data)

st.title("🌿 EcoFarm Advisor")
st.caption("Measure your farm's carbon footprint, get AI-powered eco advice, and plant for bees and butterflies.")

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("🚜 Farm details")
    name = st.text_input("Farmer name", placeholder="e.g. Ramesh")
    c1, c2 = st.columns([2, 1])
    land_value = c1.number_input("Land size", min_value=0.0, value=2.0, step=0.5)
    land_unit = c2.selectbox("Unit", ["acres", "hectares"])
    crop = st.selectbox("Main crop", sorted(crop_data.keys()))

    st.subheader("Fertilizer")
    fert_type = st.selectbox("Type", FERTILIZER_TYPES)
    fert_kg = st.number_input("Total used this season (kg)", min_value=0.0, value=200.0, step=10.0)

    st.subheader("Irrigation")
    pump_type = st.selectbox("Pump type", PUMP_TYPES)
    irr_hours = st.number_input("Pump hours this season", min_value=0.0, value=150.0, step=10.0)
    pump_kw = st.number_input("Pump power (kW)", min_value=0.5, value=3.7, step=0.5,
                              disabled=pump_type != "Electric")

    st.subheader("Machinery")
    diesel_l = st.number_input("Diesel used this season (litres)", min_value=0.0, value=40.0, step=5.0)

    language = st.selectbox("Advice language", ["English", "Hindi", "Telugu", "Tamil", "Marathi"])
    analyse = st.button("🌱 Analyse my farm", type="primary", use_container_width=True)

    st.divider()
    if ai_advisor.ai_available():
        st.success("GenAI: Claude connected")
    else:
        st.info("GenAI: offline mode (set ANTHROPIC_API_KEY for AI advice & chat)")

# ---------------------------------------------------------------- analysis
if analyse:
    area_ha = land_value * ACRE_TO_HA if land_unit == "acres" else land_value
    farmer = Farmer.enter_details(
        name=name, land_area=area_ha, crop_type=crop, fertilizer_type=fert_type,
        fertilizer_used=fert_kg, pump_type=pump_type, irrigation_hours=irr_hours,
        pump_kw=pump_kw, machinery_diesel=diesel_l)
    errors = farmer.validate()
    if errors:
        for e in errors:
            st.error(e)
    else:
        calc = EcoCalculator(crop_base_emission=crop_data[crop]["base_emission"])
        result = calc.calculate_footprint(farmer)
        companions = companion_advisor.suggest_crops(crop)
        pollinators = pollinator_advisor.suggest_plants(crop)
        with st.spinner("Preparing your personalised advice..."):
            advice, source = ai_advisor.generate_advice(farmer, result, companions, pollinators, language)
        db.save_data(farmer, result, advice)
        st.session_state.update(farmer=farmer, result=result, companions=companions,
                                pollinators=pollinators, advice=advice, source=source,
                                language=language, chat=[])

if "result" not in st.session_state:
    st.info("👈 Enter your farm details in the sidebar and click **Analyse my farm** to begin.")
    st.stop()

farmer: Farmer = st.session_state["farmer"]
result = st.session_state["result"]
companions = st.session_state["companions"]
pollinators = st.session_state["pollinators"]
advice = st.session_state["advice"]

tab_dash, tab_plants, tab_ai, tab_hist = st.tabs(
    ["📊 Dashboard", "🌼 Companion & Pollinator Plants", "🤖 AI Advisor & Chat", "🗂️ History"])

# ---------------------------------------------------------------- dashboard
with tab_dash:
    m1, m2, m3 = st.columns(3)
    m1.metric("Total footprint", f"{result.total:,.0f} kg CO₂e")
    m2.metric("Per hectare", f"{result.per_hectare:,.0f} kg CO₂e/ha")
    m3.metric("Eco-score", f"{result.eco_score}/100", result.rating)
    st.progress(result.eco_score / 100, text=f"Eco-score: {result.rating}")

    df = pd.DataFrame({"Source": list(result.breakdown().keys()),
                       "kg CO2e": list(result.breakdown().values())})
    left, right = st.columns(2)
    with left:
        st.subheader("Emission sources")
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Source:N", sort="-y", axis=alt.Axis(labelAngle=-20)),
            y="kg CO2e:Q", color=alt.Color("Source:N", legend=None),
            tooltip=["Source", "kg CO2e"])
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.subheader("Share of footprint")
        pie = alt.Chart(df[df["kg CO2e"] > 0]).mark_arc(innerRadius=50).encode(
            theta="kg CO2e:Q", color="Source:N", tooltip=["Source", "kg CO2e"])
        st.altair_chart(pie, use_container_width=True)

    pdf_advice = advice if st.session_state["language"] == "English" else ai_advisor._fallback_advice(
        farmer, result, companions, pollinators)  # PDF font supports Latin script only
    st.download_button("📄 Download eco-report (PDF)",
                       data=build_pdf(farmer, result, companions, pollinators, pdf_advice),
                       file_name=f"ecoreport_{farmer.name.strip().replace(' ', '_')}.pdf",
                       mime="application/pdf")

# ---------------------------------------------------------------- plants
with tab_plants:
    st.subheader(f"🌾 Companion crops for {farmer.crop_type}")
    cols = st.columns(len(companions) or 1)
    for col, c in zip(cols, companions):
        col.success(f"**{c['name']}**\n\n{c['benefit']}")
    st.subheader("🐝🦋 Pollinator-friendly plants")
    cols = st.columns(len(pollinators) or 1)
    for col, p in zip(cols, pollinators):
        col.warning(f"**{p['plant']}**\n\nAttracts: {p['attracts']}\n\nBlooms: {p['bloom']}")

# ---------------------------------------------------------------- AI
with tab_ai:
    st.subheader("Your personalised action plan")
    st.caption(f"Source: {st.session_state['source']}")
    st.markdown(advice)
    st.divider()
    st.subheader("💬 Ask EcoBot")
    for m in st.session_state["chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q = st.chat_input("Ask e.g. 'How can I cut fertilizer use?'")
    if q:
        history = list(st.session_state["chat"])
        st.session_state["chat"].append({"role": "user", "content": q})
        with st.spinner("Thinking..."):
            reply = ai_advisor.chat(q, history, farmer, result, companions, pollinators)
        st.session_state["chat"].append({"role": "assistant", "content": reply})
        st.rerun()

# ---------------------------------------------------------------- history
with tab_hist:
    st.subheader("Saved reports")
    only_me = st.checkbox("Show only this farmer", value=True)
    rows = db.fetch_data(farmer.name if only_me else None)
    if rows:
        hist = pd.DataFrame(rows)
        st.dataframe(hist, use_container_width=True, hide_index=True)
        if len(hist) > 1:
            trend = hist.sort_values("report_id")
            st.line_chart(trend, x="created_at", y="eco_score")
    else:
        st.write("No saved reports yet.")
