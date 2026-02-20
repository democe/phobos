import requests
from datetime import datetime, timezone
from sources.base import Item

AMBIENT_URL = "https://api.ambientweather.net/v1/devices"
NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"


def fetch(config: dict, browser) -> list[Item]:
    device = _fetch_ambient_device(config)
    current = device["lastData"]
    lat, lon = _get_coords(device, config)
    forecast = _fetch_nws_forecast(lat, lon)
    content = f"Current conditions: {current}\n\nForecast: {forecast}"
    item_id = f"weather-{current['dateutc']}"
    return [Item(
        id=item_id,
        source="weather",
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )]


def _fetch_ambient_device(config: dict) -> dict:
    resp = requests.get(AMBIENT_URL, params={
        "apiKey": config["ambient_api_key"],
        "applicationKey": config["ambient_app_key"],
    })
    resp.raise_for_status()
    return resp.json()[0]


def _get_coords(device: dict, config: dict) -> tuple[float, float]:
    coords = device.get("info", {}).get("coords", {}).get("coords", {})
    if coords.get("lat") and coords.get("lon"):
        return coords["lat"], coords["lon"]
    if "nws_lat" in config and "nws_lon" in config:
        return float(config["nws_lat"]), float(config["nws_lon"])
    raise ValueError(
        "Cannot determine station coordinates for NWS forecast. "
        "Add nws_lat and nws_lon to the weather config."
    )


def _fetch_nws_forecast(lat: float, lon: float) -> str:
    headers = {"User-Agent": "phobos-pipeline"}
    points_url = NWS_POINTS_URL.format(lat=lat, lon=lon)
    points_resp = requests.get(points_url, headers=headers)
    points_resp.raise_for_status()
    forecast_url = points_resp.json()["properties"]["forecast"]
    forecast_resp = requests.get(forecast_url, headers=headers)
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"]
    if not periods:
        return "No forecast available."
    return periods[0]["detailedForecast"]
