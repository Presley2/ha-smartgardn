#!/usr/bin/env python3
"""Sync custom card files from src/ to www/ directory."""

import shutil
from pathlib import Path

def sync_cards():
    """Copy all card files from src/cards to www/."""
    root = Path(__file__).parent.parent
    src_dir = root / "src" / "cards"
    www_dir = root / "custom_components" / "smartgardn_et0" / "www"

    if not src_dir.exists():
        print(f"❌ Source directory not found: {src_dir}")
        return False

    if not www_dir.exists():
        www_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created www directory: {www_dir}")

    card_files = list(src_dir.glob("*-card.js"))

    if not card_files:
        print(f"❌ No card files found in {src_dir}")
        return False

    for src_file in card_files:
        dst_file = www_dir / src_file.name
        shutil.copy2(src_file, dst_file)
        print(f"✓ Synced: {src_file.name}")

    print(f"✓ All {len(card_files)} cards synced successfully!")
    return True

if __name__ == "__main__":
    success = sync_cards()
    exit(0 if success else 1)
