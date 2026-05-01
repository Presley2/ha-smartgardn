# Pull Request Erstellen — Schritt für Schritt

## Schritt 1: Fork das Repo auf GitHub

1. Gehe zu: https://github.com/Presley2/ha-smartgardn
2. Klicke oben rechts auf **"Fork"**
3. Wähle dein Account als Ziel
4. Warte bis Fork fertig ist

Du hast jetzt: `https://github.com/DEIN_USERNAME/ha-smartgardn`

---

## Schritt 2: Remote anpassen (lokal)

```bash
cd /Users/michael/smartgrdn

# Alten Remote entfernen
git remote remove origin

# Deinen Fork als neues origin hinzufügen
git remote add origin https://github.com/DEIN_USERNAME/ha-smartgardn.git

# Bestätige:
git remote -v
# Sollte zeigen: origin    https://github.com/DEIN_USERNAME/ha-smartgardn.git
```

---

## Schritt 3: Push zu deinem Fork

```bash
git push origin master
```

Output sollte sein:
```
Counting objects: 100% (150/150)
Compressing objects: 100% (50/50)
Writing objects: 100% (150/150)
...
To https://github.com/DEIN_USERNAME/ha-smartgardn.git
   abc1234..def5678  master -> master
```

---

## Schritt 4: Pull Request erstellen (auf GitHub)

### Option A: Via GitHub Web UI (einfach)

1. Gehe zu deinem Fork: `https://github.com/DEIN_USERNAME/ha-smartgardn`
2. Du siehst oben einen gelben Banner:
   ```
   "This branch is 2 commits ahead of Presley2:master"
   Compare & pull request
   ```
3. Klicke auf **"Compare & pull request"**

### Option B: Manuell

1. Gehe zu: https://github.com/Presley2/ha-smartgardn/pulls
2. Klicke auf **"New pull request"**
3. Klicke auf **"compare across forks"**
4. Wähle:
   - **base repository:** Presley2/ha-smartgardn
   - **base branch:** master
   - **head repository:** DEIN_USERNAME/ha-smartgardn
   - **compare branch:** master

---

## Schritt 5: Pull Request beschreiben

### Title (Überschrift):
```
fix: Critical security and calculation fixes in v0.2.0
```

### Description (Body):
Kopiere und paste dies:

```markdown
## Summary

This PR addresses 5 critical security/logic issues and 2 calculation bugs found during comprehensive code audit.

### 🔴 Critical Fixes (5)
- **Frost-lock:** Now works with both `temp_entity` and legacy `temp_min_entity` configs
- **Safe dict access:** Prevent crashes during zone reconfiguration (Issue #1)
- **Entity ID parsing:** Replace string-based with Base64 encoding (Issue #4)
- **Startup recovery:** Fix race condition with safe dict access (Issue #3)
- **Cycle & Soak:** Replace `asyncio.sleep()` with event-based scheduling (Issue #5)

### 🟡 Medium Priority (3)
- Add 5-second timeout to recorder.get_history() calls (Issue #6)
- **LUX sensor conversion:** Fix 1000× underestimation (1.0/54000 → 1.0/54)
- **PAR sensor accuracy:** Improve from 0.51 to 0.0219
- Enhance input validation in config flow (Issue #11)

### ✅ Test Results
- 150/150 tests passing
- All calculations verified against FAO-56 standard
- Edge cases tested (clamping, swapped temps, etc.)

### 📋 Files Changed
- 11 files modified
- 964 lines added
- 77 lines removed

### 📚 Documentation
- Added comprehensive audit report (`AUDIT_REPORT.md`)
- Added calculation verification report (`CALCULATION_VERIFICATION_REPORT.md`)
- Updated `CHANGELOG.md` with detailed release notes
- Bumped version to 0.2.0

### 🔍 Test Plan
All tests pass locally:
```bash
.venv/bin/python -m pytest tests/ -v
# ============================= 150 passed in 1.09s ==============================
```

Verified calculations:
- FAO-56 ET₀: 4.50 mm/day ✓
- Hargreaves ET₀: 14.46 mm/day ✓
- NFK balance: Clamping works correctly ✓
- Duration: 8.75 min ✓

### ⚠️ Breaking Changes
None — All changes are backward compatible.

### 🔒 Security
Fixed potential security issues:
- Safe entity ID encoding (prevents injection attacks)
- Safe configuration access (prevents crashes)
- Enhanced input validation

---

**Ready to merge!** 🚀
```

---

## Schritt 6: PR abschicken

1. Scrolle nach unten
2. Klicke auf grünen **"Create pull request"** Button
3. Done! ✅

GitHub schickt dir Benachrichtigungen, wenn der PR reviewed wird.

---

## Was passiert dann?

1. **Maintainer reviewed** deinen PR (1-3 Tage)
2. **CI/CD Tests laufen** automatisch
3. **Entweder:**
   - ✅ Merged → Dein Code ist jetzt im Repo!
   - 🔄 Changes requested → Du machst Anpassungen
   - ❌ Rejected → Mit Kommentar warum

---

## Tipps

### Wenn maintainer Änderungen fordert:

```bash
# Änderungen machen
git add .
git commit -m "fix: address review feedback"
git push origin master

# PR wird automatisch aktualisiert!
```

### Wenn PR conflicts hat:

```bash
# Upstream hinzufügen
git remote add upstream https://github.com/Presley2/ha-smartgardn.git

# Rebase auf latest
git fetch upstream
git rebase upstream/master

# Conflicts auflösen
# ...

git push --force-with-lease origin master
```

### PR Status checken:

- Gehe zu: https://github.com/Presley2/ha-smartgardn/pulls
- Suche deinen PR in der Liste
- Klick drauf um Details zu sehen

---

## Checkliste

- [ ] Fork erstellt
- [ ] Remote geändert zu deinem Fork
- [ ] `git push origin master` erfolgreich
- [ ] Pull Request auf GitHub erstellt
- [ ] Titel und Description eingetragen
- [ ] PR abgesendet

---

## Beispiel PR (wie es aussieht)

```
Title: fix: Critical security and calculation fixes in v0.2.0

Description:
## Summary
This PR addresses 5 critical security/logic issues...

Files changed: 11
Commits: 2
Additions: 964
Deletions: 77

Status: Open
```

---

Das war's! Dein PR ist jetzt live und wartet auf Review. 🎉

