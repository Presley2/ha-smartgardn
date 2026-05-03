"""Tests for Phase 4 coordinator logic."""

from __future__ import annotations

from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartgardn_et0.const import DOMAIN
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator, QueueItem


async def _setup_coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> IrrigationCoordinator:
    """Setup coordinator with async_track functions mocked."""
    entry.add_to_hass(hass)
    coord = IrrigationCoordinator(hass, entry)
    with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
            await coord.async_setup()
    return coord


def create_sample_entry() -> MockConfigEntry:
    """Create a sample config entry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "G",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "humidity_min_entity": "sensor.rh_min",
            "humidity_max_entity": "sensor.rh_max",
            "solar_entity": "sensor.solar",
            "wind_entity": "sensor.wind",
            "rain_entity": "sensor.rain",
            "et_methode": "fao56",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                    "schwellwert_pct": 50,
                    "zielwert_pct": 80,
                },
                "z2": {
                    "zone_name": "Z2",
                    "valve_entity": "switch.mv2",
                    "nfk_max": 150,
                    "kc": 0.8,
                    "schwellwert_pct": 50,
                    "zielwert_pct": 80,
                },
            },
        },
    )


@pytest.fixture
def sample_entry() -> MockConfigEntry:
    """Return a sample config entry for testing."""
    return create_sample_entry()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_coordinator_setup_initializes_queue(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that coordinator initializes empty queue on setup."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        assert len(coord.queue) == 0
        assert coord.running is None
        assert coord._frost_active is False
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_enqueue_start_adds_item_to_queue(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that enqueue_start adds item to queue."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock):
            await coord.async_enqueue_start("z1", 30.0)
            assert len(coord.queue) == 1
            assert coord.queue[0].zone_id == "z1"
            assert coord.queue[0].dauer_min == 30.0
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_enqueue_start_triggers_run_if_queue_empty(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that enqueue_start calls _run_next_in_queue if queue is empty."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock) as mock_run:
            await coord.async_enqueue_start("z1", 30.0)
            mock_run.assert_called_once()
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_enqueue_start_does_not_trigger_run_if_queue_not_empty(
    hass: HomeAssistant, sample_entry: MockConfigEntry
) -> None:
    """Test that enqueue_start does NOT call _run_next_in_queue if queue is not empty."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock) as mock_run:
            # Add first item
            await coord.async_enqueue_start("z1", 30.0)
            mock_run.reset_mock()

            # Add second item while first is running
            coord.running = coord.queue[0]
            coord.queue.clear()
            await coord.async_enqueue_start("z2", 20.0)

            # Should not call _run_next_in_queue
            mock_run.assert_not_called()
            assert len(coord.queue) == 1
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_queue_fifo_order(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that queue maintains FIFO order."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock):
            await coord.async_enqueue_start("z1", 30.0)
            await coord.async_enqueue_start("z2", 20.0)
            await coord.async_enqueue_start("z1", 15.0)

            assert coord.queue[0].zone_id == "z1"
            assert coord.queue[0].dauer_min == 30.0
            assert coord.queue[1].zone_id == "z2"
            assert coord.queue[1].dauer_min == 20.0
            assert coord.queue[2].zone_id == "z1"
            assert coord.queue[2].dauer_min == 15.0
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_enqueue_start_with_cycle_and_soak(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that enqueue_start preserves Cycle & Soak params."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock):
            await coord.async_enqueue_start("z1", 30.0, cs_cycles=3, cs_pause_min=15.0)
            assert coord.queue[0].cs_remaining == 3
            assert coord.queue[0].cs_pause_min == 15.0
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_trafo_on_then_valve(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test trafo sequencing: turn on trafo, wait, turn on valve."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(coord, "_switch_service", new_callable=AsyncMock) as mock_switch:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await coord._trafo_on_then_valve("switch.mv1")

                calls = mock_switch.call_args_list
                assert len(calls) == 2
                assert calls[0] == call("turn_on", "switch.trafo")
                assert calls[1] == call("turn_on", "switch.mv1")
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_valve_off_then_trafo_check_when_all_off(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test valve off sequence: turn off valve, wait, turn off trafo if all valves off."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Set all valve states to "off"
        hass.states.async_set("switch.mv1", "off")
        hass.states.async_set("switch.mv2", "off")

        with patch.object(coord, "_switch_service", new_callable=AsyncMock) as mock_switch:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await coord._valve_off_then_trafo_check("switch.mv1")

                calls = mock_switch.call_args_list
                assert len(calls) == 2
                assert calls[0] == call("turn_off", "switch.mv1")
                assert calls[1] == call("turn_off", "switch.trafo")
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_valve_off_then_trafo_check_when_one_on(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test valve off sequence: don't turn off trafo if other valve still on."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Set valve 1 to "off", valve 2 to "on"
        hass.states.async_set("switch.mv1", "off")
        hass.states.async_set("switch.mv2", "on")

        with patch.object(coord, "_switch_service", new_callable=AsyncMock) as mock_switch:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await coord._valve_off_then_trafo_check("switch.mv1")

                calls = mock_switch.call_args_list
                # Should only turn off the valve, not the trafo
                assert len(calls) == 1
                assert calls[0] == call("turn_off", "switch.mv1")
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_frost_lock_stops_running_zone(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that frost lock stops a running zone."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Set up a running zone
        coord.running = QueueItem("z1", 30.0, 0, 10.0, started_at=datetime.now(UTC))

        with patch.object(coord, "_valve_off_then_trafo_check", new_callable=AsyncMock) as mock_off:
            hass.states.async_set("sensor.t_min", "-2.0")
            await coord._check_frost_and_lock()

            assert coord._frost_active is True
            assert coord.running is None
            mock_off.assert_called_once()
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_frost_lock_clears_queue(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that frost lock clears the queue."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Add items to queue
        with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock):
            await coord.async_enqueue_start("z1", 30.0)
            await coord.async_enqueue_start("z2", 20.0)
            assert len(coord.queue) == 2

        with patch.object(coord, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            hass.states.async_set("sensor.t_min", "-2.0")
            await coord._check_frost_and_lock()

            assert len(coord.queue) == 0
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_frost_lock_fires_event_on_activation(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that frost lock fires event on activation."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        events_fired: list[str] = []
        hass.bus.async_listen("smartgardn_et0_frost_lock", lambda e: events_fired.append("lock"))

        with patch.object(coord, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            hass.states.async_set("sensor.t_min", "-2.0")
            await coord._check_frost_and_lock()

            await hass.async_block_till_done()
            assert "lock" in events_fired
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_frost_lock_fires_event_on_release(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that frost lock fires event on release."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Activate frost lock first
        with patch.object(coord, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            hass.states.async_set("sensor.t_min", "-2.0")
            await coord._check_frost_and_lock()

        events_fired: list[str] = []
        hass.bus.async_listen("smartgardn_et0_frost_release", lambda e: events_fired.append("release"))

        # Release frost lock
        hass.states.async_set("sensor.t_min", "10.0")
        await coord._check_frost_and_lock()

        await hass.async_block_till_done()
        assert "release" in events_fired
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_failsafe_check_detects_trafo_stuck_on(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that failsafe detects trafo on when all valves off."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        hass.states.async_set("switch.trafo", "on")
        hass.states.async_set("switch.mv1", "off")
        hass.states.async_set("switch.mv2", "off")

        with patch.object(coord, "_switch_service", new_callable=AsyncMock) as mock_switch:
            await coord._failsafe_check()

            mock_switch.assert_called_once_with("turn_off", "switch.trafo")
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_failsafe_check_ignores_trafo_off(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that failsafe doesn't complain if trafo is already off."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        hass.states.async_set("switch.trafo", "off")
        hass.states.async_set("switch.mv1", "off")
        hass.states.async_set("switch.mv2", "off")

        with patch.object(coord, "_switch_service", new_callable=AsyncMock) as mock_switch:
            await coord._failsafe_check()

            # Should not call switch service
            mock_switch.assert_not_called()
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_compute_next_start_semi_finds_next_weekday(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that semi-automatik mode finds next enabled weekday."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Set up weekdays: only Monday enabled
        coord._zone_weekdays["z1"] = {
            "monday": True,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
            "sunday": False,
        }
        coord._zone_times["z1"]["start"] = time(19, 0)

        zone_cfg = sample_entry.data["zones"]["z1"]
        zone_storage = {
            "nfk_aktuell": 100.0,
            "scheduling": {},
        }

        next_dt = coord._compute_next_start_semi("z1", zone_cfg, zone_storage)

        assert next_dt is not None
        # Should be on a Monday at 19:00
        assert next_dt.weekday() == 0  # Monday
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_compute_next_start_voll_returns_soon_if_below_threshold(
    hass: HomeAssistant, sample_entry: MockConfigEntry
) -> None:
    """Test that voll mode returns soon if NFK below threshold."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        zone_cfg = sample_entry.data["zones"]["z1"]
        zone_storage = {
            "nfk_aktuell": 60.0,  # 60% of 150, below 50% threshold
        }

        next_dt = coord._compute_next_start_voll("z1", zone_cfg, zone_storage)

        assert next_dt is not None
        # Should be very soon
        now = datetime.now(UTC)
        assert (next_dt - now).total_seconds() < 120  # Within 2 minutes
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_compute_next_start_voll_returns_none_if_above_threshold(
    hass: HomeAssistant, sample_entry: MockConfigEntry
) -> None:
    """Test that voll mode returns None if NFK above threshold."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        zone_cfg = sample_entry.data["zones"]["z1"]
        zone_storage = {
            "nfk_aktuell": 100.0,  # 100 out of 150, above 50% threshold
        }

        next_dt = coord._compute_next_start_voll("z1", zone_cfg, zone_storage)

        assert next_dt is None
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_compute_next_start_ansaat_within_window(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test ansaat mode within active window."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Set window to 6:00 - 10:00
        coord._zone_times["z1"]["ansaat_von"] = time(6, 0)
        coord._zone_times["z1"]["ansaat_bis"] = time(10, 0)
        coord._zone_numbers["z1"]["ansaat_intervall"] = 60.0

        with patch("custom_components.smartgardn_et0.coordinator.datetime") as mock_dt:
            # Set time to 8:00
            now = datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = now
            mock_dt.combine = datetime.combine

            zone_cfg = sample_entry.data["zones"]["z1"]
            zone_storage = {"nfk_aktuell": 100.0}

            next_dt = coord._compute_next_start_ansaat("z1", zone_cfg, zone_storage)

            # Should be about 60 minutes from now
            assert next_dt is not None
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_daily_calc_with_fao56_method(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test daily calc with FAO56 method computes ET0."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Set up weather sensors
        hass.states.async_set("sensor.t_min", "15.0")
        hass.states.async_set("sensor.t_max", "25.0")
        hass.states.async_set("sensor.rh_min", "40.0")
        hass.states.async_set("sensor.rh_max", "90.0")
        hass.states.async_set("sensor.solar", "400.0")
        hass.states.async_set("sensor.wind", "2.0")
        hass.states.async_set("sensor.rain", "0.0")

        with patch.object(coord.storage, "async_save_immediate", new_callable=AsyncMock):
            with patch("custom_components.smartgardn_et0.coordinator.calc_et0_fao56") as mock_et0:
                mock_et0.return_value = 5.0

                await coord._daily_calc()

                # Verify ET0 calculation was called
                mock_et0.assert_called_once()
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_daily_calc_fires_calc_done_event(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that daily calc fires calc_done event."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        hass.states.async_set("sensor.t_min", "15.0")
        hass.states.async_set("sensor.t_max", "25.0")
        hass.states.async_set("sensor.rh_min", "40.0")
        hass.states.async_set("sensor.rh_max", "90.0")
        hass.states.async_set("sensor.solar", "400.0")
        hass.states.async_set("sensor.wind", "2.0")
        hass.states.async_set("sensor.rain", "0.0")

        events_fired: list[str] = []
        hass.bus.async_listen("smartgardn_et0_calc_done", lambda e: events_fired.append("done"))

        with patch.object(coord.storage, "async_save_immediate", new_callable=AsyncMock):
            with patch("custom_components.smartgardn_et0.coordinator.calc_et0_fao56", return_value=5.0):
                await coord._daily_calc()

        await hass.async_block_till_done()
        assert "done" in events_fired
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_daily_calc_continues_with_fallback_if_missing_temps(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that daily calc continues with fallback when temps missing (Phase 5.3 reliability)."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        # Don't set t_min/t_max
        with patch.object(coord.storage, "async_save_immediate", new_callable=AsyncMock) as mock_save:
            await coord._daily_calc()

            # Should save with fallback ET0 (last_known or 0)
            mock_save.assert_called_once()
            call_args = mock_save.call_args[0][0]
            assert call_args["globals"]["letzte_et0_berechnung"] is not None
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_daily_calc_skips_if_no_storage(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that daily calc skips if storage not loaded."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        coord._storage_data = None
        hass.states.async_set("sensor.t_min", "15.0")
        hass.states.async_set("sensor.t_max", "25.0")

        with patch.object(coord.storage, "async_save_immediate", new_callable=AsyncMock) as mock_save:
            await coord._daily_calc()

            # Should not save
            mock_save.assert_not_called()
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_switch_service_calls_homeassistant_service(
    hass: HomeAssistant, sample_entry: MockConfigEntry
) -> None:
    """Test that _switch_service calls the correct HA service."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        with patch.object(hass, "services") as mock_services:
            mock_services.async_call = AsyncMock()
            await coord._switch_service("turn_on", "switch.test")

            mock_services.async_call.assert_called_once_with("homeassistant", "turn_on", {"entity_id": "switch.test"})
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_zone_done_clears_cs_and_runs_next(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that zone_done transitions to next queue item when C&S is done."""
    coord = await _setup_coordinator(hass, sample_entry)
    try:
        hass.states.async_set("switch.mv1", "on")
        hass.states.async_set("switch.mv2", "off")

        # Set up running item
        coord.running = QueueItem("z1", 30.0, 0, 10.0, started_at=datetime.now(UTC))

        events_fired: list[str] = []
        hass.bus.async_listen("smartgardn_et0_zone_finished", lambda e: events_fired.append(e.data.get("zone_id")))

        with patch.object(coord, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            with patch.object(coord, "_run_next_in_queue", new_callable=AsyncMock):
                await coord._zone_done()

        await hass.async_block_till_done()
        assert "z1" in events_fired
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_zone_done_handles_cycle_and_soak(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that zone_done handles C&S by scheduling via async_track_point_in_time."""
    from unittest.mock import call

    coord = await _setup_coordinator(hass, sample_entry)
    try:
        hass.states.async_set("switch.mv1", "on")
        hass.states.async_set("switch.mv2", "off")

        # Set up running item with C&S remaining
        coord.running = QueueItem("z1", 30.0, 2, 10.0, started_at=datetime.now(UTC))

        with patch.object(coord, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_point_in_time") as mock_track:
                # Mock returns a dummy unsubscriber function
                mock_track.return_value = MagicMock()

                await coord._zone_done()

                # Should register async_track_point_in_time for the C&S pause
                assert mock_track.called
                # Check that _zone_cs_pause_done callback is registered
                call_args = mock_track.call_args
                assert call_args[0][0] == coord.hass
                assert call_args[0][2] is not None  # pause_end time
    finally:
        await coord.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_shutdown_clears_zone_done_unsubs(hass: HomeAssistant, sample_entry: MockConfigEntry) -> None:
    """Test that shutdown clears zone_done unsubscribers."""
    coord = await _setup_coordinator(hass, sample_entry)

    unsub_mock = MagicMock()
    coord._zone_done_unsub["z1"] = unsub_mock

    await coord.async_shutdown()

    unsub_mock.assert_called_once()
    assert len(coord._zone_done_unsub) == 0
