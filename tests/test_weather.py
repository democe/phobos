# tests/test_weather.py
from sources import weather
from unittest.mock import MagicMock
import pytest

WEATHER_CONFIG = {
    "ambient_api_key": "k",
    "ambient_app_key": "a",
    "station_mac": "AA:BB:CC",
    "prompt": "summarize",
}

def _make_ambient_resp(with_coords=False):
    device = {"lastData": {"tempf": 72.0, "humidity": 55, "windspeedmph": 10, "dateutc": 1700000000000}}
    if with_coords:
        device["info"] = {"coords": {"coords": {"lat": 43.615, "lon": -116.202}}}
    return device

def _make_points_resp():
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"properties": {"forecast": "https://api.weather.gov/gridpoints/BOI/1,2/forecast"}}
    return resp

def _make_forecast_resp(forecast="Sunny and warm."):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"properties": {"periods": [{"name": "Today", "detailedForecast": forecast}]}}
    return resp

def _make_ambient_api_resp(device):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = [device]
    return resp

def test_fetch_uses_coords_from_ambient_response(mocker):
    mock_get = mocker.patch("sources.weather.requests.get")
    mock_get.side_effect = [
        _make_ambient_api_resp(_make_ambient_resp(with_coords=True)),
        _make_points_resp(),
        _make_forecast_resp(),
    ]
    items = weather.fetch(WEATHER_CONFIG, browser=None)
    assert len(items) == 1
    assert "72.0" in items[0].content
    assert "Sunny and warm." in items[0].content
    # Verify lat/lon from device coords were used in the NWS call
    points_call_url = mock_get.call_args_list[1][0][0]
    assert "43.615" in points_call_url
    assert "-116.202" in points_call_url

def test_fetch_falls_back_to_config_coords(mocker):
    mock_get = mocker.patch("sources.weather.requests.get")
    config_with_coords = {**WEATHER_CONFIG, "nws_lat": "43.615", "nws_lon": "-116.202"}
    mock_get.side_effect = [
        _make_ambient_api_resp(_make_ambient_resp(with_coords=False)),
        _make_points_resp(),
        _make_forecast_resp(),
    ]
    items = weather.fetch(config_with_coords, browser=None)
    assert len(items) == 1

def test_fetch_raises_if_no_coords_available(mocker):
    mock_get = mocker.patch("sources.weather.requests.get")
    mock_get.side_effect = [
        _make_ambient_api_resp(_make_ambient_resp(with_coords=False)),
    ]
    with pytest.raises(ValueError, match="nws_lat"):
        weather.fetch(WEATHER_CONFIG, browser=None)

def test_fetch_item_has_stable_id(mocker):
    mock_get = mocker.patch("sources.weather.requests.get")
    empty_forecast = MagicMock()
    empty_forecast.raise_for_status = lambda: None
    empty_forecast.json.return_value = {"properties": {"periods": []}}
    mock_get.side_effect = [
        _make_ambient_api_resp(_make_ambient_resp(with_coords=True)),
        _make_points_resp(),
        empty_forecast,
    ]
    items = weather.fetch(WEATHER_CONFIG, browser=None)
    assert items[0].id == "weather-1700000000000"
