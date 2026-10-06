"""EcoCalculator class: carbon footprint + eco-score.

Emission factors are indicative averages (kg CO2e) and are kept in one place so
agricultural experts can review/update them.
"""
from dataclasses import dataclass, asdict
from .models import Farmer

EMISSION_FACTORS = {
    # kg CO2e per kg of fertilizer product applied (manufacture + field N2O, approx.)
    "fertilizer": {"Urea": 1.6, "DAP": 1.7, "NPK": 1.4, "Organic compost": 0.1, "None": 0.0},
    "grid_electricity": 0.82,   # kg CO2e per kWh (Indian grid average, approx.)
    "diesel": 2.68,             # kg CO2e per litre of diesel
    "diesel_pump_l_per_hour": 1.2,  # litres per hour for a ~5 HP diesel pump
}

# Intensity (kg CO2e per hectare per season) at which the eco-score reaches 0.
WORST_INTENSITY = 4000.0


@dataclass
class FootprintResult:
    crop: float
    fertilizer: float
    irrigation: float
    machinery: float
    total: float
    per_hectare: float
    eco_score: int
    rating: str

    def breakdown(self) -> dict:
        return {"Crop (field emissions)": self.crop, "Fertilizer": self.fertilizer,
                "Irrigation": self.irrigation, "Machinery": self.machinery}

    def to_dict(self) -> dict:
        return asdict(self)


class EcoCalculator:
    def __init__(self, emission_factors: dict | None = None, crop_base_emission: float = 0.0):
        self.factors = emission_factors or EMISSION_FACTORS
        self.crop_base_emission = crop_base_emission  # kg CO2e / ha

    def calculate_footprint(self, farmer: Farmer) -> FootprintResult:
        f = self.factors
        crop = self.crop_base_emission * farmer.land_area
        fert = farmer.fertilizer_used * f["fertilizer"].get(farmer.fertilizer_type, 0.0)

        if farmer.pump_type == "Electric":
            irrigation = farmer.irrigation_hours * farmer.pump_kw * f["grid_electricity"]
        elif farmer.pump_type == "Diesel":
            irrigation = farmer.irrigation_hours * f["diesel_pump_l_per_hour"] * f["diesel"]
        else:
            irrigation = 0.0

        machinery = farmer.machinery_diesel * f["diesel"]
        total = crop + fert + irrigation + machinery
        per_ha = total / farmer.land_area
        score = self.eco_score(per_ha)
        return FootprintResult(round(crop, 1), round(fert, 1), round(irrigation, 1),
                               round(machinery, 1), round(total, 1), round(per_ha, 1),
                               score, self.rating(score))

    @staticmethod
    def eco_score(per_hectare: float) -> int:
        score = 100 * (1 - per_hectare / WORST_INTENSITY)
        return int(max(0, min(100, round(score))))

    @staticmethod
    def rating(score: int) -> str:
        if score >= 80:
            return "Excellent"
        if score >= 60:
            return "Good"
        if score >= 40:
            return "Moderate"
        return "Needs improvement"
