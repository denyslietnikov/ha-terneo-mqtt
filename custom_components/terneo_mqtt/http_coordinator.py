"""HTTP telemetry coordinator for Terneo devices."""
import asyncio
import aiohttp
import json
import logging
from typing import Any, Dict, Optional
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)

class TerneoHTTPCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching HTTP telemetry from Terneo devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        sn: Optional[str] = None,
        poll_interval: int = 60,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Terneo HTTP Telemetry",
            update_interval=dt.timedelta(seconds=poll_interval),
        )
        self.host = host
        self.sn = sn
        self._session = aiohttp.ClientSession()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Terneo HTTP API."""
        try:
            url = f"http://{self.host}/api.cgi"
            payload = {"cmd": 4}
            if self.sn:
                payload["sn"] = self.sn

            async with self._session.post(url, json=payload, timeout=10) as response:
                if response.status != 200:
                    raise UpdateFailed(f"HTTP {response.status}: {await response.text()}")
                
                data = await response.json()
                _LOGGER.debug("HTTP telemetry data: %s", data)
                return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching HTTP telemetry: {err}")

    async def async_close(self) -> None:
        """Close the session."""
        await self._session.close()