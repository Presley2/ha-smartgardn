"""Test Lovelace card registration and infrastructure."""

from pathlib import Path
import json


def test_card_files_exist():
    """Test that all card files exist in www/."""
    www_path = Path(__file__).parent.parent / "custom_components" / "smartgardn_et0" / "www"
    required_cards = [
        "overview-card.js",
        "history-card.js",
        "settings-card.js",
        "ansaat-card.js",
    ]

    for card in required_cards:
        card_path = www_path / card
        assert card_path.exists(), f"Card file not found: {card_path}"


def test_card_structure():
    """Test that all card files have valid structure."""
    www_path = Path(__file__).parent.parent / "custom_components" / "smartgardn_et0" / "www"
    required_cards = [
        "overview-card.js",
        "history-card.js",
        "settings-card.js",
        "ansaat-card.js",
    ]

    for card in required_cards:
        card_path = www_path / card
        with open(card_path) as f:
            content = f.read()
            # Verify basic structure
            assert "@customElement(" in content, f"{card}: Missing @customElement decorator"
            assert "extends LitElement" in content, f"{card}: Missing LitElement extension"
            assert "render()" in content, f"{card}: Missing render() method"
            assert ("static styles" in content or "static get styles" in content), f"{card}: Missing styles"


def test_card_urls_in_manifest():
    """Test that manifest.json contains card resource URLs."""
    manifest_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "smartgardn_et0"
        / "manifest.json"
    )

    with open(manifest_path) as f:
        manifest = json.load(f)

    assert "lovelace" in manifest, "manifest.json missing 'lovelace' section"
    assert "resources" in manifest["lovelace"], "manifest.json missing 'resources'"

    # Check that all cards are in resources
    resources = manifest["lovelace"]["resources"]
    required_cards = [
        "overview-card.js",
        "history-card.js",
        "settings-card.js",
        "ansaat-card.js",
    ]

    for card in required_cards:
        card_url = f"/smartgardn_et0_cards/{card}"
        assert any(r["url"] == card_url for r in resources), (
            f"Card {card} not found in manifest resources"
        )


def test_card_imports_consistent():
    """Test that source and www card files are identical."""
    src_path = Path(__file__).parent.parent / "src" / "cards"
    www_path = Path(__file__).parent.parent / "custom_components" / "smartgardn_et0" / "www"

    required_cards = [
        "overview-card.js",
        "history-card.js",
        "settings-card.js",
        "ansaat-card.js",
    ]

    for card in required_cards:
        src_file = src_path / card
        www_file = www_path / card

        assert src_file.exists(), f"Source card not found: {src_file}"
        assert www_file.exists(), f"WWW card not found: {www_file}"

        # Files should be identical (or www is newer)
        with open(src_file) as f:
            src_content = f.read()
        with open(www_file) as f:
            www_content = f.read()

        # Allow www to be same or newer
        if src_content != www_content:
            # This is okay if www_path is more recent (build output)
            # But warn if src is newer
            assert src_file.stat().st_mtime <= www_file.stat().st_mtime, (
                f"Source card {card} is newer than www version - need to sync"
            )


def test_sync_cards_script():
    """Test that sync_cards.py script exists and is executable."""
    sync_script = Path(__file__).parent.parent / "scripts" / "sync_cards.py"
    assert sync_script.exists(), "sync_cards.py script not found"
    assert sync_script.stat().st_mode & 0o111, "sync_cards.py is not executable"

    # Verify it's a valid Python script
    with open(sync_script) as f:
        content = f.read()
        assert "def sync_cards()" in content, "sync_cards() function not found"


def test_setup_hooks_script():
    """Test that setup_hooks.py script exists and is executable."""
    hooks_script = Path(__file__).parent.parent / "scripts" / "setup_hooks.py"
    assert hooks_script.exists(), "setup_hooks.py script not found"
    assert hooks_script.stat().st_mode & 0o111, "setup_hooks.py is not executable"

    # Verify it's a valid Python script
    with open(hooks_script) as f:
        content = f.read()
        assert "def setup_hooks()" in content, "setup_hooks() function not found"


def test_precommit_hook():
    """Test that pre-commit hook exists and is executable."""
    hook_path = Path(__file__).parent.parent / ".github" / "hooks" / "pre-commit"
    assert hook_path.exists(), "pre-commit hook not found"
    assert hook_path.stat().st_mode & 0o111, "pre-commit hook is not executable"

    # Verify it's a valid shell script
    with open(hook_path) as f:
        content = f.read()
        assert "#!/bin/bash" in content, "pre-commit hook missing shebang"
        assert "sync_cards.py" in content, "pre-commit hook doesn't call sync_cards.py"


def test_installation_test_guide():
    """Test that INSTALLATION_CARDS_TEST.md exists."""
    guide_path = (
        Path(__file__).parent.parent / "docs" / "INSTALLATION_CARDS_TEST.md"
    )
    assert guide_path.exists(), "INSTALLATION_CARDS_TEST.md not found"

    with open(guide_path) as f:
        content = f.read()
        assert "Installation" in content, "Guide missing Installation section"
        assert "Testing" in content, "Guide missing Testing section"
        assert "Debugging" in content, "Guide missing Debugging section"


def test_manifest_static_path():
    """Test that manifest.json has correct static path configuration."""
    manifest_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "smartgardn_et0"
        / "manifest.json"
    )

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Verify resources have correct structure
    resources = manifest["lovelace"]["resources"]
    for resource in resources:
        assert "url" in resource, "Resource missing 'url' field"
        assert "type" in resource, "Resource missing 'type' field"
        assert resource["type"] == "module", f"Resource type should be 'module', got {resource['type']}"
        assert resource["url"].startswith("/smartgardn_et0_cards/"), f"Invalid URL: {resource['url']}"
