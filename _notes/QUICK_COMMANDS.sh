#!/bin/bash
# SmartGardn v0.2.0 — Quick Commands für Push + Pull Request

echo "============================================"
echo "SmartGardn v0.2.0 — Push & PR Quick Guide"
echo "============================================"
echo ""

# Schritt 1: Remote anpassen
echo "SCHRITT 1: Remote anpassen"
echo "=========================="
echo "Ersetze DEIN_USERNAME mit deinem GitHub username!"
echo ""
echo "$ cd /Users/michael/smartgrdn"
echo "$ git remote remove origin"
echo "$ git remote add origin https://github.com/DEIN_USERNAME/ha-smartgardn.git"
echo ""
echo "Bestätigung:"
echo "$ git remote -v"
echo ""

# Schritt 2: Push
echo "SCHRITT 2: Push zu deinem Fork"
echo "==============================="
echo "$ git push origin master"
echo ""
echo "Erwartet:"
echo "  To https://github.com/DEIN_USERNAME/ha-smartgardn.git"
echo "     ...::master -> master"
echo ""

# Schritt 3: PR erstellen
echo "SCHRITT 3: Pull Request erstellen"
echo "=================================="
echo "1. Gehe zu: https://github.com/DEIN_USERNAME/ha-smartgardn"
echo "2. Klick auf 'Compare & pull request' Button (gelber Banner oben)"
echo "3. Title eingeben:"
echo "   'fix: Critical security and calculation fixes in v0.2.0'"
echo "4. Description kopieren von /Users/michael/PULL_REQUEST_GUIDE.md"
echo "5. Klick 'Create pull request'"
echo ""

echo "============================================"
echo "FERTIG! 🚀"
echo "============================================"
echo ""
echo "Dein PR ist jetzt live unter:"
echo "  https://github.com/Presley2/ha-smartgardn/pulls"
echo ""

