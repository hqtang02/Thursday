
# weather_api.py
"""Retrieve historical daily precipitation from Open-Meteo."""

from datetime import date, timedelta
import math

import requests


API_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_historical_rainfall(latitude, longitude, days=30):
    """Return historical daily precipitation in millimetres."""

    for name, value, lower, upper in [
        ("latitude", latitude, -90, 90),
        ("longitude", longitude, -180, 180),
    ]:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not lower <= value <= upper
        ):
            raise ValueError(f"Invalid {name}.")

    if isinstance(days, bool) or not isinstance(days, int):
        raise TypeError("days must be an integer.")

    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365.")

    # Allow several days for historical data availability.
    end_date = date.today() - timedelta(days=7)
    start_date = end_date - timedelta(days=days - 1)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "auto",
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError(
            f"Unable to retrieve weather data: {error}"
        ) from error

    daily = data.get("daily") or {}
    dates = daily.get("time")
    rainfall = daily.get("precipitation_sum")

    if not isinstance(dates, list) or not isinstance(rainfall, list):
        raise ValueError("Missing daily precipitation data.")

    if len(dates) != days or len(rainfall) != days:
        raise ValueError("Incomplete rainfall data returned by API.")

    for value in rainfall:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("Invalid precipitation value returned.")

    return {
        "dates": dates,
        "rainfall_mm": rainfall,
        "latitude": latitude,
        "longitude": longitude,
        "source": "Open-Meteo Historical Weather API",
    }
