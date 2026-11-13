"""Metric calculations. Each metric has its own module and a .md that defines it:

  covered_ground.py   CANOPY.md            building canopies, road pergola, covered ground
  ecosystem.py        ECOSYSTEM_SCORE.md   ecosystem score (habitat, diversity, connectivity, resilience),
                                           shown in the dashboard as the synergy index
  heat.py             HEAT_STRESS.md       share of the route in shade at 15:00 on 21 June
  wind.py             WIND_INDEX.md        share of tall-building facade with shelter next to it
  water.py            WATER.md             share of a 70 mm storm kept on site
Green facades are computed in backend/facades.py (GREEN_FACADES.md).
"""
from .covered_ground import covered_ground
from .ecosystem import ecosystem_score
from .heat import heat_stress
from .wind import wind_index
from .water import water_retention

__all__ = ["covered_ground", "ecosystem_score", "heat_stress", "wind_index", "water_retention"]
