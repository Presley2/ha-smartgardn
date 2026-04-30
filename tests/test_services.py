"""Tests for Phase 6 services and events."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_et0.const import DOMAIN
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator, QueueItem


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_start_zone_enqueues_zone(hass: HomeAssistant) -> None:
    """Test that async_start_zone correctly enqueues a zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        with patch.object(coordinator, "_run_next_in_queue", new_callable=AsyncMock):
            await coordinator.async_start_zone("select.test_entry_id_z1_modus", 30.0)
            assert len(coordinator.queue) == 1
            assert coordinator.queue[0].zone_id == "z1"
            assert coordinator.queue[0].dauer_min == 30.0
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_start_zone_fires_event(hass: HomeAssistant) -> None:
    """Test that async_start_zone fires irrigation_et0_zone_started event."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        from homeassistant.core import Event

        fired_events: list[Event] = []

        def capture_event(event: Event) -> None:
            fired_events.append(event)

        hass.bus.async_listen("irrigation_et0_zone_started", capture_event)

        with patch.object(coordinator, "_run_next_in_queue", new_callable=AsyncMock):
            await coordinator.async_start_zone("select.test_entry_id_z1_modus", 30.0)
            # Let async_fire_event complete
            await hass.async_block_till_done()

        assert len(fired_events) > 0
        assert fired_events[-1].data["zone_id"] == "z1"
        assert fired_events[-1].data["duration_min"] == 30.0
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_start_zone_respects_frost_lock(hass: HomeAssistant) -> None:
    """Test that async_start_zone is blocked when frost lock is active."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        coordinator._frost_active = True

        with patch.object(coordinator, "_run_next_in_queue", new_callable=AsyncMock):
            await coordinator.async_start_zone("select.test_entry_id_z1_modus", 30.0)
            # Queue should be empty because frost lock blocked it
            assert len(coordinator.queue) == 0
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_start_zone_invalid_entity_id(hass: HomeAssistant) -> None:
    """Test that async_start_zone handles invalid entity IDs gracefully."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        with patch.object(coordinator, "_run_next_in_queue", new_callable=AsyncMock):
            # Invalid entity ID (not starting with select.)
            await coordinator.async_start_zone("switch.invalid", 30.0)
            assert len(coordinator.queue) == 0

            # Invalid format
            await coordinator.async_start_zone("select.invalid_format", 30.0)
            assert len(coordinator.queue) == 0
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_stop_zone_stops_running_zone(hass: HomeAssistant) -> None:
    """Test that async_stop_zone stops a running zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        # Set up a running zone
        coordinator.running = QueueItem("z1", 30.0, 0, 10.0, datetime.now(UTC))

        with patch.object(coordinator, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            await coordinator.async_stop_zone("select.test_entry_id_z1_modus")
            assert coordinator.running is None
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_stop_zone_removes_from_queue(hass: HomeAssistant) -> None:
    """Test that async_stop_zone removes the zone from the queue."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
                "z2": {
                    "zone_name": "Z2",
                    "valve_entity": "switch.mv2",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        # Add items to queue
        coordinator.queue.append(QueueItem("z1", 30.0, 0, 10.0))
        coordinator.queue.append(QueueItem("z2", 20.0, 0, 10.0))
        assert len(coordinator.queue) == 2

        # Stop z1
        await coordinator.async_stop_zone("select.test_entry_id_z1_modus")
        assert len(coordinator.queue) == 1
        assert coordinator.queue[0].zone_id == "z2"
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_stop_zone_fires_event(hass: HomeAssistant) -> None:
    """Test that async_stop_zone fires irrigation_et0_zone_finished event."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        from homeassistant.core import Event

        coordinator.running = QueueItem("z1", 30.0, 0, 10.0, datetime.now(UTC))

        fired_events: list[Event] = []

        def capture_event(event: Event) -> None:
            fired_events.append(event)

        hass.bus.async_listen("irrigation_et0_zone_finished", capture_event)

        with patch.object(coordinator, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            await coordinator.async_stop_zone("select.test_entry_id_z1_modus")
            await hass.async_block_till_done()

        assert len(fired_events) > 0
        assert fired_events[-1].data["zone_id"] == "z1"
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_stop_all_clears_queue_and_stops_running(hass: HomeAssistant) -> None:
    """Test that async_stop_all clears queue and stops running zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
                "z2": {
                    "zone_name": "Z2",
                    "valve_entity": "switch.mv2",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        # Set up running zone and queued items
        coordinator.running = QueueItem("z1", 30.0, 0, 10.0, datetime.now(UTC))
        coordinator.queue.append(QueueItem("z2", 20.0, 0, 10.0))

        with patch.object(coordinator, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            await coordinator.async_stop_all()
            assert coordinator.running is None
            assert len(coordinator.queue) == 0
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_stop_all_fires_event(hass: HomeAssistant) -> None:
    """Test that async_stop_all fires irrigation_et0_stop_all event."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"), patch(
        "custom_components.irrigation_et0.coordinator.async_track_time_interval"
    ):
        await coordinator.async_setup()

    try:
        from homeassistant.core import Event

        coordinator.running = QueueItem("z1", 30.0, 0, 10.0, datetime.now(UTC))

        fired_events: list[Event] = []

        def capture_event(event: Event) -> None:
            fired_events.append(event)

        hass.bus.async_listen("irrigation_et0_stop_all", capture_event)

        with patch.object(coordinator, "_valve_off_then_trafo_check", new_callable=AsyncMock):
            await coordinator.async_stop_all()
            await hass.async_block_till_done()

        assert len(fired_events) > 0
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_extract_zone_id_from_entity_valid(hass: HomeAssistant) -> None:
    """Test zone ID extraction from valid entity ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                "zone_uuid_123": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "kc": 0.8,
                },
            },
        },
    )

    coordinator = IrrigationCoordinator(hass, entry)

    zone_id = coordinator._extract_zone_id_from_entity("select.test_entry_id_zone_uuid_123_modus")
    assert zone_id == "zone_uuid_123"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_extract_zone_id_from_entity_wrong_entry_id(hass: HomeAssistant) -> None:
    """Test zone ID extraction from entity with wrong entry ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {},
        },
    )

    coordinator = IrrigationCoordinator(hass, entry)

    # Entity ID from different entry
    zone_id = coordinator._extract_zone_id_from_entity("select.other_entry_id_zone_123_modus")
    assert zone_id is None


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_extract_zone_id_from_entity_invalid_format(hass: HomeAssistant) -> None:
    """Test zone ID extraction from entity with invalid format."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={
            "name": "Garten",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {},
        },
    )

    coordinator = IrrigationCoordinator(hass, entry)

    # Not a select entity
    assert coordinator._extract_zone_id_from_entity("switch.test_entry_id_zone_123") is None

    # Missing _modus suffix
    assert coordinator._extract_zone_id_from_entity("select.test_entry_id_zone_123") is None

    # Empty zone ID
    assert (
        coordinator._extract_zone_id_from_entity("select.test_entry_id__modus") is None
    )
