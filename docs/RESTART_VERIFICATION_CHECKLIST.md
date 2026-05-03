# SmartGardn ET₀ - Post-Restart Verification Checklist

After restarting Home Assistant, use this checklist to verify SmartGardn ET₀ is working correctly.

## 1. Integration Load Status
**In HA Live Web UI:**
1. Go to: **Settings → Devices & Services → Integrations**
2. Search for "SmartGardn" or "Presley"
3. ✅ SmartGardn ET₀ should appear with status **"Connected"** (green)
4. ❌ If it shows **"Benötigt Aufmerksamkeit"** (red), click it to see error details

**If integration doesn't load:**
- Check logs: Settings → System → Logs → search for "smartgardn"
- Look for import errors, missing dependencies, or syntax errors
- Screenshot the error and send it for debugging

## 2. Cards in Lovelace UI
**In HA Live Lovelace dashboard:**
1. Go to your dashboard where SmartGardn cards should appear
2. Check for all 4 cards:
   - ✅ **Overview Card** (Shows ET₀ value, status, last watering)
   - ✅ **History Card** (Shows ET₀ trend over time)
   - ✅ **Settings Card** (Zone configuration UI)
   - ✅ **Ansaat Card** (Planting schedule)
3. Cards should load without errors
4. Cards should be interactive (buttons, toggles work)

**If cards don't load:**
- Open browser console (F12 → Console)
- Look for JavaScript errors like "404" or "failed to load"
- Check network tab (F12 → Network) for static path requests
- Screenshot errors and send for debugging

## 3. Card File Updates (No Restart Test)
**After verifying cards load:**
1. Edit any card file: `custom_components/smartgardn_et0/www/overview-card.js`
2. Make a small visual change (e.g., change a color or text)
3. Copy updated file to HA Live via SMB
4. Go to HA Lovelace dashboard
5. Press **F5** to refresh browser
6. ✅ New card version should load immediately
7. ✅ **No HA restart should be needed**

**If cards don't update without restart:**
- This indicates the static path optimization isn't working
- You would need to trigger a config reload (Settings → Devices & Services → SmartGardn → ⋮ → Reload)
- Or if that fails, do another restart

## 4. Integration Services
**Test zone control services:**
1. Go to: **Developer Tools → Services**
2. Call service: `smartgardn_et0.start_zone`
   ```yaml
   zone: switch.drs8_schaltaktor_garten_bewasserung_mv1_vch23
   dauer_min: 5
   ```
3. ✅ Zone valve should turn on for 5 minutes
4. Service `smartgardn_et0.stop_zone` should stop the zone
5. Service `smartgardn_et0.stop_all` should stop all zones

**If services fail:**
- Check HA logs for errors
- Verify switch entity IDs are correct

## 5. Daily Recalculation
**Test automatic ET₀ calculation:**
1. Check sensor: `sensor.presley_bewasserung_et0_wert`
2. Value should update daily at configured time
3. ✅ Should show current ET₀ value (mm/day)
4. Check zone automation rules are triggering correctly

## What To Do If Something Fails

### Integration won't load (red "Benötigt Aufmerksamkeit")
1. Check HA logs for specific error message
2. Look for Python syntax errors or import failures
3. Send error details and logs for investigation

### Cards show 404 or "failed to load"
1. Verify static path is registered: Check HA logs for `"✓ Registered static path"`
2. Test URL directly: `http://192.168.178.92:8123/smartgardn_et0_cards/overview-card.js`
3. Check manifest.json has correct resource URLs

### Cards update requires restart still
1. Trigger config reload instead: Settings → Devices & Services → SmartGardn → ⋮ → Reload
2. If reload doesn't work, check logs for "skip_static=True" behavior

---

## Expected Timeline

- **Restart**: ~30-60 seconds
- **Integration load**: Automatic after startup
- **Cards render**: Automatic when dashboard loads
- **Total downtime**: ~1-2 minutes

---

## Quick Reference: SMB Mount (if needed for debugging)
```bash
source /Users/michael/Documents/Coding/.secrets.env
mount -t smbfs "//${SMB_USERNAME}:${SMB_PASSWORD}@${SMB_HOST}/${SMB_SHARE}" ${SMB_MOUNT_POINT}
# Mount point: /private/tmp/ha_mount
# Check logs: /private/tmp/ha_mount/home-assistant.log.1
```

---

**Status**: Ready for restart. All code validated. No syntax errors detected.
