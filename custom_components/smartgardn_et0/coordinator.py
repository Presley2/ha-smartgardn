"""DataUpdateCoordinator for smartgardn_et0."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import deque
from collections.abc import Callable
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
from custom_components.smartgardn_et0.weather.forecast import fetch_dwd_forecast
from custom_components.smartgardn_et0.weather.sensors import get_daily_minmax, read_sensor
from custom_components.smartgardn_et0.irrigation.et0 import compute_et0_with_fallback
from custom_components.smartgardn_et0.utils.scheduling import (
    compute_next_start_ansaat,
    compute_next_start_semi,
    compute_next_start_voll,
)
from custom_components.smartgardn_et0.utils.queue import QueueItem

_LOGGER = logging.getLogger(__name__)


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

    def _ensure_storage_schema(self) -> None:
        """Ensure storage has expected globals and one initialized record per configured zone."""
        if self._storage_data is None:
            return

        globals_data = self._storage_data.setdefault("globals", {})
        globals_data.setdefault("gts", 0.0)
        globals_data.setdefault("gts_jahr", 0)
        globals_data.setdefault("et_methode", "fao56")
        globals_data.setdefault("letzte_et0_berechnung", None)
        globals_data.setdefault("et0_last_known", 0.0)

        zones_storage = self._storage_data.setdefault("zones", {})
        for zone_id, zone_cfg in self.entry.data.get("zones", {}).items():
            nfk_max = float(zone_cfg.get("nfk_max", 150))
            nfk_start_pct = float(zone_cfg.get("nfk_start_pct", 85))
            nfk_start = max(0.0, min(nfk_max, nfk_max * nfk_start_pct / 100.0))

            zone_storage = zones_storage.setdefault(
                zone_id,
                {
                    "name": zone_cfg.get("zone_name", zone_id),
                    "nfk_aktuell": nfk_start,
                    "letzte_berechnung": None,
                    "ansaat_start_datum": None,
                    "verlauf": [],
                    "scheduling": {},
                },
            )
            scheduling = zone_storage.setdefault("scheduling", {})
            scheduling.setdefault("next_start_dt", None)
            scheduling.setdefault("next_ansaat_tick", None)
            scheduling.setdefault("running_since", None)
            scheduling.setdefault("active_zone_remaining_min", 0.0)
            scheduling.setdefault("queue", [])

    async def async_setup(self) -> None:
        """Load storage and register scheduled callbacks."""
        self._storage_data = await self.storage.async_load()
        self._ensure_storage_schema()
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
        if self._storage_data:
            await self.storage.async_save_immediate(self._storage_data)

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
            zone_data = self._storage_data.get("zones", {}).get(zone_id)
            if zone_data:
                zone_data["scheduling"]["running_since"] = None
                await self.storage.async_save_immediate(self._storage_data)

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

        # Prepare zone history data for cards (last 30 days per zone)
        zone_verlauf = {}
        if self._storage_data:
            for zone_id, zone_data in self._storage_data.get("zones", {}).items():
                verlauf = zone_data.get("verlauf", [])
                zone_verlauf[zone_id] = verlauf[-30:]

        return {
            "frost_active": frost_active,
            "trafo_state": trafo_state.state if trafo_state else "unavailable",
            "storage": self._storage_data,
            "zone_verlauf": zone_verlauf,
        }

    # ===== Phase 4: Trafo sequencing =====

    async def _trafo_on_then_valve(self, valve_entity_id: str) -> None:
        """Turn on trafo (if configured), wait TRAFO_DELAY_S, turn on valve."""
        if self._dry_run:
            _LOGGER.info("Dry-run active: skip turn_on for %s", valve_entity_id)
            return
        trafo_entity = self.entry.data.get("trafo_entity")
        if trafo_entity:
            await self._switch_service("turn_on", trafo_entity)
            await asyncio.sleep(TRAFO_DELAY_S)
        await self._switch_service("turn_on", valve_entity_id)

    async def _valve_off_then_trafo_check(self, valve_entity_id: str) -> None:
        """Turn off valve, wait TRAFO_DELAY_S, turn off trafo if all valves are off."""
        if self._dry_run:
            _LOGGER.info("Dry-run active: skip turn_off for %s", valve_entity_id)
            return
        await self._switch_service("turn_off", valve_entity_id)
        trafo_entity = self.entry.data.get("trafo_entity")
        if trafo_entity:
            await asyncio.sleep(TRAFO_DELAY_S)
            # Check all zone valves — if all off, turn off trafo
            all_off = all(
                (state := self.hass.states.get(self.entry.data["zones"][zid].get("valve_entity")))
                and state.state == "off"
                for zid in self.entry.data.get("zones", {})
            )
            if all_off:
                await self._switch_service("turn_off", trafo_entity)

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
        self._ensure_storage_schema()
        if not self.queue:
            self.running = None
            return
        self.running = self.queue.popleft()

        # Validate zone still exists in config
        zone_cfg = self.entry.data.get("zones", {}).get(self.running.zone_id)
        if not zone_cfg:
            _LOGGER.error("Zone %s not found in config during queue run", self.running.zone_id)
            self.running = None
            await self._run_next_in_queue()
            return

        valve_id = zone_cfg.get("valve_entity")
        if not valve_id:
            _LOGGER.error("No valve entity for zone %s", self.running.zone_id)
            self.running = None
            await self._run_next_in_queue()
            return

        await self._trafo_on_then_valve(valve_id)
        self.running.started_at = datetime.now(UTC)
        duration_s = self.running.dauer_min * 60
        if self._storage_data:
            zone_storage = self._storage_data["zones"].get(self.running.zone_id)
            if zone_storage:
                zone_storage["scheduling"]["running_since"] = self.running.started_at.isoformat()
                zone_storage["scheduling"]["active_zone_remaining_min"] = self.running.dauer_min
                await self.storage.async_save_immediate(self._storage_data)

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

        # Validate zone still exists in config
        zone_cfg = self.entry.data.get("zones", {}).get(zone_id)
        if not zone_cfg:
            _LOGGER.error("Zone %s not found in config during completion", zone_id)
            self.running = None
            await self._run_next_in_queue()
            return

        valve_id = zone_cfg.get("valve_entity")
        if not valve_id:
            _LOGGER.error("No valve entity for zone %s", zone_id)
            self.running = None
            await self._run_next_in_queue()
            return

        await self._valve_off_then_trafo_check(valve_id)
        if self._storage_data:
            zone_storage = self._storage_data["zones"].get(zone_id)
            if zone_storage:
                zone_storage["scheduling"]["running_since"] = None
                zone_storage["scheduling"]["active_zone_remaining_min"] = 0.0
                await self.storage.async_save_immediate(self._storage_data)

        # Handle Cycle & Soak: if cs_remaining > 0, schedule resume using event scheduler
        if self.running.cs_remaining > 0:
            self.running.cs_remaining -= 1
            pause_end = datetime.now(UTC) + timedelta(minutes=self.running.cs_pause_min)
            unsub = async_track_point_in_time(
                self.hass,
                partial(self._zone_cs_pause_done, zone_id, self.running.dauer_min, self.running.cs_remaining, self.running.cs_pause_min),
                pause_end
            )
            self._unsubs.append(unsub)
        else:
            # Fire zone_finished event
            self.hass.bus.async_fire("smartgardn_et0_zone_finished", {"zone_id": zone_id})
            # Clean up unsub
            if zone_id in self._zone_done_unsub:
                del self._zone_done_unsub[zone_id]
            # Move to next in queue
            await self._run_next_in_queue()

    async def _zone_cs_pause_done(
        self, zone_id: str, dauer_min: float, cs_remaining: int, cs_pause_min: float
    ) -> None:
        """Called when Cycle & Soak pause ends, resume the same zone."""
        zone_cfg = self.entry.data.get("zones", {}).get(zone_id)
        if not zone_cfg:
            _LOGGER.error("Zone %s not found after C&S pause", zone_id)
            await self._run_next_in_queue()
            return
        await self.async_enqueue_start(zone_id, dauer_min, cs_remaining, cs_pause_min)

    async def _failsafe_check(self) -> None:
        """Every 5 min: if trafo is on but all valves are off, turn off trafo."""
        trafo_entity = self.entry.data.get("trafo_entity")
        if not trafo_entity:
            return
        trafo_state = self.hass.states.get(trafo_entity)
        if trafo_state and trafo_state.state == "on":
            all_off = all(
                (state := self.hass.states.get(self.entry.data["zones"][zid].get("valve_entity")))
                and state.state == "off"
                for zid in self.entry.data.get("zones", {})
            )
            if all_off:
                _LOGGER.warning("Failsafe: trafo on but all valves off, turning off trafo")
                await self._switch_service("turn_off", trafo_entity)

    # ===== Phase 4: Daily calculation (00:05) =====

    async def _daily_calc(self) -> None:
        """Run at 00:05 daily: compute ET0, ETc, NFK, GTS, schedule next runs."""
        today = date.today()
        data = self.entry.data
        storage = self._storage_data

        if not storage:
            _LOGGER.error("Storage not loaded, skipping daily calc")
            return
        self._ensure_storage_schema()

        # Phase 5.2: Catch-up on missed days
        await self._catch_up_missed_days()

        # Step 1: Read weather sensors and rain
        rain = read_sensor(self.hass, data.get("rain_entity"))

        # Phase 5.3: Compute ET0 with fallback chain
        et0, et_method, et_fallback_active = await compute_et0_with_fallback(
            self.hass, self.entry, self._storage_data
        )

        # Compute Ka (temperature correction factor)
        # Get t_max from new single temp_entity or fallback to old temp_max_entity
        temp_entity = data.get("temp_entity")
        if temp_entity:
            _, t_max = await get_daily_minmax(self.hass, temp_entity)
        else:
            t_max = read_sensor(self.hass, data.get("temp_max_entity"))
        ka = calc_ka(t_max if t_max else 20.0)

        # Step 2: For each zone, compute ETc and NFK balance (LAWN only, not DRIP)
        for zone_id, zone_cfg in data.get("zones", {}).items():
            zone_storage = storage["zones"].get(zone_id)
            if not zone_storage:
                continue

            zone_type = zone_cfg.get("zone_type", "lawn")

            # DRIP zones: no ET0/NFK calculation, time-controlled only
            if zone_type == "drip":
                zone_storage["letzte_berechnung"] = str(today)
                continue

            # LAWN zones: compute ETc and NFK water balance
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
            t_min, t_max = await get_daily_minmax(self.hass, temp_entity)
        else:
            t_min = read_sensor(self.hass, data.get("temp_min_entity"))
            t_max = read_sensor(self.hass, data.get("temp_max_entity"))

        # Calculate average temperature for GTS
        if t_min is not None and t_max is not None:
            t_mittel = (t_min + t_max) / 2.0
        else:
            t_mittel = t_max if t_max else 0.0  # Fallback to t_max if t_min unavailable

        gts_inc = gts_increment(t_mittel, today.month)
        globals_data["gts"] += gts_inc
        globals_data["letzte_et0_berechnung"] = datetime.now(UTC).isoformat()

        forecast = await fetch_dwd_forecast(
            self.hass,
            self.entry.data.get("dwd_lat_override") or self.entry.data["latitude"],
            self.entry.data.get("dwd_lon_override") or self.entry.data["longitude"],
            self.entry.data.get("elevation", 0),
        )
        if self.data is None:
            self.data = {}
        self.data["dwd_forecast"] = forecast

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
        self.data["et_fallback_active"] = et_fallback_active

        self.hass.bus.async_fire(
            "smartgardn_et0_calc_done", {"timestamp": datetime.now(UTC).isoformat()}
        )
        if et_fallback_active:
            self.hass.bus.async_fire(
                "smartgardn_et0_fallback_active", {"method": et_method}
            )


    async def _trigger_zone_start(self, zone_id: str) -> None:
        """Called when a scheduled start time is reached."""
        zone_cfg = self.entry.data["zones"].get(zone_id)
        if not zone_cfg:
            return
        dauer = self._zone_numbers[zone_id]["dauer"]
        cs_zyklen = int(self._zone_numbers[zone_id]["cs_zyklen"])
        cs_pause = self._zone_numbers[zone_id]["cs_pause"]
        await self.async_enqueue_start(zone_id, dauer, cs_zyklen, cs_pause)

    def _should_skip_for_rain(self, target_date_offset: int) -> bool:
        """True if rain forecast for target day exceeds threshold.

        Args:
            target_date_offset: 1=tomorrow, 2=day-after-tomorrow
        """
        if not self.entry.data.get("dwd_forecast_enabled"):
            return False
        forecast = (self.data or {}).get("dwd_forecast", [])
        threshold = self.entry.data.get("regen_skip_threshold_mm", 10.0)
        idx = target_date_offset - 1
        if idx < len(forecast):
            return forecast[idx].precip_sum >= threshold
        return False

    def _compute_next_start_semi(
        self, zone_id: str, zone_cfg: dict, zone_storage: dict
    ) -> datetime | None:
        """Compute next start for Semi-Automatik mode."""
        weekdays_enabled = self._zone_weekdays.get(
            zone_id, dict.fromkeys(WEEKDAYS, True)
        )
        start_time = self._zone_times.get(zone_id, {}).get("start", dtime(19, 0))
        forecast = (self.data or {}).get("dwd_forecast", [])
        rain_threshold = self.entry.data.get("regen_skip_threshold_mm", 10.0)

        return compute_next_start_semi(
            zone_id, weekdays_enabled, start_time, forecast, rain_threshold
        )

    def _compute_next_start_voll(
        self, zone_id: str, zone_cfg: dict, zone_storage: dict
    ) -> datetime | None:
        """Compute next start for Voll-Automatik mode."""
        nfk_aktuell = zone_storage["nfk_aktuell"]
        nfk_max = zone_cfg.get("nfk_max", 150)
        schwellwert_pct = self._zone_numbers[zone_id].get(
            "schwellwert", zone_cfg.get("schwellwert_pct", 50)
        )
        start_time = self._zone_times.get(zone_id, {}).get("start", dtime(19, 0))
        forecast = (self.data or {}).get("dwd_forecast", [])
        rain_threshold = self.entry.data.get("regen_skip_threshold_mm", 10.0)

        return compute_next_start_voll(
            zone_id, nfk_aktuell, nfk_max, schwellwert_pct, start_time, forecast, rain_threshold
        )

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

        # Try unified temp_entity first, then fallback to temp_min_entity
        temp_entity = self.entry.data.get("temp_entity") or self.entry.data.get("temp_min_entity")
        t_min_state = self.hass.states.get(temp_entity) if temp_entity else None

        frost_active = False
        if t_min_state and t_min_state.state not in ("unknown", "unavailable"):
            with contextlib.suppress(ValueError):
                frost_active = float(t_min_state.state) < frost_threshold

        if frost_active and not self._frost_active:
            _LOGGER.warning("Frost lock activated: stopping all irrigation")
            self._frost_active = True
            # Stop running zone if any
            if self.running:
                running_zone_id = self.running.zone_id
                zone_cfg = self.entry.data.get("zones", {}).get(self.running.zone_id)
                if zone_cfg:
                    valve_id = zone_cfg.get("valve_entity")
                    if valve_id:
                        await self._valve_off_then_trafo_check(valve_id)
                if self._storage_data:
                    zone_storage = self._storage_data["zones"].get(running_zone_id)
                    if zone_storage:
                        zone_storage["scheduling"]["running_since"] = None
                        zone_storage["scheduling"]["active_zone_remaining_min"] = 0.0
                        await self.storage.async_save_immediate(self._storage_data)
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
            if self._storage_data:
                zone_storage = self._storage_data["zones"].get(zone_id)
                if zone_storage:
                    zone_storage["scheduling"]["running_since"] = None
                    zone_storage["scheduling"]["active_zone_remaining_min"] = 0.0
                    await self.storage.async_save_immediate(self._storage_data)
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
                if self._storage_data:
                    zone_storage = self._storage_data["zones"].get(self.running.zone_id)
                    if zone_storage:
                        zone_storage["scheduling"]["running_since"] = None
                        zone_storage["scheduling"]["active_zone_remaining_min"] = 0.0
            self.running = None
        if self._storage_data:
            for zone_storage in self._storage_data["zones"].values():
                zone_storage["scheduling"]["running_since"] = None
                zone_storage["scheduling"]["active_zone_remaining_min"] = 0.0
            await self.storage.async_save_immediate(self._storage_data)

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
        """Manually start a zone with trafo sequencing through the queue."""
        zone_cfg = self.entry.data.get("zones", {}).get(zone_id)
        if not zone_cfg:
            _LOGGER.error("Zone %s not configured", zone_id)
            return

        if self._frost_active:
            _LOGGER.warning("Cannot start zone %s: frost lock active", zone_id)
            return

        _LOGGER.info("Manual start zone %s for %.1f min", zone_id, dauer_min)
        await self.async_enqueue_start(zone_id, dauer_min)

