# Deployment Guide — Irrigation ET₀

## Option 1: SMB (Recommended for Local Development)

### Prerequisites
- ✅ SMB share enabled on Home Assistant instance
- ✅ Mac has SMB access to HA network
- ✅ Python 3.9+ on local Mac

### Setup (One-time)

**macOS:**
```bash
# Create mount point
mkdir -p /Volumes/homeassistant

# Mount SMB share (replace IP and credentials)
mount_smbfs //homeassistant@192.168.1.100/homeassistant /Volumes/homeassistant
```

Or use Finder: Cmd+K → `smb://homeassistant@192.168.1.100/homeassistant`

### Deploy

```bash
# Set SMB path (if not default)
export SMB_PATH="/Volumes/homeassistant"

# Set HA URL and token for auto-reload (optional)
export HA_URL="http://192.168.1.100:8123"
export HA_TOKEN="<your-long-lived-token>"

# Run deploy
bash deploy-smb.sh
```

**What it does:**
1. ✅ Runs all tests
2. ✅ Copies `custom_components/smartgardn_et0/` to SMB
3. ✅ Triggers HA integration reload (if token provided)
4. ✅ No Home Assistant restart needed (hot-reload)

### Token-Usage
- **Per deploy**: ~100 tokens (just for HA reload call)
- **Cost**: Negligible ✅

---

## Option 2: Direct File Copy (Manual)

If you prefer no scripts:

```bash
# 1. Mount SMB share (macOS)
mount_smbfs //homeassistant@192.168.1.100/homeassistant /Volumes/homeassistant

# 2. Copy integration
cp -r custom_components/smartgardn_et0 /Volumes/homeassistant/custom_components/

# 3. In HA: Settings → Devices & Services → Irrigation ET₀ → ⚙️ → Reload
```

---

## Option 3: Git + SSH (For Remote Servers)

If HA runs on a Linux server with SSH:

```bash
# Copy via rsync over SSH
rsync -av custom_components/smartgardn_et0/ \
  user@192.168.1.100:/config/custom_components/smartgardn_et0/

# Then reload via HA API
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  http://192.168.1.100:8123/api/config/config_entries/entry/<ENTRY_ID>/reload
```

---

## Creating Long-Lived Token (for Auto-Reload)

1. Home Assistant → Settings → Devices & Services
2. Click your user profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Create new token, name it "SMB Deploy"
5. Copy and save: `export HA_TOKEN="eyJ0eXAiOi..."`

---

## Troubleshooting

### SMB Mount Fails
```bash
# Check if share is accessible
ping 192.168.1.100

# Try without credentials (if guest access enabled)
mount_smbfs //192.168.1.100/homeassistant /Volumes/homeassistant

# Check current mounts
mount | grep smbfs
```

### Integration Doesn't Reload
- ✅ Check HA_TOKEN is valid (Settings → Devices & Services)
- ✅ Check ENTRY_ID is correct: `http://192.168.1.100:8123/developer-tools/service` 
- ✅ Try manual reload: Settings → Devices & Services → Irrigation ET₀ → ⚙️ → Reload

### Tests Fail Before Deploy
```bash
python -m pytest tests/ -v
# Fix errors before deploying
```

---

## Development Workflow

**Recommended for rapid iteration:**

```bash
# 1. Make code changes in custom_components/smartgardn_et0/

# 2. Test locally
python -m pytest tests/ -q

# 3. Deploy to HA
bash deploy-smb.sh

# 4. Check results in HA UI (no restart needed)

# 5. Iterate...
```

Each cycle takes ~10-20 seconds (no HA restart overhead).

---

## Production Deployment (via HACS)

Once ready for public use:

```bash
# 1. Push to GitHub
git push origin main

# 2. Create release tag
git tag v0.1.0
git push origin v0.1.0

# 3. GitHub Actions automatically:
#    - Runs tests ✅
#    - Builds distribution ZIP
#    - Creates release with artifacts

# 4. Submit to HACS
#    - Fork HACS/core repo
#    - Add entry to default_repositories.json
#    - PR to HACS

# 5. Users install via:
#    HACS → Integrations → Search "Irrigation ET₀" → Install
```

---

## SMB vs. Cloud Deployment Comparison

| Aspect | SMB (Local) | Cloud (MCP) |
|--------|-----------|----------|
| **Token Cost** | ~100/deploy | 6,000-10,000/deploy |
| **Speed** | <5s | 30-60s |
| **Network** | Local only | Anywhere |
| **Reliability** | Direct connection | Internet-dependent |
| **Setup** | SMB enable | OAuth setup |
| **Recommendation** | ✅ Development | Remote work |

---

## Deployment Checklist

Before deploying to production:

- [ ] All tests pass: `pytest tests/ -q`
- [ ] No ruff linting errors: `ruff check custom_components/`
- [ ] Manifest.json valid: `python -c "import json; json.load(open('custom_components/smartgardn_et0/manifest.json'))"`
- [ ] README updated
- [ ] Version bumped in manifest.json
- [ ] Git changes committed: `git add -A && git commit -m "..."`
- [ ] Tested on actual HA instance
- [ ] No restart needed (hot-reload verified)

---

**Last Updated**: 2026-05-01  
**Author**: Michael Richter
