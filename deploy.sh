#!/usr/bin/env bash
#
# ErstiLink veröffentlichen
# -------------------------
# Baut die Seite, prüft sie und schiebt die Änderungen zu GitHub.
# Netlify baut danach automatisch und veröffentlicht innerhalb einer Minute.
#
#   ./deploy.sh                     Standardnachricht
#   ./deploy.sh "Gruppen für TU"    eigene Nachricht
#
set -euo pipefail
cd "$(dirname "$0")"

NACHRICHT="${1:-Inhalte aktualisiert}"

echo "→ Website bauen"
python3 build.py

echo
echo "→ Auslieferung prüfen"
python3 build.py pruefen

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo
  echo "Kein Git-Repository. Einmalig einrichten:"
  echo "  git init && git branch -M main"
  echo "  git remote add origin https://github.com/DEINNAME/erstilink.git"
  exit 1
fi

echo
echo "→ Änderungen übertragen"
git add -A

if git diff --cached --quiet; then
  echo "Nichts geändert – nichts zu tun."
  exit 0
fi

git commit -m "$NACHRICHT"
git push

echo
echo "Fertig. Netlify baut jetzt automatisch."
echo "Status: https://app.netlify.com  ·  Live in ca. 60 Sekunden auf https://erstilink.de"
