#!/usr/bin/env bash
#
# release-addon.sh — publication d'un addon Kodi TheWorms de bout en bout :
#   1) commit + push de l'addon        (origin = GitHub, puis forgejo = miroir)
#   2) régénération du dépôt kodi-repo  (zip + addons.xml + md5)
#   3) commit + push de kodi-repo       (origin puis forgejo)
#   4) release GitHub (tag vX.Y.Z) avec le zip généré en pièce jointe
#
# Usage :
#   ./release-addon.sh <chemin-depot-addon> ["message de commit"] ["notes de release"]
#
# Exemples :
#   ./release-addon.sh /run/media/theworms/Data/Git/kodi-addon-emby
#   ./release-addon.sh ~/Data/Git/kodi-addon-protonvpn "Correctif widget" "Notes ici"
#
set -uo pipefail

# ------------------------------------------------------------------ Config ---
KODI_REPO="${KODI_REPO:-/run/media/theworms/Data/Git/kodi-repo}"
FORGEJO_BASE="${FORGEJO_BASE:-http://192.168.0.230:3000/theworms}"
GH_OWNER="${GH_OWNER:-TheWorms}"

# ------------------------------------------------------------------- Utils ---
c_ok(){ printf '\033[32m✓\033[0m %s\n' "$*"; }
c_info(){ printf '\033[36m•\033[0m %s\n' "$*"; }
c_warn(){ printf '\033[33m!\033[0m %s\n' "$*"; }
die(){ printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

xmlget(){ python3 -c "import xml.dom.minidom as m,sys; print(m.parse(sys.argv[1]).getElementsByTagName('addon')[0].getAttribute(sys.argv[2]))" "$1" "$2"; }

# push origin puis forgejo ; forgejo non bloquant (on prévient si rejet)
push_both(){ # $1 = remote-forgejo-url ; $2 = branche
  local furl="$1" br="$2"
  git push origin "$br" || die "push origin échoué (branche $br)"
  c_ok "push origin/$br"
  git remote get-url forgejo >/dev/null 2>&1 || git remote add forgejo "$furl"
  if git push forgejo "$br"; then
    c_ok "push forgejo/$br"
  else
    c_warn "push forgejo rejeté — réessaie manuellement :"
    c_warn "    (cd $(pwd) && git push forgejo $br --force-with-lease)"
  fi
}

# --------------------------------------------------------------------- Args ---
ADDON_REPO="${1:-}"; [[ -n "$ADDON_REPO" ]] || die "Usage: release-addon.sh <chemin-depot-addon> [msg] [notes]"
COMMIT_MSG="${2:-}"
RELEASE_NOTES="${3:-}"
[[ -d "$ADDON_REPO" ]] || die "Dépôt introuvable : $ADDON_REPO"
ADDON_REPO="$(cd "$ADDON_REPO" && pwd)"
REPO_NAME="$(basename "$ADDON_REPO")"
[[ -d "$KODI_REPO" ]] || die "kodi-repo introuvable : $KODI_REPO (variable KODI_REPO ?)"

# -------------------------------------------- addon.xml : racine ou sous-dossier ---
if [[ -f "$ADDON_REPO/addon.xml" ]]; then
  ADDON_DIR="$ADDON_REPO"
else
  ADDON_XML="$(find "$ADDON_REPO" -maxdepth 2 -name addon.xml -not -path '*/.git/*' 2>/dev/null | head -n1)"
  [[ -n "$ADDON_XML" ]] || die "addon.xml introuvable dans $ADDON_REPO"
  ADDON_DIR="$(dirname "$ADDON_XML")"
fi
ADDON_ID="$(xmlget "$ADDON_DIR/addon.xml" id)"
VERSION="$(xmlget "$ADDON_DIR/addon.xml" version)"
TAG="v$VERSION"
[[ -n "$COMMIT_MSG" ]]   && MSG="$COMMIT_MSG"   || MSG="$ADDON_ID $VERSION"
[[ -n "$RELEASE_NOTES" ]] && NOTES="$RELEASE_NOTES" || NOTES="Release $VERSION de $ADDON_ID."

printf '\n\033[1m== %s  →  %s %s ==\033[0m\n' "$REPO_NAME" "$ADDON_ID" "$VERSION"
c_info "addon.xml : $ADDON_DIR/addon.xml"

# ------------------------------------------------ 1) Addon : commit + push ---
cd "$ADDON_REPO"
git rev-parse --git-dir >/dev/null 2>&1 || die "$ADDON_REPO n'est pas un dépôt git"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git add -A
if git diff --cached --quiet; then
  c_info "addon : rien à committer"
else
  git commit -q -m "$MSG"; c_ok "commit addon : $MSG"
fi
push_both "$FORGEJO_BASE/$REPO_NAME.git" "$BRANCH"

# ------------------------------------------ 2) kodi-repo : régénération ---
cd "$KODI_REPO"
python3 - "$ADDON_DIR" <<'PYEOF'
import re, sys
src = sys.argv[1]
p = "_repo_generator.py"; s = open(p).read()
if src in s:
    print("  ADDON_SOURCES : déjà présent")
else:
    s = re.sub(r'(ADDON_SOURCES = \[.*?)(\n\])',
               lambda m: m.group(1) + '\n    "%s",' % src + m.group(2), s, flags=re.S)
    open(p, "w").write(s); print("  ADDON_SOURCES : ajouté " + src)
PYEOF
python3 _repo_generator.py >/dev/null || die "génération kodi-repo échouée"
c_ok "kodi-repo régénéré"

RBRANCH="$(git rev-parse --abbrev-ref HEAD)"
git add -A
if git diff --cached --quiet; then
  c_info "kodi-repo : inchangé (pas de push)"
else
  git commit -q -m "$ADDON_ID $VERSION"; c_ok "commit kodi-repo"
  push_both "$FORGEJO_BASE/kodi-repo.git" "$RBRANCH"
fi

# ------------------------------------------------ 3) Release GitHub ---
ZIP="$KODI_REPO/zips/$ADDON_ID/$ADDON_ID-$VERSION.zip"
cd "$ADDON_REPO"
if ! command -v gh >/dev/null 2>&1; then
  c_warn "gh (GitHub CLI) absent — release non créée. Tag visé : $TAG"
elif gh release view "$TAG" --repo "$GH_OWNER/$REPO_NAME" >/dev/null 2>&1; then
  c_warn "release $TAG existe déjà — ignorée"
else
  args=(release create "$TAG" --repo "$GH_OWNER/$REPO_NAME" --title "$ADDON_ID $VERSION" --notes "$NOTES")
  [[ -f "$ZIP" ]] && args+=("$ZIP")
  if gh "${args[@]}"; then c_ok "release $TAG créée"; else c_warn "création release échouée"; fi
fi

printf '\033[1;32m== Terminé : %s %s ==\033[0m\n' "$ADDON_ID" "$VERSION"
