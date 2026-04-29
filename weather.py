import logging
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


def _resolve_bind_host() -> str:
    """Listen address: explicit FASTMCP_HOST, else 0.0.0.0 when PORT is set (e.g. Cloud Run)."""
    if os.environ.get("FASTMCP_HOST"):
        return os.environ["FASTMCP_HOST"]
    if os.environ.get("PORT") is not None:
        return "0.0.0.0"
    return "127.0.0.1"


def _resolve_bind_port() -> int:
    """Port: Cloud Run and others set PORT; locally FASTMCP_PORT or 8000."""
    if os.environ.get("PORT") is not None:
        return int(os.environ["PORT"])
    return int(os.environ.get("FASTMCP_PORT", "8000"))


# HTTP MCP (Streamable HTTP). Override with FASTMCP_HOST / FASTMCP_PORT; Cloud Run uses PORT.
mcp = FastMCP(
    "weather",
    host=_resolve_bind_host(),
    port=_resolve_bind_port(),
)


@mcp.custom_route("/", methods=["GET"])
async def _root(_request: Request) -> JSONResponse:
    """Non-MCP GET / so Cloud Run / browser checks show something useful."""
    p = mcp.settings.streamable_http_path
    return JSONResponse(
        {
            "status": "ok",
            "mcp_streamable_http_path": p,
            "hint": f"Configure MCP Streamable HTTP clients with URL path {p} on this host (e.g. https://<host>{p}).",
        }
    )


# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get("event", "Unknown")}
Area: {props.get("areaDesc", "Unknown")}
Severity: {props.get("severity", "Unknown")}
Description: {props.get("description", "No description available")}
Instructions: {props.get("instruction", "No specific instructions provided")}
"""

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period["name"]}:
Temperature: {period["temperature"]}°{period["temperatureUnit"]}
Wind: {period["windSpeed"]} {period["windDirection"]}
Forecast: {period["detailedForecast"]}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


@mcp.prompt(
    title="Alerts for a US state",
    description="Use get_alerts with a two-letter state code (e.g. CA, TX).",
)
def alerts_for_state(state: str) -> list[dict[str, str]]:
    code = state.strip().upper()
    return [
        {
            "role": "user",
            "content": (
                f"Call get_alerts with state={code!r}, then summarize active NWS alerts: "
                "what is happening, where, severity, and any recommended actions."
            ),
        }
    ]


@mcp.prompt(
    title="Forecast at coordinates",
    description="Use get_forecast with decimal latitude and longitude (NWS covers the US).",
)
def forecast_at_location(latitude: float, longitude: float) -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": (
                f"Call get_forecast with latitude={latitude} and longitude={longitude}. "
                "Summarize the next few periods for someone planning their day."
            ),
        }
    ]


@mcp.prompt(
    title="Alerts + local forecast",
    description="Combine get_alerts for a state with get_forecast for a point in that region.",
)
def alerts_and_forecast(state: str, latitude: float, longitude: float) -> list[dict[str, str]]:
    code = state.strip().upper()
    return [
        {
            "role": "user",
            "content": (
                f"First call get_alerts with state={code!r}. "
                f"Then call get_forecast with latitude={latitude} and longitude={longitude}. "
                "Give a short briefing: headline risks from alerts, then how the local forecast fits."
            ),
        }
    ]


def main() -> None:
    base = f"http://{mcp.settings.host}:{mcp.settings.port}"
    path = mcp.settings.streamable_http_path
    logging.info("MCP Streamable HTTP at %s%s", base, path)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info("Starting weather MCP server")
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Weather MCP server stopped (interrupt)")