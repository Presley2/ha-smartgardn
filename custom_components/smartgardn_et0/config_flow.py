"""Config flow for smartgardn_et0."""

from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlowWithConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

from custom_components.smartgardn_et0.const import DOMAIN, SOIL_TYPES, ZONE_TYPE_KC

_ENTITY_SENSOR = EntitySelector(EntitySelectorConfig(domain="sensor"))
_ENTITY_SWITCH = EntitySelector(EntitySelectorConfig(domain="switch"))

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("name"): TextSelector(),
        vol.Required("location"): LocationSelector(),
        vol.Required("elevation"): NumberSelector(
            NumberSelectorConfig(min=-500, max=9000, step=1, mode=NumberSelectorMode.BOX)
        ),
    }
)

_OPTIONAL_WEATHER_FIELDS = (
    "humidity_entity",
    "solar_entity",
    "solar_sensor_type",
    "wind_entity",
    "rain_entity",
)

STEP_WEATHER_SCHEMA = vol.Schema(
    {
        vol.Required("temp_entity"): _ENTITY_SENSOR,
        vol.Optional("humidity_entity"): _ENTITY_SENSOR,
        vol.Optional("solar_entity"): _ENTITY_SENSOR,
        vol.Optional("solar_sensor_type"): SelectSelector(
            SelectSelectorConfig(
                options=[
                    "w_m2",      # W/m² (Photodiode, Pyranometer)
                    "lux",       # Lux (simple light sensors)
                    "par",       # PAR (photosynthetically active radiation)
                ]
            )
        ),
        vol.Optional("wind_entity"): _ENTITY_SENSOR,
        vol.Optional("rain_entity"): _ENTITY_SENSOR,
    }
)

STEP_SOLAR_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("solar_sensor_type"): SelectSelector(
            SelectSelectorConfig(
                options=[
                    "w_m2",      # W/m² (Photodiode, Pyranometer) — multiply by 0.0864
                    "lux",       # Lux — divide by 54000 then multiply by 0.0864
                    "par",       # PAR µmol/m²/s — multiply by 0.51 then divide by 0.0864
                    "none",      # No solar sensor (fallback to Hargreaves)
                ]
            )
        ),
    }
)

STEP_HARDWARE_SCHEMA = vol.Schema(
    {
        vol.Optional("trafo_entity"): _ENTITY_SWITCH,
        vol.Required("frost_threshold", default=4.0): NumberSelector(
            NumberSelectorConfig(min=-10, max=15, step=0.5, mode=NumberSelectorMode.BOX)
        ),
    }
)

