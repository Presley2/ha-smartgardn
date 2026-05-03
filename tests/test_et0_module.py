"""Tests for ET₀ module refactoring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartgardn_et0.const import DOMAIN
from custom_components.smartgardn_et0.irrigation.et0 import compute_et0_with_fallback


@pytest.mark.asyncio
@pytest.mark.usefixtures("enable_custom_integrations")
async def test_compute_et0_with_fallback_no_temp_data() -> None:
    """Test ET₀ computation with missing temperature data."""
    hass = MagicMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test",
            "latitude": 50.0,
            "elevation": 100,
            "temp_entity": "sensor.temp",
            "et_methode": "fao56",
        },
    )

    with patch(
        "custom_components.smartgardn_et0.irrigation.et0.get_daily_minmax",
        return_value=(None, None),
    ):
        et0, method, fallback = await compute_et0_with_fallback(hass, entry)

    assert et0 == 0.0
    assert method == "last_known"
    assert fallback is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("enable_custom_integrations")
async def test_compute_et0_hargreaves_fallback() -> None:
    """Test ET₀ computation falls back to Hargreaves when PM inputs missing."""
    hass = MagicMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test",
            "latitude": 50.0,
            "elevation": 100,
            "temp_entity": "sensor.temp",
            "humidity_entity": "sensor.humidity",
            "solar_entity": None,
            "wind_entity": None,
            "et_methode": "fao56",
        },
    )

    with patch(
        "custom_components.smartgardn_et0.irrigation.et0.get_daily_minmax",
        side_effect=[(15.0, 25.0), (40.0, 60.0)],
    ), patch(
        "custom_components.smartgardn_et0.irrigation.et0.read_sensor",
        return_value=None,
    ), patch(
        "custom_components.smartgardn_et0.irrigation.et0.calc_et0_hargreaves",
        return_value=5.0,
    ):
        et0, method, fallback = await compute_et0_with_fallback(hass, entry)

    assert et0 == 5.0
    assert method == "hargreaves"
    assert fallback is True
