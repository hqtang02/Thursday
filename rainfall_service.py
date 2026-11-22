
import json
from urllib.parse import urlencode
from urllib.request import urlopen


def fetch_json(url):
    try:
        with urlopen(url, timeout=15) as response:
            return json.load(response)
    except Exception as exc:
        raise RuntimeError(
            "无法连接天气服务，请检查网络连接"
        ) from exc


def search_city(city_name):
    """Search cities worldwide using Open-Meteo."""

    city_name = city_name.strip()

    if len(city_name) < 2:
        raise ValueError("请输入至少两个字符的城市名称")

    params = urlencode({
        "name": city_name,
        "count": 10,
        "language": "en",
        "format": "json",
    })

    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + params
    )

    data = fetch_json(url)
    results = data.get("results", [])

    if not results:
        raise ValueError("未找到城市，请尝试英文名称")

    return results


def get_rainfall_forecast(latitude, longitude):
    """Get seven-day precipitation forecast in mm."""

    latitude = float(latitude)
    longitude = float(longitude)

    if not -90 <= latitude <= 90:
        raise ValueError("纬度无效")

    if not -180 <= longitude <= 180:
        raise ValueError("经度无效")

    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum",
        "forecast_days": 7,
        "timezone": "auto",
    })

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + params
    )

    data = fetch_json(url)
    daily = data.get("daily", {})

    dates = daily.get("time", [])
    rainfall = daily.get("precipitation_sum", [])

    if len(dates) != 7 or len(rainfall) != 7:
        raise ValueError("天气数据不完整")

    if any(v is None or v < 0 for v in rainfall):
        raise ValueError("降雨数据存在异常")

    return dates, rainfall
