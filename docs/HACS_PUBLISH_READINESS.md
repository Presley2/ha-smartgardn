# HACS Publish Readiness (Quick Gate)

Use this checklist before creating a release tag and submitting to HACS.

## Metadata

- [ ] Repository URL in `README.md`, `info.md`, and `manifest.json` is `https://github.com/michaelrichter/ha-smartgardn-et0`
- [ ] `manifest.json` version matches release version
- [ ] `custom_components/smartgardn_et0/const.py` version matches release version
- [ ] `pyproject.toml` version matches release version

## HACS Structure

- [ ] `hacs.json` exists at repo root
- [ ] `custom_components/smartgardn_et0/manifest.json` exists
- [ ] `custom_components/smartgardn_et0/translations/` contains at least one language file
- [ ] Brand assets exist in `custom_components/smartgardn_et0/brand/`

## Release

- [ ] GitHub release tag exists (for example `v0.2.1`)
- [ ] Release notes mention breaking changes (if any)
- [ ] `.github/workflows/release.yml` still contains `id: create_release`

## Sanity

- [ ] README installation URL matches real repository
- [ ] Services listed in README match `services.yaml`
- [ ] No obvious stale links to old repositories/users
