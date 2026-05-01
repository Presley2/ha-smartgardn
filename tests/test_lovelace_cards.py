"""Tests for Lovelace cards."""
import pytest


def test_overview_card_imports():
    """Test that overview-card.js can be imported as a module."""
    # This would require Node.js/JavaScript testing environment
    # For now, test that the file exists and has expected structure
    with open('src/cards/overview-card.js') as f:
        content = f.read()
        assert '@customElement' in content
        assert 'irrigation-overview-card' in content
        assert '_getZoneData' in content
        assert '_formatModus' in content


def test_history_card_imports():
    """Test that history-card.js has expected functions."""
    with open('src/cards/history-card.js') as f:
        content = f.read()
        assert '@customElement' in content
        assert 'irrigation-history-card' in content
        assert '_generatePolylinePoints' in content
        assert '_renderChart' in content


def test_settings_card_imports():
    """Test that settings-card.js has expected functions."""
    with open('src/cards/settings-card.js') as f:
        content = f.read()
        assert '@customElement' in content
        assert 'irrigation-settings-card' in content
        assert '_renderSlider' in content
        assert '_updateNumber' in content
        assert '_getModeLabel' in content


def test_ansaat_card_imports():
    """Test that ansaat-card.js has expected functions."""
    with open('src/cards/ansaat-card.js') as f:
        content = f.read()
        assert '@customElement' in content
        assert 'irrigation-ansaat-card' in content
        assert '_getAnsaatStatus' in content
        assert '_renderTimeline' in content
        assert '_startAnsaat' in content


def test_cards_use_lit_elements():
    """Test that all cards are Lit elements."""
    cards = [
        'src/cards/overview-card.js',
        'src/cards/history-card.js',
        'src/cards/settings-card.js',
        'src/cards/ansaat-card.js',
    ]
    for card_file in cards:
        with open(card_file) as f:
            content = f.read()
            assert 'from \'lit\'' in content or 'from "lit"' in content
            assert 'LitElement' in content
            assert 'html' in content or 'css' in content


def test_cards_have_styles():
    """Test that all cards define CSS styles."""
    cards = [
        'src/cards/overview-card.js',
        'src/cards/history-card.js',
        'src/cards/settings-card.js',
        'src/cards/ansaat-card.js',
    ]
    for card_file in cards:
        with open(card_file) as f:
            content = f.read()
            assert 'static get styles()' in content
            assert 'css`' in content


def test_overview_card_structure():
    """Test overview card has all required methods."""
    with open('src/cards/overview-card.js') as f:
        content = f.read()
        methods = [
            'setConfig',
            'connectedCallback',
            'disconnectedCallback',
            '_getZoneData',
            '_getEntityState',
            '_formatValue',
            'render',
        ]
        for method in methods:
            assert method in content


def test_settings_card_structure():
    """Test settings card has all required methods."""
    with open('src/cards/settings-card.js') as f:
        content = f.read()
        methods = [
            'setConfig',
            '_getZones',
            '_selectZone',
            '_updateNumber',
            '_updateSelect',
            'render',
        ]
        for method in methods:
            assert method in content


def test_cards_dist_exists():
    """Test that built cards exist in dist directory."""
    import os
    dist_cards = [
        'dist/cards/overview-card.js',
        'dist/cards/history-card.js',
        'dist/cards/settings-card.js',
        'dist/cards/ansaat-card.js',
    ]
    for card in dist_cards:
        assert os.path.exists(card), f"{card} not found in dist/"


def test_cards_www_exists():
    """Test that cards are copied to custom_components www directory."""
    import os
    www_cards = [
        'custom_components/irrigation_et0/www/overview-card.js',
        'custom_components/irrigation_et0/www/history-card.js',
        'custom_components/irrigation_et0/www/settings-card.js',
        'custom_components/irrigation_et0/www/ansaat-card.js',
    ]
    for card in www_cards:
        assert os.path.exists(card), f"{card} not found"


def test_manifest_has_lovelace_resources():
    """Test that manifest.json includes Lovelace card resources."""
    import json
    with open('custom_components/irrigation_et0/manifest.json') as f:
        manifest = json.load(f)
        assert 'lovelace' in manifest
        assert 'resources' in manifest['lovelace']
        resources = manifest['lovelace']['resources']
        assert len(resources) == 4

        card_names = ['overview-card.js', 'history-card.js', 'settings-card.js', 'ansaat-card.js']
        resource_urls = [r['url'] for r in resources]
        for card_name in card_names:
            assert any(card_name in url for url in resource_urls)
