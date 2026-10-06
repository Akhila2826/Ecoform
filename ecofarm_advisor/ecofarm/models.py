"""Farmer class (see class diagram): holds the details a farmer enters."""
from dataclasses import dataclass, asdict

ACRE_TO_HA = 0.404686

FERTILIZER_TYPES = ["Urea", "DAP", "NPK", "Organic compost", "None"]
PUMP_TYPES = ["Electric", "Diesel", "Solar / Rain-fed (none)"]


@dataclass
class Farmer:
    name: str
    land_area: float            # in hectares
    crop_type: str
    fertilizer_type: str = "Urea"
    fertilizer_used: float = 0.0   # kg per season (total)
    pump_type: str = "Electric"
    irrigation_hours: float = 0.0  # pump hours per season
    pump_kw: float = 3.7           # ~5 HP pump
    machinery_diesel: float = 0.0  # litres of diesel per season

    def validate(self) -> list[str]:
        errors = []
        if not self.name.strip():
            errors.append("Please enter the farmer's name.")
        if self.land_area <= 0:
            errors.append("Land area must be greater than zero.")
        for label, value in [("Fertilizer", self.fertilizer_used),
                             ("Irrigation hours", self.irrigation_hours),
                             ("Machinery diesel", self.machinery_diesel)]:
            if value < 0:
                errors.append(f"{label} cannot be negative.")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)

    # enterDetails() from the class diagram; the UI plays viewResults().
    @classmethod
    def enter_details(cls, **kwargs) -> "Farmer":
        return cls(**kwargs)
