"""smartgardn_et0 — FAO-56 ET₀-based irrigation control."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.components.http import StaticPathConfig

_LOGGER = logging.getLogger(__name__)

from custom_components.smartgardn_et0.const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_RECALCULATE,
    SERVICE_START_ZONE,
    SERVICE_STOP_ALL,
    SERVICE_STOP_ZONE,
)
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator
from custom_components.smartgardn_et0.migration import async_setup_migration_service

_LOVELACE_CARDS = [
    "overview-card.js",
    "history-card.js",
    "settings-card.js",
    "ansaat-card.js",
]
_URL_BASE = "/smartgardn_et0_cards"


async def _async_register_lovelace_resources(hass: HomeAssistant) -> None:
    """Register static path and Lovelace resources."""
    # 1. Serve the www/ directory under /smartgardn_et0_cards
    www_path = Path(__file__).parent / "www"
    if www_path.is_dir() and hass.http:
        # Avoid hard setup failure if HA already knows this static path.
        with contextlib.suppress(Exception):
            await hass.http.async_register_static_paths([
                StaticPathConfig(_URL_BASE, str(www_path), cache_headers=False)
            ])
            _LOGGER.debug(f"Registered static path: {_URL_BASE} -> {www_path}")

    # 2. Register resources in Lovelace (storage mode only)
    lovelace_data = hass.data.get("lovelace")
    if not lovelace_data:
        _LOGGER.debug("Lovelace data not available - using YAML mode or Lovelace not loaded")
        return

    resource_collection = lovelace_data.get("resources")
    if resource_collection is None:
        _LOGGER.debug("No resource collection found in lovelace data")
        return

    # Only works in storage mode; skip YAML mode (read-only)
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
        if not isinstance(resource_collection, ResourceStorageCollection):
            _LOGGER.info("Lovelace in YAML mode - cards must be manually registered in ui-lovelace.yaml")
            return  # YAML mode
    except ImportError:
        _LOGGER.debug("Could not import ResourceStorageCollection")
        return

    # Ensure collection is loaded from disk
    if not getattr(resource_collection, "loaded", False):
        try:
            await resource_collection.async_load()
            resource_collection.loaded = True
        except Exception as e:
            _LOGGER.warning(f"Failed to load resource collection: {e}")
            return

    existing_urls = {item.get("url") for item in resource_collection.async_items()}

    for js_file in _LOVELACE_CARDS:
        url = f"{_URL_BASE}/{js_file}"
        if url not in existing_urls:
            try:
                await resource_collection.async_create_item({
                    "res_type": "module",
                    "url": url,
                })
                _LOGGER.debug(f"Registered Lovelace card: {url}")
            except Exception as e:
                _LOGGER.warning(f"Failed to register card {url}: {e}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up smartgardn_et0 from a config entry."""
    coordinator = IrrigationCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator}
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    entry.async_on_unload(coordinator.async_shutdown)

    # Register Lovelace custom cards
    await _async_register_lovelace_resources(hass)

    # Register hub device
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Bewässerung {entry.data.get('name', '')}",
        manufacturer="smartgardn_et0",
        model="FAO-56",
    )

    # Register one device per zone
    for zone_id, zone_data in entry.data.get("zones", {}).items():
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{entry.entry_id}_{zone_id}")},
            name=f"Zone {zone_data['zone_name']}",
            manufacturer="smartgardn_et0",
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

    async def handle_recalculate(call: ServiceCall) -> None:
        await coordinator._daily_calc()
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_START_ZONE):
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

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_ZONE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_ZONE,
            handle_stop_zone,
            schema=vol.Schema({vol.Required("zone"): cv.entity_id}),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_ALL):
        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_ALL,
            handle_stop_all,
            schema=vol.Schema({}),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RECALCULATE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RECALCULATE,
            handle_recalculate,
            schema=vol.Schema({}),
        )

    # Register migration service (Phase 9)
    await async_setup_migration_service(hass, entry.entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