STEP_ZONE_SCHEMA = vol.Schema(
    {
        vol.Required("zone_name"): TextSelector(),
        vol.Required("zone_type"): SelectSelector(
            SelectSelectorConfig(options=list(ZONE_TYPE_KC.keys()))
        ),
        vol.Required("valve_entity"): _ENTITY_SWITCH,
        vol.Required("kc", default=0.8): NumberSelector(
            NumberSelectorConfig(min=0.1, max=2.0, step=0.01, mode=NumberSelectorMode.BOX)
        ),
        vol.Required("soil_type"): SelectSelector(
            SelectSelectorConfig(options=list(SOIL_TYPES.keys()))
        ),
        vol.Required("root_depth_dm", default=10): NumberSelector(
            NumberSelectorConfig(min=1, max=30, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required("schwellwert_pct", default=50): NumberSelector(
            NumberSelectorConfig(min=10, max=90, step=5, mode=NumberSelectorMode.BOX)
        ),
        vol.Required("zielwert_pct", default=80): NumberSelector(
            NumberSelectorConfig(min=20, max=100, step=5, mode=NumberSelectorMode.BOX)
        ),
        vol.Required("durchfluss_mm_min", default=0.8): NumberSelector(
            NumberSelectorConfig(min=0.1, max=10.0, step=0.1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required("nfk_start_pct", default=85): NumberSelector(
            NumberSelectorConfig(min=0, max=100, step=5, mode=NumberSelectorMode.BOX)
        ),
    }
)


def _build_entry_data(
    anlage_name: str,
    latitude: float,
    longitude: float,
    elevation: int,
    weather: dict[str, Any],
    hardware: dict[str, Any],
    zones: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "name": anlage_name,
        "latitude": latitude,
        "longitude": longitude,
        "elevation": elevation,
        "temp_entity": weather.get("temp_entity"),
        "humidity_entity": weather.get("humidity_entity"),
        "solar_entity": weather.get("solar_entity"),
        "solar_sensor_type": weather.get("solar_sensor_type", "w_m2"),
        "wind_entity": weather.get("wind_entity"),
        "rain_entity": weather.get("rain_entity"),
        "trafo_entity": hardware.get("trafo_entity"),
        "frost_threshold": hardware["frost_threshold"],
        "zones": zones,
    }


class IrrigationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for smartgardn_et0."""

    VERSION = 1

    def __init__(self) -> None:
        self._anlage_name: str = ""
        self._latitude: float = 0.0
        self._longitude: float = 0.0
        self._elevation: int = 0
        self._weather: dict[str, Any] = {}
        self._hardware: dict[str, Any] = {}
        self._zones: dict[str, dict[str, Any]] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Step 1: Basic installation info."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = str(user_input["name"]).strip()
            location = user_input.get("location", {})
            elevation = int(user_input["elevation"])

            # Parse location (dict with "latitude" and "longitude" keys)
            try:
                latitude = float(location.get("latitude", 0))
                longitude = float(location.get("longitude", 0))
            except (ValueError, TypeError):
                errors["location"] = "invalid_location"

            # Validate latitude range
            if not errors and not -90 <= latitude <= 90:
                errors["latitude"] = "invalid_latitude"

            if not errors:
                # Check for duplicate name across existing entries
                for entry in self._async_current_entries():
                    if entry.data.get("name") == name:
                        errors["base"] = "already_configured"
                        break

            if not errors:
                self._anlage_name = name
                self._latitude = latitude
                self._longitude = longitude
                self._elevation = elevation
                return await self.async_step_weather()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Step 2: Weather sensor entities."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._weather = {
                "temp_entity": user_input.get("temp_entity"),
                "humidity_entity": user_input.get("humidity_entity"),
                "solar_entity": user_input.get("solar_entity"),
                "solar_sensor_type": user_input.get("solar_sensor_type", "w_m2"),
                "wind_entity": user_input.get("wind_entity"),
                "rain_entity": user_input.get("rain_entity"),
            }
            return await self.async_step_hardware()

        return self.async_show_form(
            step_id="weather",
            data_schema=STEP_WEATHER_SCHEMA,
            errors=errors,
        )

    async def async_step_hardware(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Step 3: Hardware configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._hardware = {
                "trafo_entity": user_input.get("trafo_entity"),
                "frost_threshold": float(user_input["frost_threshold"]),
            }
            return await self.async_step_zone()

        return self.async_show_form(
            step_id="hardware",
            data_schema=STEP_HARDWARE_SCHEMA,
            errors=errors,
        )

    async def async_step_zone(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Step 4: Add a zone."""
        errors: dict[str, str] = {}

        if user_input is not None:
            zone_id = str(uuid.uuid4())
            soil_type = str(user_input["soil_type"])
            root_depth_dm = int(user_input["root_depth_dm"])
            nfk_max = SOIL_TYPES[soil_type] * root_depth_dm

            self._zones[zone_id] = {
                "zone_name": str(user_input["zone_name"]),
                "zone_type": str(user_input["zone_type"]),
                "valve_entity": str(user_input["valve_entity"]),
                "kc": float(user_input["kc"]),
                "soil_type": soil_type,
                "root_depth_dm": root_depth_dm,
                "schwellwert_pct": int(user_input["schwellwert_pct"]),
                "zielwert_pct": int(user_input["zielwert_pct"]),
                "durchfluss_mm_min": float(user_input["durchfluss_mm_min"]),
                "nfk_start_pct": int(user_input["nfk_start_pct"]),
                "nfk_max": nfk_max,
            }
            return self.async_show_menu(
                step_id="zone_menu",
                menu_options=["add_zone", "finish"],
            )

        return self.async_show_form(
            step_id="zone",
            data_schema=STEP_ZONE_SCHEMA,
            errors=errors,
        )

    async def async_step_zone_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Route from zone menu to add_zone or finish."""
        # HA's flow engine calls this with {"next_step_id": "add_zone"|"finish"}
        if user_input is not None:
            next_step = user_input.get("next_step_id", "finish")
            if next_step == "add_zone":
                return await self.async_step_add_zone()
            return await self.async_step_finish()
        return self.async_show_menu(
            step_id="zone_menu",
            menu_options=["add_zone", "finish"],
        )

    async def async_step_add_zone(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Show the zone form again for an additional zone."""
        return await self.async_step_zone()

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create the config entry."""
        data = _build_entry_data(
            anlage_name=self._anlage_name,
            latitude=self._latitude,
            longitude=self._longitude,
            elevation=self._elevation,
            weather=self._weather,
            hardware=self._hardware,
            zones=self._zones,
        )
        return self.async_create_entry(title=self._anlage_name, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> IrrigationOptionsFlow:
        """Return the options flow handler."""
        return IrrigationOptionsFlow(config_entry)


class IrrigationOptionsFlow(OptionsFlowWithConfigEntry):
    """Options flow for runtime reconfiguration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Show menu for different option types."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["general", "weather", "forecast"],
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Options for general settings."""
        current = self.config_entry.data

        if user_input is not None:
            updated = dict(current)
            updated["name"] = str(user_input["name"])
            updated["frost_threshold"] = float(user_input["frost_threshold"])
            return self.async_create_entry(title="", data=updated)

        schema = vol.Schema(
            {
                vol.Required("name", default=current.get("name", "")): TextSelector(),
                vol.Required(
                    "frost_threshold", default=current.get("frost_threshold", 4.0)
                ): NumberSelector(
                    NumberSelectorConfig(min=-10, max=15, step=0.5, mode=NumberSelectorMode.BOX)
                ),
            }
        )

        return self.async_show_form(step_id="general", data_schema=schema)

    async def async_step_weather(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Options for weather sensor configuration."""
        current = self.config_entry.data

        if user_input is not None:
            updated = dict(current)
            updated["temp_entity"] = user_input.get("temp_entity")
            updated["humidity_entity"] = user_input.get("humidity_entity")
            updated["solar_entity"] = user_input.get("solar_entity")
            updated["solar_sensor_type"] = user_input.get("solar_sensor_type", "w_m2")
            updated["wind_entity"] = user_input.get("wind_entity")
            updated["rain_entity"] = user_input.get("rain_entity")
            return self.async_create_entry(title="", data=updated)

        schema = vol.Schema(
            {
                vol.Required("temp_entity", default=current.get("temp_entity", "")): _ENTITY_SENSOR,
                vol.Optional("humidity_entity", default=current.get("humidity_entity", "")): _ENTITY_SENSOR,
                vol.Optional("solar_entity", default=current.get("solar_entity", "")): _ENTITY_SENSOR,
                vol.Optional("solar_sensor_type", default=current.get("solar_sensor_type", "w_m2")): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            "w_m2",   # W/m² (Photodiode, Pyranometer)
                            "lux",    # Lux (simple light sensors)
                            "par",    # PAR (photosynthetically active radiation)
                            "none",   # No solar sensor
                        ]
                    )
                ),
                vol.Optional("wind_entity", default=current.get("wind_entity", "")): _ENTITY_SENSOR,
                vol.Optional("rain_entity", default=current.get("rain_entity", "")): _ENTITY_SENSOR,
            }
        )

        return self.async_show_form(step_id="weather", data_schema=schema)

    async def async_step_forecast(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Options for DWD forecast configuration."""
        current = self.config_entry.data

        if user_input is not None:
            updated = dict(current)
            updated["dwd_forecast_enabled"] = user_input.get("dwd_forecast_enabled", False)
            if user_input.get("dwd_lat_override"):
                updated["dwd_lat_override"] = float(user_input["dwd_lat_override"])
            else:
                updated.pop("dwd_lat_override", None)
            if user_input.get("dwd_lon_override"):
                updated["dwd_lon_override"] = float(user_input["dwd_lon_override"])
            else:
                updated.pop("dwd_lon_override", None)
            return self.async_create_entry(title="", data=updated)

        schema = vol.Schema(
            {
                vol.Required(
                    "dwd_forecast_enabled",
                    default=current.get("dwd_forecast_enabled", False),
                ): vol.In([False, True]),
                vol.Optional(
                    "dwd_lat_override", default=current.get("dwd_lat_override", "")
                ): NumberSelector(
                    NumberSelectorConfig(min=-90, max=90, step=0.01, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    "dwd_lon_override", default=current.get("dwd_lon_override", "")
                ): NumberSelector(
                    NumberSelectorConfig(min=-180, max=180, step=0.01, mode=NumberSelectorMode.BOX)
                ),
            }
        )

        return self.async_show_form(step_id="forecast", data_schema=schema)
