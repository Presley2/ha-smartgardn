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
_STATIC_PATH_REGISTERED = False  # Track if static path is already registered


async def _async_register_lovelace_resources(hass: HomeAssistant, *, skip_static: bool = False) -> None:
    """Register static path and Lovelace resources.

    Args:
        hass: Home Assistant instance
        skip_static: If True, skip static path registration (already done once per HA session)
    """
    global _STATIC_PATH_REGISTERED

    # 1. Serve the www/ directory under /smartgardn_et0_cards
    # (Only need to do this ONCE per HA session, not on every config entry reload)
    if not skip_static and not _STATIC_PATH_REGISTERED:
        www_path = Path(__file__).parent / "www"
        if not www_path.is_dir():
            _LOGGER.warning(f"www directory not found at {www_path}")
            return

        if not hass.http:
            _LOGGER.warning("HTTP component not available")
            return

        # Register static path - this is the core requirement
        try:
            await hass.http.async_register_static_paths([
                StaticPathConfig(_URL_BASE, str(www_path), cache_headers=False)
            ])
            _LOGGER.info(f"✓ Registered static path: {_URL_BASE} -> {www_path}")
            _STATIC_PATH_REGISTERED = True
        except Exception as e:
            _LOGGER.error(f"Failed to register static path: {e}")
            return

    # 2. ALSO register via Lovelace resources (for Storage Mode support)
    # This can be done on every reload since it's safe/idempotent
    await _async_try_register_lovelace_storage(hass)


async def _async_try_register_lovelace_storage(hass: HomeAssistant) -> None:
    """Try to register in Lovelace storage collection (Storage Mode only)."""
    lovelace_data = hass.data.get("lovelace")
    if not lovelace_data:
        return

    resource_collection = lovelace_data.get("resources")
    if resource_collection is None:
        return

    # Only works in storage mode
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
        if not isinstance(resource_collection, ResourceStorageCollection):
            return
    except (ImportError, AttributeError):
        return

    # Ensure loaded
    if not getattr(resource_collection, "loaded", False):
        try:
            await resource_collection.async_load()
            resource_collection.loaded = True
        except Exception:
            return

    # Register each card
    existing_urls = {item.get("url") for item in resource_collection.async_items()}
    for js_file in _LOVELACE_CARDS:
        url = f"{_URL_BASE}/{js_file}"
        if url not in existing_urls:
            try:
                await resource_collection.async_create_item({
                    "res_type": "module",
                    "url": url,
                })
                _LOGGER.debug(f"Registered Lovelace resource: {url}")
            except Exception:
                pass


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up smartgardn_et0 from a config entry."""
    # Register Lovelace custom cards FIRST (so they're available before UI loads)
    # Static path is registered only once per HA session (not on every reload)
    await _async_register_lovelace_resources(hass, skip_static=False)

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
    # Re-register Lovelace resources (safe/idempotent, skips static path)
    await _async_register_lovelace_resources(hass, skip_static=True)
    # Reload the entry
    await hass.config_entries.async_reload(entry.entry_id)
