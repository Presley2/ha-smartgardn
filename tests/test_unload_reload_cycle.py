"""Tests for __init__.py setup/unload lifecycle."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_et0.const import DOMAIN


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Create a minimal config entry for testing."""
    return MockConfigEntry(domain=DOMAIN, title="Test Anlage", data={})


async def test_setup_then_unload_clears_data(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Setup populates hass.data; unload removes the entry cleanly."""
    with (
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        from custom_components.irrigation_et0 import async_setup_entry, async_unload_entry

        result = await async_setup_entry(hass, mock_entry)
        assert result is True
        assert DOMAIN in hass.data
        assert mock_entry.entry_id in hass.data[DOMAIN]

        unload_result = await async_unload_entry(hass, mock_entry)
        assert unload_result is True
        assert mock_entry.entry_id not in hass.data.get(DOMAIN, {})
