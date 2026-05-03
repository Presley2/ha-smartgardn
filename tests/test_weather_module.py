"""Tests for weather module refactoring."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.smartgardn_et0.weather.sensors import read_sensor


@pytest.mark.asyncio
async def test_read_sensor_with_valid_state(hass: HomeAssistant) -> None:
    """Test reading a sensor with valid numeric state."""
    hass.states.set("sensor.temperature", "25.5")
    value = read_sensor(hass, "sensor.temperature")
    assert value == 25.5


def test_read_sensor_with_unavailable(hass: HomeAssistant) -> None:
    """Test reading unavailable sensor returns None."""
    hass.states.set("sensor.temperature", "unavailable")
    value = read_sensor(hass, "sensor.temperature")
    assert value is None


def test_read_sensor_with_unknown(hass: HomeAssistant) -> None:
    """Test reading unknown sensor returns None."""
    hass.states.set("sensor.temperature", "unknown")
    value = read_sensor(hass, "sensor.temperature")
    assert value is None


def test_read_sensor_with_none_entity(hass: HomeAssistant) -> None:
    """Test reading None entity returns None."""
    value = read_sensor(hass, None)
    assert value is None


def test_read_sensor_with_nonexistent_entity(hass: HomeAssistant) -> None:
    """Test reading nonexistent entity returns None."""
    value = read_sensor(hass, "sensor.nonexistent")
    assert value is None


def test_read_sensor_with_invalid_number(hass: HomeAssistant) -> None:
    """Test reading sensor with non-numeric state returns None."""
    hass.states.set("sensor.text", "not_a_number")
    value = read_sensor(hass, "sensor.text")
    assert value is None
