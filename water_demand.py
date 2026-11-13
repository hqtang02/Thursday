
# water_demand.py
"""Calculate estimated daily household rainwater demand."""

WATER_RATES = {
    "vegetables": 4.0,
    "flowers": 3.0,
    "trees": 2.0,
    "lawn": 5.0,
}


def calculate_garden_demand(area_m2, plant_type):
    """Return estimated daily irrigation demand in litres."""
    if not isinstance(area_m2, (int, float)) or isinstance(area_m2, bool):
        raise TypeError("Area must be a number.")

    if area_m2 < 0:
        raise ValueError("Area cannot be negative.")

    if plant_type not in WATER_RATES:
        raise ValueError(f"Unsupported plant type: {plant_type}")

    return area_m2 * WATER_RATES[plant_type]


def calculate_toilet_demand(people):
    """Return estimated daily toilet flushing demand in litres."""
    if isinstance(people, bool) or not isinstance(people, int):
        raise TypeError("Number of people must be an integer.")

    if people < 0:
        raise ValueError("Number of people cannot be negative.")

    return people * 25.0


def calculate_total_demand(
    garden_area=0,
    plant_type="vegetables",
    lawn_area=0,
    people=0,
):
    """Return a breakdown of daily water demand."""
    garden = calculate_garden_demand(garden_area, plant_type)
    lawn = calculate_garden_demand(lawn_area, "lawn")
    toilet = calculate_toilet_demand(people)

    return {
        "garden_l": garden,
        "lawn_l": lawn,
        "toilet_l": toilet,
        "total_l": garden + lawn + toilet,
    }
