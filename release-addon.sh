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

# Tampon de version dans les README de l'addon (marqueurs <!-- version:auto -->,
# non destructif : seul le bloc marqué change ; inséré après le 1er titre si absent)
stamp_addon_version(){ # $1 = dossier depot addon ; $2 = version
  python3 - "$1" "$2" <<'PYEOF'
import os, re, sys
repo, ver = sys.argv[1], sys.argv[2]
block = "<!-- version:auto -->\n**Version : %s**\n<!-- /version:auto -->" % ver
for name in sorted(os.listdir(repo)):
    if name.lower() not in ("readme.md", "readme.en.md"):
        continue
    p = os.path.join(repo, name); s = open(p, encoding="utf-8").read()
    if "<!-- version:auto -->" in s:
        s2 = re.sub(r"<!-- version:auto -->.*?<!-- /version:auto -->", block, s, flags=re.S)
    else:
        out, done = [], False
        for ln in s.split("\n"):
            out.append(ln)
            if not done and ln.startswith("# "):
                out += ["", block]; done = True
        s2 = "\n".join(out)
    if s2 != s:
        open(p, "w", encoding="utf-8").write(s2); print("  README tamponné :", name)
PYEOF
}

# Bloc "versions actuelles" dans le README de kodi-repo (généré depuis addons.xml,
# entre marqueurs <!-- versions:auto --> ; les tableaux écrits à la main restent intacts)
stamp_repo_versions(){ # $1 = dossier kodi-repo
  python3 - "$1" <<'PYEOF'
import os, re, sys, xml.dom.minidom as m
repo = sys.argv[1]; ax = os.path.join(repo, "zips", "addons.xml")
rows = []
if os.path.isfile(ax):
    for a in m.parse(ax).getElementsByTagName("addon"):
        i, v = a.getAttribute("id"), a.getAttribute("version")
        if i and i != "repository.theworms": rows.append((i, v))
rows.sort()
tbl = ["<!-- versions:auto -->", "**Versions actuelles** *(généré)* :", "",
       "| id | version |", "|----|---------|"]
tbl += ["| `%s` | %s |" % (i, v) for i, v in rows] + ["<!-- /versions:auto -->"]
block = "\n".join(tbl)
for name in sorted(os.listdir(repo)):
    if name.lower() not in ("readme.md", "readme.en.md"):
        continue
    p = os.path.join(repo, name); s = open(p, encoding="utf-8").read()
    if "<!-- versions:auto -->" in s:
        s2 = re.sub(r"<!-- versions:auto -->.*?<!-- /versions:auto -->", block, s, flags=re.S)
    else:
        out, inserted, intable = [], False, False
        for ln in s.split("\n"):
            out.append(ln)
            if ln.strip().startswith("|"): intable = True
            elif intable and ln.strip() == "" and not inserted:
                out += [block, ""]; inserted = True; intable = False
        if not inserted: out += ["", block]
        s2 = "\n".join(out)
    if s2 != s:
        open(p, "w", encoding="utf-8").write(s2); print("  kodi-repo README tamponné :", name)
PYEOF
}

# push origin (canonique, rebase si distant en avance) puis forgejo (miroir, force-with-lease si besoin)
push_both(){ # $1 = remote-forgejo-url ; $2 = branche
  local furl="$1" br="$2"
  # --- origin (GitHub) : source de vérité, on rebase si le distant a de l'avance ---
  if ! git push origin "$br"; then
    c_warn "origin/$br rejeté (distant en avance) — rebase automatique…"
    if git pull --rebase origin "$br"; then
      git push origin "$br" || die "push origin échoué même après rebase"
    else
      git rebase --abort 2>/dev/null || true
      die "rebase origin impossible (conflits) — résous à la main puis relance le script"
    fi
  fi
  c_ok "push origin/$br"
  # --- forgejo (miroir) : force-with-lease en cas de divergence ---
  git remote get-url forgejo >/dev/null 2>&1 || git remote add forgejo "$furl"
  if git push forgejo "$br"; then
    c_ok "push forgejo/$br"
  elif git push forgejo "$br" --force-with-lease; then
    c_ok "push forgejo/$br (force-with-lease)"
  else
    c_warn "push forgejo échoué — vérifie le dépôt Forgejo et les droits"
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
# garde-fou : ne rien faire si un rebase/merge est en cours ou si HEAD est détaché
GITDIR="$(git rev-parse --git-dir)"
if [[ -d "$GITDIR/rebase-merge" || -d "$GITDIR/rebase-apply" || -f "$GITDIR/MERGE_HEAD" ]]; then
  die "rebase/merge en cours dans $ADDON_REPO — termine-le (git rebase --continue|--abort) puis relance"
fi
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" != "HEAD" ]] || die "HEAD détaché dans $ADDON_REPO — repositionne-toi sur une branche (ex. git switch main) puis relance"
stamp_addon_version "$ADDON_REPO" "$VERSION"
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
stamp_repo_versions "$KODI_REPO"

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
