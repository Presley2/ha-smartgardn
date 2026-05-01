"""Tests for Node-RED migration service."""
import pytest
from custom_components.irrigation_et0.migration import (
    migrate_from_nodered,
    validate_migration,
)


@pytest.mark.asyncio
async def test_migrate_simple_zone():
    """Test migration of a single zone."""
    legacy_data = {
        "installation_name": "My Garden",
        "location": {"latitude": 51.5, "longitude": 7.5, "elevation": 100},
        "zones": [
            {
                "name": "Front Lawn",
                "soil_type": "loam",
                "root_depth_dm": 20,
                "nfk_max": 100,
            }
        ],
    }

    migrated = await migrate_from_nodered(None, legacy_data)

    assert migrated["name"] == "My Garden"
    assert migrated["latitude"] == 51.5
    assert migrated["longitude"] == 7.5
    assert migrated["elevation"] == 100
    assert len(migrated["zones"]) == 1
    zone = list(migrated["zones"].values())[0]
    assert zone["name"] == "Front Lawn"
    assert zone["soil_type"] == "loam"
    assert zone["nfk_max"] == 100


@pytest.mark.asyncio
async def test_migrate_multiple_zones():
    """Test migration of multiple zones."""
    legacy_data = {
        "installation_name": "Farm",
        "location": {"latitude": 52.0, "longitude": 13.0, "elevation": 50},
        "zones": [
            {"name": "Zone A", "soil_type": "sand", "root_depth_dm": 15, "nfk_max": 50},
            {"name": "Zone B", "soil_type": "clay", "root_depth_dm": 25, "nfk_max": 150},
            {
                "name": "Zone C",
                "soil_type": "loam",
                "root_depth_dm": 20,
                "nfk_max": 100,
            },
        ],
    }

    migrated = await migrate_from_nodered(None, legacy_data)

    assert migrated["name"] == "Farm"
    assert len(migrated["zones"]) == 3
    zones = list(migrated["zones"].values())
    assert zones[0]["name"] == "Zone A"
    assert zones[1]["name"] == "Zone B"
    assert zones[2]["name"] == "Zone C"
    assert zones[0]["nfk_max"] == 50
    assert zones[1]["nfk_max"] == 150


@pytest.mark.asyncio
async def test_migrate_preserves_custom_parameters():
    """Test that custom parameters are preserved during migration."""
    legacy_data = {
        "installation_name": "Custom Farm",
        "location": {"latitude": 48.0, "longitude": 16.0, "elevation": 200},
        "zones": [
            {
                "name": "Vegetables",
                "soil_type": "loam",
                "root_depth_dm": 30,
                "nfk_max": 120,
                "kc": 0.8,
                "schwellwert_pct": 40,
                "zielwert_pct": 90,
                "dauer_min": 45,
                "cs_zyklen": 3,
                "cs_pause_min": 20,
            }
        ],
    }

    migrated = await migrate_from_nodered(None, legacy_data)

    zone = list(migrated["zones"].values())[0]
    assert zone["kc"] == 0.8
    assert zone["schwellwert_pct"] == 40
    assert zone["zielwert_pct"] == 90
    assert zone["dauer_min"] == 45
    assert zone["cs_zyklen"] == 3
    assert zone["cs_pause_min"] == 20


@pytest.mark.asyncio
async def test_migrate_uses_defaults_for_missing_fields():
    """Test that reasonable defaults are used for missing fields."""
    legacy_data = {
        "installation_name": "Minimal",
        "location": {"latitude": 50.0, "longitude": 10.0},
        "zones": [{"name": "Zone"}],
    }

    migrated = await migrate_from_nodered(None, legacy_data)

    zone = list(migrated["zones"].values())[0]
    assert zone["soil_type"] == "loam"  # default
    assert zone["root_depth_dm"] == 20  # default
    assert zone["nfk_max"] == 100  # default
    assert zone["modus"] == "aus"  # default
    assert zone["schwellwert_pct"] == 50  # default
    assert zone["zielwert_pct"] == 80  # default


@pytest.mark.asyncio
async def test_validate_migration_valid_data():
    """Test validation of valid migrated data."""
    valid_data = {
        "name": "My Farm",
        "latitude": 51.5,
        "longitude": 7.5,
        "elevation": 100,
        "zones": {
            "zone-1": {
                "name": "Zone A",
                "nfk_max": 100,
                "root_depth_dm": 20,
            }
        },
    }

    is_valid, issues = await validate_migration(valid_data)

    assert is_valid is True
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_validate_migration_missing_location():
    """Test validation catches missing location data."""
    invalid_data = {
        "name": "My Farm",
        "zones": {"zone-1": {"name": "Zone A", "nfk_max": 100, "root_depth_dm": 20}},
    }

    is_valid, issues = await validate_migration(invalid_data)

    assert is_valid is False
    assert any("latitude" in issue for issue in issues)
    assert any("longitude" in issue for issue in issues)


@pytest.mark.asyncio
async def test_validate_migration_no_zones():
    """Test validation catches missing zones."""
    invalid_data = {
        "name": "My Farm",
        "latitude": 51.5,
        "longitude": 7.5,
        "zones": {},
    }

    is_valid, issues = await validate_migration(invalid_data)

    assert is_valid is False
    assert any("No zones" in issue for issue in issues)


@pytest.mark.asyncio
async def test_validate_migration_invalid_zone_parameters():
    """Test validation catches invalid zone parameters."""
    invalid_data = {
        "name": "My Farm",
        "latitude": 51.5,
        "longitude": 7.5,
        "zones": {
            "zone-1": {
                "name": "Zone A",
                "nfk_max": 0,  # Invalid: must be positive
                "root_depth_dm": 20,
            }
        },
    }

    is_valid, issues = await validate_migration(invalid_data)

    assert is_valid is False
    assert any("invalid nfk_max" in issue for issue in issues)


@pytest.mark.asyncio
async def test_migrate_generates_unique_zone_ids():
    """Test that migration generates unique UUIDs for each zone."""
    legacy_data = {
        "installation_name": "Test",
        "location": {"latitude": 51.5, "longitude": 7.5},
        "zones": [
            {"name": "Zone 1"},
            {"name": "Zone 2"},
            {"name": "Zone 3"},
        ],
    }

    migrated = await migrate_from_nodered(None, legacy_data)

    zone_ids = list(migrated["zones"].keys())
    assert len(zone_ids) == 3
    assert len(set(zone_ids)) == 3  # All unique


@pytest.mark.asyncio
async def test_migrate_ansaat_defaults():
    """Test that ansaat (seed watering) defaults are set."""
    legacy_data = {
        "installation_name": "Test",
        "location": {"latitude": 51.5, "longitude": 7.5},
        "zones": [{"name": "Seed Zone"}],
    }

    migrated = await migrate_from_nodered(None, legacy_data)

    zone = list(migrated["zones"].values())[0]
    assert zone["ansaat_intervall_h"] == 1
    assert zone["ansaat_dauer_min"] == 5
    assert zone["ansaat_laufzeit_tage"] == 21
    assert zone["ansaat_von"] == "06:00"
    assert zone["ansaat_bis"] == "10:00"
