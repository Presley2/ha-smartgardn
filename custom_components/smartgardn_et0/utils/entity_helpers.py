"""Entity ID parsing and manipulation helpers."""

from __future__ import annotations


def extract_zone_id_from_entity(entity_id: str) -> str | None:
    """Extract zone_id from select.{entry_id}_{zone_id}_modus entity ID.

    Args:
        entity_id: The entity ID to parse (e.g., "select.smartgardn_z1_modus")

    Returns:
        The zone_id if successful, None otherwise
    """
    if not entity_id.startswith("select."):
        return None

    # Format: select.{entry_id}_{zone_id}_modus
    try:
        # Remove 'select.' prefix
        without_prefix = entity_id[7:]
        # Remove '_modus' suffix
        if without_prefix.endswith("_modus"):
            without_suffix = without_prefix[:-6]
            # Extract zone_id (last component after last _)
            parts = without_suffix.rsplit("_", 1)
            if len(parts) == 2:
                return parts[1]
    except (ValueError, AttributeError):
        pass

    return None
