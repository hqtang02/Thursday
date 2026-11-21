
# calculator.py
"""Daily rainwater collection and allocation simulation."""

import math


def _validate_number(name, value, allow_zero=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    if value < 0 or (not allow_zero and value == 0):
        raise ValueError(f"{name} must be positive or zero as allowed.")


def simulate_day(
    start_l,
    rain_mm,
    roof_area_m2,
    efficiency,
    tank_capacity_l,
    primary_demand_l,
    secondary_demand_l,
    reserve_l=0,
):
    """Simulate one day of collection, overflow and allocation."""

    for name, value in {
        "start_l": start_l,
        "rain_mm": rain_mm,
        "roof_area_m2": roof_area_m2,
        "tank_capacity_l": tank_capacity_l,
        "primary_demand_l": primary_demand_l,
        "secondary_demand_l": secondary_demand_l,
        "reserve_l": reserve_l,
    }.items():
        _validate_number(name, value)

    _validate_number("efficiency", efficiency)

    if not 0 <= efficiency <= 1:
        raise ValueError("Efficiency must be between 0 and 1.")

    if start_l > tank_capacity_l:
        raise ValueError("Initial storage exceeds tank capacity.")

    if reserve_l > tank_capacity_l:
        raise ValueError("Reserve exceeds tank capacity.")

    collected_l = rain_mm * roof_area_m2 * efficiency

    total_available = start_l + collected_l

    overflow_l = max(
        0.0,
        total_available - tank_capacity_l
    )

    available_l = min(
        total_available,
        tank_capacity_l
    )

    primary_used_l = min(
        primary_demand_l,
        available_l
    )

    external_supply_l = (
        primary_demand_l - primary_used_l
    )

    after_primary_l = (
        available_l - primary_used_l
    )

    secondary_used_l = min(
        secondary_demand_l,
        max(0.0, after_primary_l - reserve_l)
    )

    secondary_shortage_l = (
        secondary_demand_l - secondary_used_l
    )

    end_l = (
        after_primary_l - secondary_used_l
    )

    return {
        "start_l": start_l,
        "rain_mm": rain_mm,
        "collected_l": collected_l,
        "overflow_l": overflow_l,
        "primary_used_l": primary_used_l,
        "external_supply_l": external_supply_l,
        "secondary_used_l": secondary_used_l,
        "secondary_shortage_l": secondary_shortage_l,
        "end_l": end_l,
    }


def simulate_period(rainfall_mm, **parameters):
    """Simulate multiple days using the previous day's ending storage."""

    results = []
    current_storage = parameters.pop("initial_storage_l")

    for day, rain in enumerate(rainfall_mm, start=1):
        result = simulate_day(
            start_l=current_storage,
            rain_mm=rain,
            **parameters
        )

        result["day"] = day
        results.append(result)
        current_storage = result["end_l"]

    return results
