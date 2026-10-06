import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecofarm.advisors import CompanionCropAdvisor, PollinatorAdvisor, load_crop_data, reduction_tips
from ecofarm.ai_advisor import generate_advice, chat
from ecofarm.database import DatabaseManager
from ecofarm.eco_calculator import EcoCalculator
from ecofarm.models import Farmer
from ecofarm.report import build_pdf

DATA = load_crop_data()


def make_farmer(**kw):
    base = dict(name="Ramesh", land_area=2.0, crop_type="Wheat", fertilizer_type="Urea",
                fertilizer_used=200, pump_type="Electric", irrigation_hours=100, pump_kw=3.7,
                machinery_diesel=40)
    base.update(kw)
    return Farmer(**base)


def test_footprint_math():
    r = EcoCalculator(crop_base_emission=350).calculate_footprint(make_farmer())
    assert r.crop == 700.0
    assert r.fertilizer == 320.0                      # 200 kg * 1.6
    assert round(r.irrigation, 1) == round(100 * 3.7 * 0.82, 1)
    assert r.machinery == round(40 * 2.68, 1)
    assert abs(r.total - (r.crop + r.fertilizer + r.irrigation + r.machinery)) < 0.5
    assert 0 <= r.eco_score <= 100


def test_score_bounds_and_rating():
    assert EcoCalculator.eco_score(0) == 100
    assert EcoCalculator.eco_score(10**6) == 0
    assert EcoCalculator.rating(85) == "Excellent"
    assert EcoCalculator.rating(10) == "Needs improvement"


def test_rice_is_worse_than_chickpea():
    f = make_farmer()
    rice = EcoCalculator(crop_base_emission=DATA["Rice"]["base_emission"]).calculate_footprint(f)
    chick = EcoCalculator(crop_base_emission=DATA["Chickpea"]["base_emission"]).calculate_footprint(f)
    assert rice.eco_score < chick.eco_score


def test_validation():
    assert make_farmer(land_area=0).validate()
    assert make_farmer(name=" ").validate()
    assert not make_farmer().validate()


def test_advisors_cover_all_crops():
    comp, poll = CompanionCropAdvisor(DATA), PollinatorAdvisor(DATA)
    for crop in DATA:
        assert comp.suggest_crops(crop) and poll.suggest_plants(crop)
    assert comp.suggest_crops("Unknown") == []


def test_database_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        db = DatabaseManager(os.path.join(d, "t.db"))
        f = make_farmer()
        r = EcoCalculator(crop_base_emission=350).calculate_footprint(f)
        db.save_data(f, r, "summary")
        rows = db.fetch_data("ramesh")
        assert len(rows) == 1 and rows[0]["eco_score"] == r.eco_score
        assert db.fetch_data("nobody") == []
        db.delete_all()
        assert db.fetch_data() == []


def test_ai_fallback_without_key(monkeypatch=None):
    os.environ.pop("ANTHROPIC_API_KEY", None)
    f = make_farmer()
    r = EcoCalculator(crop_base_emission=350).calculate_footprint(f)
    comp, poll = DATA["Wheat"]["companions"], DATA["Wheat"]["pollinators"]
    text, source = generate_advice(f, r, comp, poll)
    assert source == "rule-based" and "Eco-score" in text
    assert "ANTHROPIC_API_KEY" in chat("hi", [], f, r, comp, poll)
    assert reduction_tips(r, f)


def test_pdf_generation():
    f = make_farmer()
    r = EcoCalculator(crop_base_emission=350).calculate_footprint(f)
    pdf = build_pdf(f, r, DATA["Wheat"]["companions"], DATA["Wheat"]["pollinators"], "**Hi** <b>&")
    assert pdf.startswith(b"%PDF")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
