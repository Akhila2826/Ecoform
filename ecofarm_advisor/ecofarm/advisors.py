"""CompanionCropAdvisor, PollinatorAdvisor and the data loader (DatabaseManager.fetchData)."""
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "crop_pollinator_data.json"


def load_crop_data(path: Path = DATA_FILE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["crops"]


class CompanionCropAdvisor:
    def __init__(self, crop_data: dict):
        self.crop_data = crop_data

    def suggest_crops(self, crop_name: str) -> list[dict]:
        return self.crop_data.get(crop_name, {}).get("companions", [])


class PollinatorAdvisor:
    def __init__(self, crop_data: dict):
        self.crop_data = crop_data

    def suggest_plants(self, crop_name: str) -> list[dict]:
        return self.crop_data.get(crop_name, {}).get("pollinators", [])


def reduction_tips(result, farmer) -> list[str]:
    """Rule-based tips targeting the biggest emission sources (also the AI fallback)."""
    tips = []
    if farmer.crop_type == "Rice":
        tips.append("Use alternate wetting and drying (AWD) in paddy fields - it can cut methane substantially.")
    if result.fertilizer > 0.3 * result.total and farmer.fertilizer_type in ("Urea", "DAP", "NPK"):
        tips.append("Fertilizer is a major source: apply based on a soil test, split doses, and "
                    "replace part with compost or a legume companion crop.")
    if farmer.pump_type == "Diesel" and result.irrigation > 0:
        tips.append("Switch the diesel pump to a solar or electric pump and use drip irrigation to save fuel and water.")
    elif farmer.pump_type == "Electric" and result.irrigation > 0.25 * result.total:
        tips.append("Schedule irrigation carefully, and consider a solar pump or drip irrigation.")
    if result.machinery > 0.2 * result.total:
        tips.append("Reduce tillage passes (minimum/zero tillage) and keep tractors well maintained to save diesel.")
    if not tips:
        tips.append("Your footprint is already low - keep using residue mulching and crop rotation.")
    return tips
