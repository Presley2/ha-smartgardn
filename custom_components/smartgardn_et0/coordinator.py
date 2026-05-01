"""DataUpdateCoordinator for smartgardn_et0."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime
from functools import partial

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.recorder import get_instance

from custom_components.smartgardn_et0.const import (
    DOMAIN,
    MODE_FULL,
    MODE_OFF,
    MODE_SEED,
    MODE_SEMI,
    TRAFO_DELAY_S,
    WEEKDAYS,
)
from custom_components.smartgardn_et0.et0_calculator import (
    calc_et0_fao56,
    calc_et0_hargreaves,
    calc_ka,
    convert_solar_to_w_m2,
)
from custom_components.smartgardn_et0.gts_calculator import gts_increment, gts_should_reset
from custom_components.smartgardn_et0.storage import IrrigationStorage, StorageData
from custom_components.smartgardn_et0.water_balance import (
    calc_daily_balance,
    calc_etc,
    needs_watering,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """Represents a single irrigation queue entry with Cycle & Soak tracking."""

    zone_id: str
    dauer_min: float
    cs_remaining: int  # 0 if no C&S active
    cs_pause_min: float
    started_at: datetime | None = None


class IrrigationCoordinator(DataUpdateCoordinator[dict]):  # type: ignore[type-arg]
    """Manages state, scheduling, and sensor polling for smartgardn_et0."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self.storage = IrrigationStorage(hass)
        self._storage_data: StorageData | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._zone_enabled: dict[str, bool] = {}
        self._zone_weekdays: dict[str, dict[str, bool]] = {}
        self._zone_modus: dict[str, str] = {}
        self._zone_numbers: dict[str, dict[str, float]] = {}
        self._zone_times: dict[str, dict[str, dtime]] = {}
        self._dry_run: bool = True
        # Phase 4: Queue and scheduling state
        self.queue: deque[QueueItem] = deque()
        self.running: QueueItem | None = None
        self._frost_active: bool = False
        self._zone_done_unsub: dict[str, Callable[[], None]] = {}

    async def async_setup(self) -> None:
        """Load storage and register scheduled callbacks."""
        self._storage_data = await self.storage.async_load()
        for zone_id, zone_cfg in self.entry.data.get("zones", {}).items():
            self._zone_enabled[zone_id] = True
            self._zone_weekdays[zone_id] = dict.fromkeys(WEEKDAYS, True)
            self._zone_modus[zone_id] = MODE_OFF
            self._zone_numbers[zone_id] = {
                "dauer": 30.0,
                "schwellwert": float(zone_cfg.get("schwellwert_pct", 50)),
                "zielwert": float(zone_cfg.get("zielwert_pct", 80)),
                "manuelle_dauer": 15.0,
                "cs_zyklen": 0.0,
                "cs_pause": 10.0,
                "ansaat_intervall": 60.0,
                "ansaat_dauer": 5.0,
                "ansaat_laufzeit_tage": 14.0,
            }
            self._zone_times[zone_id] = {
                "start": dtime(19, 0),
                "ansaat_von": dtime(6, 0),
                "ansaat_bis": dtime(10, 0),
            }

        # Phase 5.1 + 5.5: Startup recovery — check for zones stuck running
        await self._startup_recovery()

        # Phase 7: Check and create repair issues
        from custom_components.smartgardn_et0.repairs import async_check_and_create_issues
        await async_check_and_create_issues(self.hass, self.entry)

        # Register daily 00:05 calculation
        unsub = async_track_time_change(self.hass, self._daily_calc, hour=0, minute=5)
        self._unsubs.append(unsub)

        # Register failsafe every 5 min
        unsub = async_track_time_interval(
            self.hass, self._failsafe_check, interval=timedelta(minutes=5)
        )
        self._unsubs.append(unsub)

        # Register frost check every 1 min
        unsub = async_track_time_interval(
            self.hass, self._check_frost_and_lock, interval=timedelta(minutes=1)
        )
        self._unsubs.append(unsub)

        # Phase 5.4: Register trafo problem detection every 5 min
        unsub = async_track_time_interval(
            self.hass, self._check_trafo_state, interval=timedelta(minutes=5)
        )
        self._unsubs.append(unsub)

    # ===== Phase 5: Reliability =====

    async def _startup_recovery(self) -> None:
        """Phase 5.1 + 5.5: On startup, check for zones stuck running from power loss."""
        storage = self._storage_data
        if not storage:
            return

        for zone_id, zone_data in storage.get("zones", {}).items():
            running_since_str = zone_data.get("scheduling", {}).get("running_since")
            if not running_since_str:
                continue

            # Zone was running before power loss
            try:
                dt_started = datetime.fromisoformat(running_since_str)
            except (ValueError, TypeError):
                _LOGGER.error(
                    "Invalid running_since timestamp for zone %s: %s", zone_id, running_since_str
                )
                zone_data["scheduling"]["running_since"] = None
                continue

            elapsed_min = (datetime.now(UTC) - dt_started).total_seconds() / 60
            valve_id = self.entry.data.get("zones", {}).get(zone_id, {}).get("valve_entity")
            if not valve_id:
                _LOGGER.warning("No valve entity found for zone %s during recovery", zone_id)
                zone_data["scheduling"]["running_since"] = None
                continue

            valve_state = self.hass.states.get(valve_id)
            dauer_min = zone_data.get("scheduling", {}).get("active_zone_remaining_min", 30.0)

            if valve_state and valve_state.state == "on":
                # Valve is still on
                if elapsed_min >= dauer_min:
                    # Time's up, close it
                    _LOGGER.warning(
                        "Startup recovery: zone %s ran for %.1f min (dauer %.1f min), closing",
                        zone_id, elapsed_min, dauer_min
                    )
                    await self._valve_off_then_trafo_check(valve_id)
                    zone_data["scheduling"]["running_since"] = None
                    await self.storage.async_save_immediate(storage)
                else:
                    # Still running, resume the timer
                    remaining_min = dauer_min - elapsed_min
                    _LOGGER.info(
                        "Startup recovery: zone %s resuming, %.1f min remaining",
                        zone_id, remaining_min
                    )
                    end_dt = datetime.now(UTC) + timedelta(minutes=remaining_min)
                    unsub = async_track_point_in_time(
                        self.hass, partial(self._zone_done_recovery, zone_id), end_dt
                    )
                    self._unsubs.append(unsub)
            else:
                # Valve is already off, clean up storage
                _LOGGER.info("Startup recovery: zone %s valve already off, cleaning up", zone_id)
                zone_data["scheduling"]["running_since"] = None
                await self.storage.async_save_immediate(storage)

    async def _zone_done_recovery(self, zone_id: str) -> None:
        """Called when a recovered zone run finishes."""
        valve_id = self.entry.data.get("zones", {}).get(zone_id, {}).get("valve_entity")
        if valve_id:
            await self._valve_off_then_trafo_check(valve_id)
        if self._storage_data:
            self._storage_data["zones"][zone_id]["scheduling"]["running_since"] = None
            await self.storage.async_save_immediate(self._storage_data)

    async def _get_daily_minmax(
        self, entity_id: str | None, start_time: datetime | None = None
    ) -> tuple[float | None, float | None]:
        """Read min/max values from HA history for a sensor.

        Args:
            entity_id: The sensor entity ID
            start_time: Start of window (default: today 00:00)

        Returns:
            (min_value, max_value) or (None, None) if no data available
        """
        if not entity_id:
            return None, None

        if start_time is None:
            start_time = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            recorder = get_instance(self.hass)
            if not recorder or not recorder.async_block_till_done:
                _LOGGER.warning("Recorder not available for %s", entity_id)
                return None, None

            # Query HA history for sensor state changes in the window
            history = await recorder.async_add_executor_job(
                lambda: recorder.history.get_significant_states(
                    self.hass,
                    start_time,
                    entity_ids=[entity_id],
                    significant_changes_only=False,
                )
            )

            if not history or entity_id not in history:
                _LOGGER.debug("No history data for %s", entity_id)
                return None, None

            states = history[entity_id]
            values = []
            for state_obj in states:
                try:
                    val = float(state_obj.state)
                    if val is not None:
                        values.append(val)
                except (ValueError, TypeError):
                    pass

            if not values:
                _LOGGER.debug("No numeric values in history for %s", entity_id)
                return None, None

            return min(values), max(values)

        except Exception as err:
            _LOGGER.error("Error reading history for %s: %s", entity_id, err)
            return None, None

    async def _compute_et0_with_fallback(self) -> tuple[float, str, bool]:
        """Phase 5.3: Compute ET0 with fallback chain.

        Returns (et0, method_used, fallback_active).
        """
        today = date.today()

        # If new single temp_entity is configured, get min/max from history
        temp_entity = self.entry.data.get("temp_entity")
        if temp_entity:
            t_min, t_max = await self._get_daily_minmax(temp_entity)
        else:
            # Fallback to old min/max entities for backwards compatibility
            t_min = self._read_sensor(self.entry.data.get("temp_min_entity"))
            t_max = self._read_sensor(self.entry.data.get("temp_max_entity"))

        if not t_min or not t_max:
            _LOGGER.error("No temperature data, using last known or 0")
            storage = self._storage_data
            last_et0 = storage["globals"].get("et0_last_known", 0.0) if storage else 0.0
            return last_et0, "last_known", True

        et_method = self.entry.data.get("et_methode", "fao56")

        # Try primary method (FAO56)
        if et_method == "fao56":
            # Similarly, get humidity min/max from history if single entity is configured
            humidity_entity = self.entry.data.get("humidity_entity")
            if humidity_entity:
                rh_min, rh_max = await self._get_daily_minmax(humidity_entity)
            else:
                rh_min = self._read_sensor(self.entry.data.get("humidity_min_entity"))
                rh_max = self._read_sensor(self.entry.data.get("humidity_max_entity"))

            # Read solar and convert based on sensor type
            solar_raw = self._read_sensor(self.entry.data.get("solar_entity"))
            solar_sensor_type = self.entry.data.get("solar_sensor_type", "w_m2")
            solar = convert_solar_to_w_m2(solar_raw, solar_sensor_type) if solar_raw else None

            wind = self._read_sensor(self.entry.data.get("wind_entity"))

            if all(x is not None for x in [rh_min, rh_max, solar, wind]):
                et0 = calc_et0_fao56(
                    t_min, t_max, rh_min, rh_max, solar, wind,
                    self.entry.data["latitude"], self.entry.data["elevation"],
                    today.timetuple().tm_yday
                )
                if self._storage_data:
                    self._storage_data["globals"]["et0_last_known"] = et0
                return et0, "fao56", False

            # Fallback to Hargreaves
            _LOGGER.warning("PM inputs missing, falling back to Hargreaves")
            et0 = calc_et0_hargreaves(
                t_min, t_max, self.entry.data["latitude"], today.timetuple().tm_yday
            )
            if self._storage_data:
                self._storage_data["globals"]["et0_last_known"] = et0
            return et0, "hargreaves", True

        # If primary method is already Hargreaves or other
        if (et_method == "hargreaves" or et_method == "haude") and t_min and t_max:
            et0 = calc_et0_hargreaves(
                t_min, t_max, self.entry.data["latitude"], today.timetuple().tm_yday
            )
            if self._storage_data:
                self._storage_data["globals"]["et0_last_known"] = et0
            return et0, "hargreaves", False

        # Fallback to last known
        storage = self._storage_data
        last_et0 = storage["globals"].get("et0_last_known", 0.0) if storage else 0.0
        return last_et0, "last_known", True

    async def _check_trafo_state(self) -> None:
        """Phase 5.4: Every 5 min, check if trafo is unavailable and create repair if stuck."""
        from homeassistant.helpers import issue_registry as ir

        trafo_id = self.entry.data.get("trafo_entity")
        if not trafo_id:
            return

        trafo_state = self.hass.states.get(trafo_id)

        if trafo_state is None or trafo_state.state == "unavailable":
            if not hasattr(self, "_trafo_unavailable_since"):
                self._trafo_unavailable_since = datetime.now(UTC)
                _LOGGER.warning("Trafo became unavailable: %s", trafo_id)
            elif (datetime.now(UTC) - self._trafo_unavailable_since).total_seconds() > 300:
                # Unavailable for >5 min, create repair issue
                issue_id = f"trafo_unavailable_{trafo_id.replace('.', '_')}"
                try:
                    ir.async_create_issue(
                        self.hass, DOMAIN, issue_id,
                        is_fixable=True, severity=ir.IssueSeverity.WARNING,
                        translation_key="trafo_unavailable",
                        translation_placeholders={"entity": trafo_id},
                    )
                    _LOGGER.error("Trafo unavailable for >5 min, created repair issue %s", issue_id)
                except Exception as err:
                    _LOGGER.error("Failed to create repair issue: %s", err)
        else:
            if hasattr(self, "_trafo_unavailable_since"):
                delattr(self, "_trafo_unavailable_since")
                self.hass.bus.async_fire("smartgardn_et0_trafo_recovered")

    async def _catch_up_missed_days(self) -> None:
        """Phase 5.2: If last calc was >1 day ago, reconstruct weather from Recorder (placeholder).

        Full implementation with Recorder history reading is deferred to Phase 10.
        """
        storage = self._storage_data
        if not storage:
            return

        last_calc_str = storage["globals"].get("letzte_et0_berechnung")
        if not last_calc_str:
            return

        try:
            last_calc_dt = datetime.fromisoformat(last_calc_str)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid letzte_et0_berechnung timestamp: %s", last_calc_str)
            return

        missed_days = (datetime.now(UTC) - last_calc_dt).days

        if missed_days < 2:
            return

        _LOGGER.info(
            "Catch-up: missed %d days since last calc, full Recorder reconstruction "
            "deferred to Phase 10",
            missed_days,
        )
        # Placeholder: no action for now

    async def async_shutdown(self) -> None:
        """Cancel all tracked listeners/timers."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for unsub in self._zone_done_unsub.values():
            unsub()
        self._zone_done_unsub.clear()

    async def _async_update_data(self) -> dict:  # type: ignore[override]
        """Poll current state from HA sensors and compute derived values."""
        data = self.entry.data
        trafo_state = self.hass.states.get(data.get("trafo_entity", ""))
        frost_threshold = data.get("frost_threshold", 4.0)

        # Check frost using current temp_entity or fallback to temp_min_entity
        temp_entity = data.get("temp_entity") or data.get("temp_min_entity")
        temp_state = self.hass.states.get(temp_entity or "")
        frost_active = False
        if temp_state and temp_state.state not in ("unknown", "unavailable"):
            with contextlib.suppress(ValueError):
                frost_active = float(temp_state.state) < frost_threshold

        return {
            "frost_active": frost_active,
            "trafo_state": trafo_state.state if trafo_state else "unavailable",
            "storage": self._storage_data,
        }

    # ===== Phase 4: Trafo sequencing =====

    async def _trafo_on_then_valve(self, valve_entity_id: str) -> None:
        """Turn on trafo, wait TRAFO_DELAY_S, turn on valve."""
        await self._switch_service("turn_on", self.entry.data["trafo_entity"])
        await asyncio.sleep(TRAFO_DELAY_S)
        await self._switch_service("turn_on", valve_entity_id)

    async def _valve_off_then_trafo_check(self, valve_entity_id: str) -> None:
        """Turn off valve, wait TRAFO_DELAY_S, turn off trafo if all valves are off."""
        await self._switch_service("turn_off", valve_entity_id)
        await asyncio.sleep(TRAFO_DELAY_S)
        # Check all zone valves — if all off, turn off trafo
        all_off = all(
            (state := self.hass.states.get(self.entry.data["zones"][zid].get("valve_entity")))
            and state.state == "off"
            for zid in self.entry.data.get("zones", {})
        )
        if all_off:
            await self._switch_service("turn_off", self.entry.data["trafo_entity"])

    async def _switch_service(self, service: str, entity_id: str) -> None:
        """Call turn_on or turn_off service for a switch entity."""
        await self.hass.services.async_call("homeassistant", service, {"entity_id": entity_id})

    # ===== Phase 4: Queue management =====

    async def async_enqueue_start(
        self, zone_id: str, dauer_min: float, cs_cycles: int = 0, cs_pause_min: float = 10.0
    ) -> None:
        """Enqueue a zone start. If queue empty, run immediately."""
        item = QueueItem(zone_id, dauer_min, cs_cycles, cs_pause_min)
        self.queue.append(item)
        if not self.running:
            await self._run_next_in_queue()

    async def _run_next_in_queue(self) -> None:
        """Pop next item from queue and start it."""
        if not self.queue:
            self.running = None
            return
        self.running = self.queue.popleft()
        valve_id = self.entry.data["zones"][self.running.zone_id]["valve_entity"]
        await self._trafo_on_then_valve(valve_id)
        self.running.started_at = datetime.now(UTC)
        duration_s = self.running.dauer_min * 60

        # Schedule end callback using async_track_point_in_time
        end_dt = datetime.now(UTC) + timedelta(seconds=duration_s)
        unsub = async_track_point_in_time(self.hass, partial(self._zone_done), end_dt)
        zone_id = self.running.zone_id
        if zone_id in self._zone_done_unsub:
            self._zone_done_unsub[zone_id]()
        self._zone_done_unsub[zone_id] = unsub

    async def _zone_done(self) -> None:
        """Called when a zone run finishes."""
        if not self.running:
            return
        zone_id = self.running.zone_id
        valve_id = self.entry.data["zones"][zone_id]["valve_entity"]
        await self._valve_off_then_trafo_check(valve_id)

        # Handle Cycle & Soak: if cs_remaining > 0, requeue same zone with pause
        if self.running.cs_remaining > 0:
            self.running.cs_remaining -= 1
            await asyncio.sleep(self.running.cs_pause_min * 60)
            await self.async_enqueue_start(
                zone_id, self.running.dauer_min, self.running.cs_remaining, self.running.cs_pause_min
            )
        else:
            # Fire zone_finished event
            self.hass.bus.async_fire("smartgardn_et0_zone_finished", {"zone_id": zone_id})
            # Clean up unsub
            if zone_id in self._zone_done_unsub:
                del self._zone_done_unsub[zone_id]
            # Move to next in queue
            await self._run_next_in_queue()

    async def _failsafe_check(self) -> None:
        """Every 5 min: if trafo is on but all valves are off, turn off trafo."""
        trafo_state = self.hass.states.get(self.entry.data["trafo_entity"])
        if trafo_state and trafo_state.state == "on":
            all_off = all(
                (state := self.hass.states.get(self.entry.data["zones"][zid].get("valve_entity")))
                and state.state == "off"
                for zid in self.entry.data.get("zones", {})
            )
            if all_off:
                _LOGGER.warning("Failsafe: trafo on but all valves off, turning off trafo")
                await self._switch_service("turn_off", self.entry.data["trafo_entity"])

    # ===== Phase 4: Daily calculation (00:05) =====

    async def _daily_calc(self) -> None:
        """Run at 00:05 daily: compute ET0, ETc, NFK, GTS, schedule next runs."""
        today = date.today()
        data = self.entry.data
        storage = self._storage_data

        if not storage:
            _LOGGER.error("Storage not loaded, skipping daily calc")
            return

        # Phase 5.2: Catch-up on missed days
        await self._catch_up_missed_days()

        # Step 1: Read weather sensors and rain
        rain = self._read_sensor(data.get("rain_entity"))

        # Phase 5.3: Compute ET0 with fallback chain
        et0, et_method, et_fallback_active = await self._compute_et0_with_fallback()

        # Compute Ka (temperature correction factor)
        # Get t_max from new single temp_entity or fallback to old temp_max_entity
        temp_entity = data.get("temp_entity")
        if temp_entity:
            _, t_max = await self._get_daily_minmax(temp_entity)
        else:
            t_max = self._read_sensor(data.get("temp_max_entity"))
        ka = calc_ka(t_max if t_max else 20.0)

        # Step 2: For each zone, compute ETc and NFK balance
        for zone_id, zone_cfg in data.get("zones", {}).items():
            zone_storage = storage["zones"].get(zone_id)
            if not zone_storage:
                continue

            kc = zone_cfg.get("kc", 0.8)
            etc = calc_etc(et0, kc, ka)
            beregnung_today = 0.0  # Simplified: no irrigation computation yet

            nfk_anfang = zone_storage["nfk_aktuell"]
            nfk_max = zone_cfg.get("nfk_max", 150)

            balance = calc_daily_balance(
                today,
                nfk_anfang,
                etc,
                rain if rain else 0.0,
                beregnung_today,
                nfk_max,
            )

            zone_storage["nfk_aktuell"] = balance.nfk_ende
            zone_storage["letzte_berechnung"] = str(today)
            zone_storage["verlauf"].append(
                {
                    "datum": str(today),
                    "nfk_ende": balance.nfk_ende,
                    "etc": etc,
                    "regen": rain if rain else 0.0,
                    "beregnung": beregnung_today,
                }
            )

        # Step 3: Compute GTS with average daily temperature
        globals_data = storage["globals"]
        if gts_should_reset(today, None):
            globals_data["gts"] = 0.0
            globals_data["gts_jahr"] = today.year

        # Get t_min and t_max from history to compute average temperature
        temp_entity = data.get("temp_entity")
        if temp_entity:
            t_min, t_max = await self._get_daily_minmax(temp_entity)
        else:
            t_min = self._read_sensor(data.get("temp_min_entity"))
            t_max = self._read_sensor(data.get("temp_max_entity"))

        # Calculate average temperature for GTS
        if t_min is not None and t_max is not None:
            t_mittel = (t_min + t_max) / 2.0
        else:
            t_mittel = t_max if t_max else 0.0  # Fallback to t_max if t_min unavailable

        gts_inc = gts_increment(t_mittel, today.month)
        globals_data["gts"] += gts_inc
        globals_data["letzte_et0_berechnung"] = datetime.now(UTC).isoformat()

        # Step 4-5: For each zone, compute next_start_dt and schedule async_track_point_in_time
        for zone_id, zone_cfg in data.get("zones", {}).items():
            zone_storage = storage["zones"].get(zone_id)
            if not zone_storage:
                continue

            mode = self._zone_modus.get(zone_id, MODE_OFF)

            if mode == MODE_SEMI:
                next_dt = self._compute_next_start_semi(zone_id, zone_cfg, zone_storage)
            elif mode == MODE_FULL:
                next_dt = self._compute_next_start_voll(zone_id, zone_cfg, zone_storage)
            elif mode == MODE_SEED:
                next_dt = self._compute_next_start_ansaat(zone_id, zone_cfg, zone_storage)
            else:
                next_dt = None

            if next_dt:
                zone_storage["scheduling"]["next_start_dt"] = next_dt.isoformat()
                unsub = async_track_point_in_time(
                    self.hass, partial(self._trigger_zone_start, zone_id), next_dt
                )
                self._unsubs.append(unsub)
            else:
                zone_storage["scheduling"]["next_start_dt"] = None

        # Step 6: Persist storage and fire event
        await self.storage.async_save_immediate(storage)

        # Update coordinator data with fallback status
        if self.data is None:
            self.data = {}
        self.data["et_fallback_active"] = et_fallback_active

        self.hass.bus.async_fire(
            "smartgardn_et0_calc_done", {"timestamp": datetime.now(UTC).isoformat()}
        )
        if et_fallback_active:
            self.hass.bus.async_fire(
                "smartgardn_et0_fallback_active", {"method": et_method}
            )

    def _read_sensor(self, entity_id: str | None) -> float | None:
        """Read a sensor value, return None if unavailable or not a number."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if not state or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    async def _trigger_zone_start(self, zone_id: str) -> None:
        """Called when a scheduled start time is reached."""
        zone_cfg = self.entry.data["zones"].get(zone_id)
        if not zone_cfg:
            return
        dauer = self._zone_numbers[zone_id]["dauer"]
        cs_zyklen = int(self._zone_numbers[zone_id]["cs_zyklen"])
        cs_pause = self._zone_numbers[zone_id]["cs_pause"]
        await self.async_enqueue_start(zone_id, dauer, cs_zyklen, cs_pause)

    def _compute_next_start_semi(
        self, zone_id: str, zone_cfg: dict, zone_storage: dict
    ) -> datetime | None:
        """Compute next start for Semi-Automatik mode."""
        # Find next enabled weekday starting from tomorrow
        weekdays_enabled = self._zone_weekdays.get(
            zone_id, dict.fromkeys(WEEKDAYS, True)
        )
        start_time = self._zone_times.get(zone_id, {}).get("start", dtime(19, 0))

        today = date.today()
        weekday_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        for i in range(1, 8):
            check_date = today + timedelta(days=i)
            weekday_name = weekday_names[check_date.weekday()]
            if weekdays_enabled.get(weekday_name, True):
                return datetime.combine(check_date, start_time, tzinfo=UTC)
        return None

    def _compute_next_start_voll(
        self, zone_id: str, zone_cfg: dict, zone_storage: dict
    ) -> datetime | None:
        """Compute next start for Voll-Automatik mode."""
        nfk_aktuell = zone_storage["nfk_aktuell"]
        nfk_max = zone_cfg.get("nfk_max", 150)
        schwellwert_pct = self._zone_numbers[zone_id].get(
            "schwellwert", zone_cfg.get("schwellwert_pct", 50)
        )

        if needs_watering(nfk_aktuell, nfk_max, schwellwert_pct):
            # Start immediately
            return datetime.now(UTC) + timedelta(minutes=1)
        return None

    def _compute_next_start_ansaat(
        self, zone_id: str, zone_cfg: dict, zone_storage: dict
    ) -> datetime | None:
        """Compute next start for Ansaat (seed watering) mode."""
        ansaat_von = self._zone_times.get(zone_id, {}).get("ansaat_von", dtime(6, 0))
        ansaat_bis = self._zone_times.get(zone_id, {}).get("ansaat_bis", dtime(10, 0))

        now = datetime.now(UTC)
        today_von = datetime.combine(now.date(), ansaat_von, tzinfo=UTC)
        today_bis = datetime.combine(now.date(), ansaat_bis, tzinfo=UTC)

        if today_von <= now < today_bis:
            return now + timedelta(
                minutes=self._zone_numbers[zone_id].get("ansaat_intervall", 60)
            )
        elif now < today_von:
            return today_von
        else:
            return datetime.combine(
                now.date() + timedelta(days=1), ansaat_von, tzinfo=UTC
            )

    # ===== Phase 4: Frost lock =====

    async def _check_frost_and_lock(self) -> None:
        """Check if frost is active; if so, stop running zone and block new starts."""
        frost_threshold = self.entry.data.get("frost_threshold", 4.0)
        t_min_state = self.hass.states.get(self.entry.data.get("temp_min_entity"))

        frost_active = False
        if t_min_state and t_min_state.state not in ("unknown", "unavailable"):
            with contextlib.suppress(ValueError):
                frost_active = float(t_min_state.state) < frost_threshold

        if frost_active and not self._frost_active:
            _LOGGER.warning("Frost lock activated: stopping all irrigation")
            self._frost_active = True
            # Stop running zone if any
            if self.running:
                valve_id = self.entry.data["zones"][self.running.zone_id]["valve_entity"]
                await self._valve_off_then_trafo_check(valve_id)
                self.running = None
            # Clear queue
            self.queue.clear()
            self.hass.bus.async_fire("smartgardn_et0_frost_lock")
        elif not frost_active and self._frost_active:
            _LOGGER.info("Frost lock released")
            self._frost_active = False
            self.hass.bus.async_fire("smartgardn_et0_frost_release")

    # ===== Phase 6: Services & Events =====

    async def async_start_zone(self, zone_entity_id: str, dauer_min: float) -> None:
        """Service handler: start a zone manually.

        Args:
            zone_entity_id: Entity ID of the select.{zone}_modus entity
            dauer_min: Duration in minutes
        """
        zone_id = self._extract_zone_id_from_entity(zone_entity_id)
        if not zone_id:
            _LOGGER.error("Could not extract zone_id from entity %s", zone_entity_id)
            return

        zone_cfg = self.entry.data.get("zones", {}).get(zone_id)
        if not zone_cfg:
            _LOGGER.error("Zone %s not configured", zone_id)
            return

        # Check frost lock
        if self._frost_active:
            _LOGGER.warning("Cannot start zone: frost lock is active")
            return

        # Enqueue the start
        cs_zyklen = int(self._zone_numbers[zone_id].get("cs_zyklen", 0))
        cs_pause = self._zone_numbers[zone_id].get("cs_pause", 10.0)
        await self.async_enqueue_start(zone_id, dauer_min, cs_zyklen, cs_pause)
        _LOGGER.info("Started zone %s for %.1f minutes", zone_id, dauer_min)
        self.hass.bus.async_fire(
            "smartgardn_et0_zone_started", {"zone_id": zone_id, "duration_min": dauer_min}
        )

    async def async_stop_zone(self, zone_entity_id: str) -> None:
        """Service handler: stop a specific zone.

        Args:
            zone_entity_id: Entity ID of the select.{zone}_modus entity
        """
        zone_id = self._extract_zone_id_from_entity(zone_entity_id)
        if not zone_id:
            _LOGGER.error("Could not extract zone_id from entity %s", zone_entity_id)
            return

        # If this zone is currently running, stop it
        if self.running and self.running.zone_id == zone_id:
            zone_cfg = self.entry.data.get("zones", {}).get(zone_id)
            if zone_cfg:
                valve_id = zone_cfg["valve_entity"]
                await self._valve_off_then_trafo_check(valve_id)
            self.running = None
            _LOGGER.info("Stopped zone %s", zone_id)
            self.hass.bus.async_fire(
                "smartgardn_et0_zone_finished", {"zone_id": zone_id}
            )

        # Also remove from queue if present
        self.queue = deque(q for q in self.queue if q.zone_id != zone_id)

    async def async_stop_all(self) -> None:
        """Service handler: stop all zones immediately."""
        # Stop running zone
        if self.running:
            zone_cfg = self.entry.data.get("zones", {}).get(self.running.zone_id)
            if zone_cfg:
                valve_id = zone_cfg["valve_entity"]
                await self._valve_off_then_trafo_check(valve_id)
            self.running = None

        # Clear queue
        self.queue.clear()
        _LOGGER.info("Stopped all zones")
        self.hass.bus.async_fire("smartgardn_et0_stop_all")

    def _extract_zone_id_from_entity(self, entity_id: str) -> str | None:
        """Extract zone_id from select.{entry_id}_{zone_id}_modus entity ID.

        Args:
            entity_id: The entity ID to parse

        Returns:
            The zone_id if successful, None otherwise
        """
        if not entity_id.startswith("select."):
            return None

        # Format: select.{entry_id}_{zone_id}_modus
        try:
            # Remove 'select.' prefix
            base = entity_id[len("select."):]
            # Split off '_modus' suffix
            if not base.endswith("_modus"):
                return None
            base = base[:-len("_modus")]

            # Reverse-engineer: base = {entry_id}_{zone_id}
            entry_id = self.entry.entry_id
            if base.startswith(entry_id + "_"):
                zone_id = base[len(entry_id) + 1:]
                return zone_id if zone_id else None

            return None
        except (AttributeError, IndexError):
            return None

    async def start_zone_manual(self, zone_id: str, dauer_min: float) -> None:
        """Manually start a zone. Full implementation in Phase 4."""
        _LOGGER.info("Manual start zone %s for %.1f min", zone_id, dauer_min)
