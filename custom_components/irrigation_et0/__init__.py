"""irrigation_et0 — FAO-56 ET₀-based irrigation control."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from custom_components.irrigation_et0.const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_START_ZONE,
    SERVICE_STOP_ALL,
    SERVICE_STOP_ZONE,
)
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up irrigation_et0 from a config entry."""
    coordinator = IrrigationCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator}
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    entry.async_on_unload(coordinator.async_shutdown)

    # Register hub device
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Bewässerung {entry.data.get('name', '')}",
        manufacturer="irrigation_et0",
        model="FAO-56",
    )

    # Register one device per zone
    for zone_id, zone_data in entry.data.get("zones", {}).items():
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{entry.entry_id}_{zone_id}")},
            name=f"Zone {zone_data['zone_name']}",
            manufacturer="irrigation_et0",
            model="Irrigation Zone",
            via_device=(DOMAIN, entry.entry_id),
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (Phase 6)
    async def handle_start_zone(call: ServiceCall) -> None:
        zone_entity = call.data["zone"]
        dauer = call.data["dauer_min"]
        await coordinator.async_start_zone(zone_entity, dauer)

    async def handle_stop_zone(call: ServiceCall) -> None:
        zone_entity = call.data["zone"]
        await coordinator.async_stop_zone(zone_entity)

    async def handle_stop_all(call: ServiceCall) -> None:
        await coordinator.async_stop_all()

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_ZONE,
        handle_start_zone,
        schema=vol.Schema(
            {
                vol.Required("zone"): cv.entity_id,
                vol.Required("dauer_min"): vol.All(vol.Coerce(float), vol.Range(min=1, max=240)),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_ZONE,
        handle_stop_zone,
        schema=vol.Schema({vol.Required("zone"): cv.entity_id}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_ALL,
        handle_stop_all,
        schema=vol.Schema({}),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
