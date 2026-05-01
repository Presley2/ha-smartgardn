# Quick Start — Irrigation ET₀

## Setup (First Time)

### Step 1: Ensure SMB Mount

```bash
# Check if already mounted
mount | grep "192.168.178.92"

# If not mounted:
mount_smbfs //Michael@192.168.178.92/config /private/tmp/ha_mount
```

### Step 2: Deploy Integration

```bash
cd /Users/michael/irrigation-ha
bash deploy-smb.sh
```

**Output:**
```
🚀 Irrigation ET₀ SMB Deploy
✅ SMB path accessible
✅ Integration copied to /private/tmp/ha_mount/custom_components/irrigation_et0
```

### Step 3: Configure in HA (First Time Only)

1. Open Home Assistant: http://192.168.178.92:8123
2. **Settings → Devices & Services → Create Integration**
3. Search for **"Irrigation ET₀"**
4. Complete 4-step wizard:
   - **Step 1 - Anlage**: 
     - Name: e.g., "Garten Bad Nauheim"
     - Location: Click map, select coordinates (no manual typing!)
     - Elevation: Enter height in meters (175m for Bad Nauheim)
   - **Step 2 - Wetter**: Select single weather sensors
     - Temperatur: One sensor with current temperature
     - Luftfeuchtigkeit: One sensor with current humidity (optional)
     - Solarstrahlung, Wind, Regen: Optional
   - **Step 3 - Hardware**: 
     - Transformator: Select your trafo switch
     - Frost-Schwelle: Default 4.0°C
   - **Step 4 - Zonen**: Add 1+ irrigation zones
     - Zone name, type (Wiese/Gemüse/Rasen), soil type, etc.

### Step 4: Get Token for Auto-Reload (Optional)

For hands-free deployment, get a long-lived token:

1. Home Assistant → Click your profile (bottom left)
2. Scroll to **"Long-Lived Access Tokens"**
3. Click **"Create Token"**
4. Name: `"SMB Deploy"`
5. Copy the token

Set in terminal:
```bash
export HA_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
export HA_URL="http://192.168.178.92:8123"
```

---

## Development Workflow

### Make Changes Locally

```bash
# Edit custom_components/irrigation_et0/ (any file)
vim custom_components/irrigation_et0/coordinator.py
```

### Deploy to HA (No Restart!)

```bash
# Quick deploy
bash deploy-smb.sh

# Integration reloads automatically if HA_TOKEN is set
# Otherwise, manual reload below
```

### Manual Reload (if HA_TOKEN not set)

```bash
export HA_TOKEN="<your-token>"
bash reload-integration.sh
```

### Verify in HA

1. **Settings → Devices & Services → Irrigation ET₀**
2. Check devices and entities show up
3. **⚙️ → Reload** if needed (but shouldn't be!)

### Add Lovelace Cards to Dashboard

After first HA restart, custom cards auto-register. Add to dashboard:

1. Dashboard → Edit (✏️)
2. Add card with YAML:
```yaml
type: custom:irrigation-et0-overview-card
title: Bewässerungs-Übersicht
entity: sensor.irrigation_et0_nfk_zone_1
```

Available cards:
- `irrigation-et0-overview-card` — Zone status grid
- `irrigation-et0-history-card` — NFK water balance history
- `irrigation-et0-settings-card` — Zone parameters (sliders)
- `irrigation-et0-ansaat-card` — Seed watering config

---

## Typical Development Cycle

```bash
# 1. Make code changes
vim custom_components/irrigation_et0/coordinator.py

# 2. Deploy
bash deploy-smb.sh

# 3. Check in HA UI
# (Integration auto-reloads if token is set)

# 4. Test your changes

# 5. Iterate...
```

**Total time per cycle: ~10 seconds ⚡**

---

## Troubleshooting

### Integration Not Appearing in "Create Integration"

**First Setup:**
- ✅ Run `bash deploy-smb.sh`
- ✅ Go to Home Assistant: **Settings → Devices & Services → Create Integration**
- ✅ Search for **"Irrigation ET₀"**
- ✅ If still not visible, restart HA once (then never again needed)

**After Changes:**
- ✅ Run `bash deploy-smb.sh` (copies files to SMB)
- ✅ Integration auto-reloads (if HA_TOKEN set)
- ✅ No restart needed for future deployments

### SMB Mount Lost

```bash
# Remount
umount /private/tmp/ha_mount
mount_smbfs //Michael@192.168.178.92/config /private/tmp/ha_mount

# Verify
ls /private/tmp/ha_mount/custom_components/
```

### HA Doesn't Reload Integration

If `bash reload-integration.sh` fails:

1. Check HA_TOKEN is valid
2. Manual reload: **Settings → Devices & Services → Irrigation ET₀ → ⚙️ → Reload**
3. Only if nothing works: Full HA restart (but this should be rare!)

---

## File Locations

| Item | Location |
|------|----------|
| **Source code** | `/Users/michael/irrigation-ha/custom_components/irrigation_et0/` |
| **HA instance** | `/private/tmp/ha_mount/custom_components/irrigation_et0/` |
| **Deploy script** | `/Users/michael/irrigation-ha/deploy-smb.sh` |
| **Reload script** | `/Users/michael/irrigation-ha/reload-integration.sh` |
| **HA UI** | http://192.168.178.92:8123 |

---

## Key Principles

✅ **SMB-only deployment** — no cloud tools, no token waste  
✅ **Hot-reload safe** — no HA restart after code changes  
✅ **Token-efficient** — ~100 tokens per deploy (vs 6,000 for cloud)  
✅ **Fast iteration** — <10 seconds per cycle  

---

**Ready to start? Run:**
```bash
bash deploy-smb.sh
```
