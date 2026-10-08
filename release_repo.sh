#!/usr/bin/env bash
set -euo pipefail

ADDON_XML="repository.theworms/addon.xml"

# --- Version actuelle + numéro de ligne de l'attribut, via Python (insensible au formatage) ---
read -r OLD LINE <<< "$(python3 - "$ADDON_XML" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'<addon\b[^>]*\bversion="([0-9][0-9.]*)"', text)
if not m:
    sys.exit(1)
line = text[:m.start(1)].count("\n") + 1
print(m.group(1), line)
PY
)" || { echo "!! version introuvable dans $ADDON_XML"; exit 1; }

if [ -n "${1:-}" ]; then
    NEW="$1"
else
    NEW=$(echo "$OLD" | awk -F. '{print $1"."$2"."$3+1}')
fi
echo "repository.theworms : $OLD -> $NEW (ligne $LINE)"

# --- Bump ciblé sur la ligne trouvée ---
sed -i "${LINE}s/version=\"$OLD\"/version=\"$NEW\"/" "$ADDON_XML"

# --- Garde-fou : XML valide et version bien appliquée ---
python3 - "$ADDON_XML" "$NEW" <<'PY' || { echo "!! XML invalide après bump — restauration"; git checkout -- "$ADDON_XML"; exit 1; }
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
assert root.tag == "addon" and root.get("version") == sys.argv[2], "version non appliquée"
PY

# --- Régénération + validation ---
python3 _repo_generator.py
python3 tools/validate_repo.py

# --- Commit + push (GitHub et Forgejo) ---
git checkout main
git add -A
git commit -m "repository.theworms $NEW"
env -u GITHUB_TOKEN git push origin main
git push forgejo main 2>/dev/null || echo "(remote forgejo absent — ignoré)"

echo
echo "✅ repository.theworms v$NEW publié. Kodi proposera la mise à jour automatiquement."
