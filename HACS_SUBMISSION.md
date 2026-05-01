# HACS Submission Checklist - SmartGardn ET0

This document tracks repository readiness for HACS inclusion.

## Repository

| Requirement | Status | Details |
|---|---|---|
| Public GitHub repository | ✅ | https://github.com/michaelrichter/ha-smartgardn-et0 |
| Default branch | ✅ | `main` |
| Issues enabled | ✅ | Enabled in repository settings |
| Active repository | ✅ | Not archived |

## Required Files

| File | Status | Location |
|---|---|---|
| `hacs.json` | ✅ | `/hacs.json` |
| `manifest.json` | ✅ | `/custom_components/smartgardn_et0/manifest.json` |
| `README.md` | ✅ | `/README.md` |
| `LICENSE` | ✅ | `/LICENSE` |
| Brand icon | ✅ | `/custom_components/smartgardn_et0/brand/icon.png` |
| Brand icon @2x | ✅ | `/custom_components/smartgardn_et0/brand/icon@2x.png` |
| Dark icon | ✅ | `/custom_components/smartgardn_et0/brand/dark_icon.png` |
| Dark icon @2x | ✅ | `/custom_components/smartgardn_et0/brand/dark_icon@2x.png` |

## Manifest Snapshot

Current key fields from `manifest.json`:

```json
{
  "domain": "smartgardn_et0",
  "name": "SmartGardn ET₀",
  "version": "0.2.1",
  "documentation": "https://github.com/michaelrichter/ha-smartgardn-et0",
  "issue_tracker": "https://github.com/michaelrichter/ha-smartgardn-et0/issues",
  "config_flow": true
}
```

## HACS Config Snapshot

Current `hacs.json`:

```json
{
  "name": "SmartGardn ET₀",
  "render_readme": true,
  "country": ["DE", "AT", "CH"],
  "homeassistant": "2024.10.0",
  "zip_release": false
}
```

## Release Readiness

| Requirement | Status | Details |
|---|---|---|
| Tagged release present | ⚠️ Verify | Ensure latest tag/release exists on GitHub (for example `v0.2.1`) |
| Release workflow valid | ✅ | `.github/workflows/release.yml` includes `id: create_release` |
| Version consistency | ✅ | `manifest.json`, `const.py`, `pyproject.toml` aligned to `0.2.1` |

## Submit to HACS

1. Open: https://github.com/hacs/default/issues/new
2. Create inclusion request for: `michaelrichter/ha-smartgardn-et0`
3. Include:
   - Repository: https://github.com/michaelrichter/ha-smartgardn-et0
   - Latest release URL (tagged version)
   - Short functional summary

## Handy Links

- Repository: https://github.com/michaelrichter/ha-smartgardn-et0
- README: https://github.com/michaelrichter/ha-smartgardn-et0#readme
- Releases: https://github.com/michaelrichter/ha-smartgardn-et0/releases
- Issues: https://github.com/michaelrichter/ha-smartgardn-et0/issues
- HACS docs: https://www.hacs.xyz/docs/publish/include/

Last updated: 2026-05-01
