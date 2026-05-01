"""Lovelace card integration for smartgardn_et0."""

from pathlib import Path
import json

CARDS = {
    "overview-card.js": "Overview: zone status grid with NFK, ETc, rain, irrigation",
    "history-card.js": "History: daily water balance trends per zone",
    "settings-card.js": "Settings: zone configuration with sliders and dropdowns",
    "ansaat-card.js": "Ansaat: seed watering mode with interval/duration/window config",
}


async def async_setup_lovelace_resources(hass, entry):
    """Register Lovelace card resources for the integration."""
    # The cards are automatically served by HA's `/static/community/` endpoint
    # This function is for future extensibility (e.g., dynamic resource registration)
    pass
