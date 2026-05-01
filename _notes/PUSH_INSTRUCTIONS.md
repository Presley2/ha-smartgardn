# SmartGardn v0.2.0 — Push Instructions

## Status
- ✅ All fixes implemented
- ✅ 150/150 tests passing
- ✅ 2 commits ready to push
- ✅ Version bumped to 0.2.0

## Git Status
```bash
$ git log --oneline -2
dced383 chore: bump version to 0.2.0 and update CHANGELOG
2f4ed60 fix: address 5 critical security & logic issues + 2 calculation bugs
```

## Current Problem
The remote `https://github.com/Presley2/ha-smartgardn.git` is not accessible from this user account (permission denied).

## Solution Options

### Option A: Create Your Own Fork (Recommended)
```bash
# 1. Fork the repo on GitHub
#    Go to https://github.com/Presley2/ha-smartgardn
#    Click "Fork" button

# 2. Add your fork as remote
cd /Users/michael/smartgrdn
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/ha-smartgardn.git
git branch -u origin/master master

# 3. Push your changes
git push origin master
```

### Option B: Push to a Different Remote
```bash
# If you have another GitHub account with write access
git remote add backup https://github.com/ANOTHER_USERNAME/ha-smartgardn.git
git push backup master
```

### Option C: Create a Pull Request from Your Fork
```bash
# After forking and pushing to your fork:
# Go to https://github.com/YOUR_USERNAME/ha-smartgardn
# Click "Pull Request" button
# Select Presley2/ha-smartgardn as the base
```

### Option D: Request Collaborator Access
Contact the repo owner (@Presley2 or @michaelrichter) to add you as a collaborator to the original repo.

---

## What Will Be Pushed

### 2 Commits:
1. **2f4ed60** - Fix: address 5 critical security & logic issues + 2 calculation bugs
   - Frost-lock fix
   - Safe dict access
   - Base64 entity encoding
   - C&S event scheduling
   - Startup recovery race condition
   - Recorder timeout
   - Input validation

2. **dced383** - Chore: bump version to 0.2.0 and update CHANGELOG

### Files Modified:
```
AUDIT_REPORT.md                                    (NEW - 290 lines)
CALCULATION_VERIFICATION_REPORT.md                 (NEW - 394 lines)
CHANGELOG.md                                       (+19 lines)
custom_components/smartgardn_et0/__init__.py       (+1 line)
custom_components/smartgardn_et0/config_flow.py    (+100 lines)
custom_components/smartgardn_et0/coordinator.py    (+60 lines)
custom_components/smartgardn_et0/et0_calculator.py (+5 lines)
custom_components/smartgardn_et0/manifest.json     (+22 lines)
custom_components/smartgardn_et0/repairs.py        (+25 lines)
tests/test_coordinator_logic.py                    (+20 lines)
tests/test_repairs.py                              (+26 lines)
```

Total: **964 lines added, 77 lines removed**

---

## Verification Before Push

```bash
# 1. Verify all tests pass
cd /Users/michael/smartgrdn
.venv/bin/python -m pytest tests/ -v

# Expected output:
# ============================= 150 passed in 1.09s ==============================

# 2. View commits to be pushed
git log origin/master..master --oneline

# 3. View detailed diff
git diff origin/master master --stat
```

---

## Push Commands (Choose One)

### If using your own fork:
```bash
git push origin master
```

### If using a different remote:
```bash
git push backup master
```

### Force push (only if needed):
```bash
git push --force-with-lease origin master
```

---

## After Push

1. **Verify on GitHub**
   - Go to your repo
   - Check that commits appear
   - Verify version 0.2.0 in manifest.json

2. **Create Release**
   - Go to https://github.com/YOUR_USERNAME/ha-smartgardn/releases
   - Click "Draft a new release"
   - Tag: v0.2.0
   - Title: SmartGardn ET₀ v0.2.0
   - Description: Copy from RELEASE_0.2.0_SUMMARY.md

3. **Submit PR (if forked)**
   - Go to https://github.com/Presley2/ha-smartgardn/pulls
   - Click "New pull request"
   - Select your fork as compare branch
   - Add description from RELEASE_0.2.0_SUMMARY.md

---

## Troubleshooting

### "fatal: unable to access ... Permission denied"
Your GitHub token doesn't have access. Solutions:
1. Use SSH instead of HTTPS: `git config --global url."git@github.com:".insteadOf "https://github.com/"`
2. Create a Personal Access Token and use it instead of password
3. Fork the repo to your own account

### "branch 'master' set up to track 'origin/master' which no longer exists"
Reset the upstream:
```bash
git branch --unset-upstream
git branch -u origin/master master
```

---

## Files in Repo Root
- `smartgrdn/` — main project directory
- `AUDIT_REPORT.md` — comprehensive code audit
- `CALCULATION_VERIFICATION_REPORT.md` — math verification
- `RELEASE_0.2.0_SUMMARY.md` — release notes

---

**Ready to push!** 🚀

