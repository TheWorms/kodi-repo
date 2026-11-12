#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de repository Kodi.

Zippe chaque addon dans  zips/<id>/<id>-<version>.zip, copie son icône/fanart
à côté du zip, et régénère  zips/addons.xml + zips/addons.xml.md5.

Paquets Python embarqués : si un addon contient un fichier vendor.txt (une
dépendance pip par ligne), ces paquets sont installés à neuf dans un dossier
temporaire et ajoutés au zip sous resources/lib/vendor/ — le dossier vendor/
local (hors git) n'est jamais repris tel quel.

Contenu des zips : quand la source est un dépôt git, seuls les fichiers
suivis par git sont zippés (un brouillon, un .patch ou une sauvegarde posés
dans le dossier ne partent plus dans le zip publié). Les dossiers de
développement (docs, tests, tools, scripts) à la racine de l'addon sont
toujours écartés.

Anciennes versions : seules les KEEP_VERSIONS dernières de chaque addon sont
gardées dans zips/<id>/.

Versions figées : un zip déjà publié (suivi par git dans ce dépôt et inchangé)
n'est jamais refait. Sans cela chaque génération réécrivait tous les zips, et
celui d'un addon à paquets embarqués (yt-dlp) changeait de contenu à chaque
sortie d'un autre addon. Pour publier un changement, monter la version.
KODI_REPO_REBUILD=all (ou une liste d'identifiants séparés par des virgules)
force la reconstruction.

Les avertissements (fichier non suivi laissé hors du zip, modifications non
commitées, version sans tag) sortent sur la sortie d'erreur.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import zlib

SOURCES_FILE = os.environ.get("KODI_REPO_SOURCES", "sources.json")
OUTPUT_DIR = "zips"

EXCLUDED_DIRS = (".git", ".github", ".claude", "__pycache__", ".idea", ".vscode")
EXCLUDED_FILES = {
    ".gitignore", ".gitmodules", ".gitattributes",
    "CLAUDE.md", "AGENTS.md", "CONTEXT.md",
    "README.md", "readme.md", "readme.en.md",
    "release.sh",
    "vendor.txt",
    "Pipfile", "Pipfile.lock", "requirements.txt",
    "pyrightconfig.json", "ruff.toml", "build.sh",
}
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".patch", ".orig", ".rej", ".bak", ".swp", "~")
# Dossiers de développement, écartés seulement à la racine de l'addon
EXCLUDED_ROOT_DIRS = ("docs", "tests", "tools", "scripts")
# Nombre de versions gardées par addon dans zips/<id>/
KEEP_VERSIONS = 3
# Écarter du zip le icon.png (logo du README) que l'addon ne cite plus.
# Mettre False si un favori ou un raccourci de skin pointe encore dessus.
DROP_UNUSED_ICON = True

# Addons dont le zip est refait même s'il est déjà publié ("all" = tous)
REBUILD = {x.strip() for x in os.environ.get("KODI_REPO_REBUILD", "").split(",") if x.strip()}

VENDOR_FILE = "vendor.txt"
VENDOR_DEST = os.path.join("resources", "lib", "vendor")


def load_sources():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, SOURCES_FILE)
    if not os.path.isfile(path):
        sys.exit(
            f"!! {path} introuvable — copie sources.json.example vers sources.json "
            "(ou définis KODI_REPO_SOURCES) puis adapte les chemins."
        )
    with open(path, encoding="utf-8") as f:
        sources = json.load(f)
    if not isinstance(sources, list) or not sources:
        sys.exit(f"!! {path} doit contenir une liste non vide de chemins.")
    return sources


def addon_meta(src):
    tree = ET.parse(os.path.join(src, "addon.xml"))
    root = tree.getroot()
    return root.get("id"), root.get("version"), root


def build_vendor(src):
    """Installe les paquets de vendor.txt dans un dossier temporaire (ou None)."""
    req = os.path.join(src, VENDOR_FILE)
    if not os.path.isfile(req):
        return None
    work = tempfile.mkdtemp(prefix="kodi-vendor-")
    target = os.path.join(work, "vendor")
    # venv jetable : pip refuse d'écrire avec le Python système (PEP 668, Arch)
    subprocess.run([sys.executable, "-m", "venv", os.path.join(work, "venv")], check=True)
    pip = os.path.join(work, "venv", "bin", "pip")
    subprocess.run([pip, "install", "--quiet", "--no-deps", "--target", target, "-r", req], check=True)
    for junk in ("bin", "share"):
        shutil.rmtree(os.path.join(target, junk), ignore_errors=True)
    out = subprocess.run([pip, "list", "--path", target, "--format", "freeze"],
                         capture_output=True, text=True).stdout.split()
    print("     vendor : " + ", ".join(out))
    # Versions embarquées, écrites dans le zip (resources/lib/vendor/VERSIONS.txt)
    with open(os.path.join(work, "VERSIONS.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return work


def warn(msg):
    """Avertissement visible même quand la sortie standard est masquée."""
    print("!! " + msg, file=sys.stderr)


def _git(args, cwd=None):
    """Sortie d'une commande git, ou None si elle échoue (pas un dépôt, git absent)."""
    try:
        proc = subprocess.run(["git"] + args, cwd=cwd, capture_output=True)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "surrogateescape")


def published_zip(addon_id, version):
    """Chemin du zip de cette version s'il est déjà publié : suivi par git dans
    ce dépôt et identique à ce qui est commité. Sinon None (zip à construire,
    ou construit par une génération précédente pas encore commitée)."""
    if "all" in REBUILD or addon_id in REBUILD:
        return None
    path = os.path.join(OUTPUT_DIR, addon_id, f"{addon_id}-{version}.zip")
    if not os.path.isfile(path):
        return None
    if _git(["ls-files", "--error-unmatch", "--", path]) is None:
        return None
    status = _git(["status", "--porcelain", "--", path])
    if status is None or status.strip():
        return None
    return path


def zip_addon_xml(zip_path, addon_id):
    """addon.xml contenu dans un zip publié (None s'il est illisible)."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            root = ET.fromstring(zf.read(f"{addon_id}/addon.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError):
        return None
    return root if root.get("id") == addon_id else None


def sources_differ(src, root, zip_path, addon_id):
    """Les sources ont-elles changé depuis le zip publié de la même version ?
    (comparaison par CRC, hors paquets embarqués)."""
    vendor_prefix = VENDOR_DEST + os.sep
    try:
        with zipfile.ZipFile(zip_path) as zf:
            published = {i.filename[len(addon_id) + 1:]: i.CRC for i in zf.infolist()
                         if not i.is_dir() and not i.filename[len(addon_id) + 1:].startswith(vendor_prefix)}
        local = {}
        for rel in addon_files(src, root, skip_local_vendor=True, quiet=True):
            with open(os.path.join(src, rel), "rb") as fh:
                local[rel] = zlib.crc32(fh.read()) & 0xFFFFFFFF
    except (OSError, zipfile.BadZipFile):
        return []
    return sorted(k for k in set(local) | set(published) if local.get(k) != published.get(k))


def check_new_version(src, addon_id, version):
    """Avertit quand une nouvelle version part d'un dépôt qui n'est pas prêt."""
    top = _git(["rev-parse", "--show-toplevel"], cwd=src)
    if top is None:
        return  # pas un dépôt git : rien à vérifier
    status = _git(["status", "--porcelain", "-z", "--", "."], cwd=src) or ""
    entries = [e for e in status.split("\0") if e]
    modified = [e[3:] for e in entries if not e.startswith("??")]
    if modified:
        warn(f"{addon_id} {version} : modifications non commitées incluses dans le zip "
             f"({', '.join(modified[:5])}{'…' if len(modified) > 5 else ''})")
    untracked = _git(["ls-files", "--others", "--exclude-standard", "-z", "--", "."], cwd=src) or ""
    left_out = [f for f in untracked.split("\0") if f and not _excluded(os.path.normpath(f))]
    if left_out:
        warn(f"{addon_id} {version} : fichier(s) non suivi(s) par git laissé(s) HORS du zip "
             f"({', '.join(left_out[:8])}{'…' if len(left_out) > 8 else ''}) — "
             "« git add » puis relancer si l'addon en a besoin")
    here = _git(["rev-parse", "--show-toplevel"])
    if here is not None and os.path.realpath(top.strip()) == os.path.realpath(here.strip()):
        return  # addon rangé dans ce dépôt (repository.theworms) : pas de tag par version
    tags = (_git(["tag", "--points-at", "HEAD"], cwd=src) or "").split()
    if f"v{version}" not in tags:
        warn(f"{addon_id} {version} : le dernier commit du dépôt source ne porte pas le tag "
             f"v{version} — cette version est publiée ici avant sa propre sortie")


def _excluded(rel):
    """Chemin (relatif à l'addon) écarté du zip par les règles d'exclusion."""
    parts = rel.split(os.sep)
    name = parts[-1]
    if any(p in EXCLUDED_DIRS for p in parts[:-1]):
        return True
    if len(parts) > 1 and parts[0] in EXCLUDED_ROOT_DIRS:
        return True
    return name in EXCLUDED_FILES or name.endswith(EXCLUDED_SUFFIXES)


def tracked_files(src):
    """Fichiers suivis par git sous src (chemins relatifs à src), ou None si
    src n'est pas dans un dépôt git."""
    try:
        out = subprocess.run(["git", "-C", src, "ls-files", "-z", "--", "."],
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    files = [f for f in out.decode("utf-8", "surrogateescape").split("\0") if f]
    return files or None


def walked_files(src):
    files = []
    for base, dirs, names in os.walk(src):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in names:
            files.append(os.path.relpath(os.path.join(base, f), src))
    return files


def unused_icon(src, root, files):
    """icon.png à la racine ou dans resources/ quand addon.xml déclare une
    autre icône et que plus aucun fichier de l'addon ne le cite : c'est le
    logo du README, inutile dans le zip. Retourne l'ensemble des chemins à
    écarter (vide dans le doute)."""
    meta = root.find("extension[@point='xbmc.addon.metadata']")
    assets = meta.find("assets") if meta is not None else None
    if assets is None:
        return set()
    declared = {os.path.normpath((el.text or "").strip()) for el in assets if (el.text or "").strip()}
    if not declared or any(os.path.basename(d) == "icon.png" for d in declared):
        return set()
    candidates = {f for f in files if f in ("icon.png", os.path.join("resources", "icon.png"))}
    if not candidates:
        return set()
    for rel in files:
        if not rel.endswith((".py", ".xml")):
            continue
        try:
            with open(os.path.join(src, rel), encoding="utf-8", errors="ignore") as fh:
                if "icon.png" in fh.read():
                    return set()
        except OSError:
            return set()
    return candidates


def addon_files(src, root, skip_local_vendor, quiet=False):
    """Chemins (relatifs à src) des fichiers à mettre dans le zip."""
    files = tracked_files(src)
    if files is None:
        if not quiet:
            print("     (pas un dépôt git : tout le dossier est parcouru)")
        files = walked_files(src)
    vendor_prefix = VENDOR_DEST + os.sep
    keep = []
    for rel in files:
        rel = os.path.normpath(rel)
        if _excluded(rel):
            continue
        if skip_local_vendor and rel.startswith(vendor_prefix):
            continue
        if not os.path.isfile(os.path.join(src, rel)):
            continue  # suivi par git mais supprimé du dossier de travail
        keep.append(rel)
    dropped = unused_icon(src, root, keep) if DROP_UNUSED_ICON else set()
    if not quiet:
        for rel in sorted(dropped):
            print(f"     {rel} écarté (logo du README, plus cité par l'addon)")
    return sorted(f for f in keep if f not in dropped)


def zip_addon(src, addon_id, version, root, vendor_dir=None):
    out_subdir = os.path.join(OUTPUT_DIR, addon_id)
    os.makedirs(out_subdir, exist_ok=True)
    zip_path = os.path.join(out_subdir, f"{addon_id}-{version}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in addon_files(src, root, skip_local_vendor=bool(vendor_dir)):
            zf.write(os.path.join(src, rel), os.path.join(addon_id, rel))
        if vendor_dir:
            vroot = os.path.join(vendor_dir, "vendor")
            for base, dirs, files in os.walk(vroot):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for f in files:
                    if f.endswith((".pyc", ".pyo")):
                        continue
                    full = os.path.join(base, f)
                    zf.write(full, os.path.join(addon_id, VENDOR_DEST, os.path.relpath(full, vroot)))
            versions = os.path.join(vendor_dir, "VERSIONS.txt")
            if os.path.isfile(versions):
                zf.write(versions, os.path.join(addon_id, VENDOR_DEST, "VERSIONS.txt"))

    print(f"  -> {zip_path}")
    return zip_path


def version_key(version):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+~]", version))


def prune_old_zips(addon_id, current):
    """Ne garde que les KEEP_VERSIONS dernières versions (la courante comprise)."""
    out_subdir = os.path.join(OUTPUT_DIR, addon_id)
    prefix = addon_id + "-"
    found = [f[len(prefix):-4] for f in os.listdir(out_subdir)
             if f.startswith(prefix) and f.endswith(".zip")]
    found.sort(key=version_key, reverse=True)
    keep = set(found[:KEEP_VERSIONS]) | {current}
    for v in found:
        if v not in keep:
            os.remove(os.path.join(out_subdir, f"{prefix}{v}.zip"))
            print(f"     ancienne version retirée : {v}")


def copy_assets(src, addon_id, root):
    out_subdir = os.path.join(OUTPUT_DIR, addon_id)
    meta = root.find("extension[@point='xbmc.addon.metadata']")
    assets = meta.find("assets") if meta is not None else None
    rels = []
    if assets is not None:
        for tag in ("icon", "fanart"):
            el = assets.find(tag)
            if el is not None and el.text:
                rels.append(el.text)
    if not rels:
        for c in ("icon.png", "resources/icon.png", "fanart.jpg", "resources/fanart.jpg"):
            if os.path.isfile(os.path.join(src, c)):
                rels.append(c)
    if os.path.isfile(os.path.join(src, "changelog.txt")):
        rels.append("changelog.txt")
    for rel in rels:
        f = os.path.join(src, rel)
        if os.path.isfile(f):
            dest = os.path.join(out_subdir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(f, dest)
            print(f"     asset {rel}")
    # Images laissées par une ancienne version et plus déclarées par l'addon
    wanted = {os.path.normpath(r) for r in rels}
    for sub in ("", "resources"):
        folder = os.path.join(out_subdir, sub)
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            rel = os.path.normpath(os.path.join(sub, name))
            if name.lower().endswith((".png", ".jpg", ".jpeg")) and rel not in wanted:
                os.remove(os.path.join(folder, name))
                print(f"     image orpheline retirée : {rel}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    addon_nodes = []

    for src in load_sources():
        if not os.path.isfile(os.path.join(src, "addon.xml")):
            print(f"!! addon.xml introuvable dans {src} — ignoré")
            continue
        addon_id, version, root = addon_meta(src)
        print(f"[{addon_id}] v{version}")

        # Version déjà publiée : le zip est figé, on ne le refait pas.
        kept = published_zip(addon_id, version)
        kept_root = zip_addon_xml(kept, addon_id) if kept else None
        if kept_root is not None and kept_root.get("version") == version:
            print(f"     déjà publiée : {kept} conservé")
            changed = sources_differ(src, root, kept, addon_id)
            if changed:
                warn(f"{addon_id} {version} : sources modifiées depuis la publication "
                     f"({', '.join(changed[:5])}{'…' if len(changed) > 5 else ''}) — "
                     "monter la version pour publier ces changements")
            prune_old_zips(addon_id, version)
            addon_nodes.append(kept_root)
            continue

        check_new_version(src, addon_id, version)
        vendor_dir = build_vendor(src)
        try:
            zpath = zip_addon(src, addon_id, version, root, vendor_dir)
        finally:
            if vendor_dir:
                shutil.rmtree(vendor_dir, ignore_errors=True)
        if addon_id == "repository.theworms":
            stable = os.path.join(OUTPUT_DIR, addon_id, addon_id + ".zip")
            shutil.copy2(zpath, stable)
            print(f"     alias stable -> {stable}")
        copy_assets(src, addon_id, root)
        prune_old_zips(addon_id, version)
        addon_nodes.append(root)

    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    for node in addon_nodes:
        lines.append(ET.tostring(node, encoding="unicode").strip())
    lines.append("</addons>\n")
    addons_xml = "\n".join(lines)

    xml_path = os.path.join(OUTPUT_DIR, "addons.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(addons_xml)
    md5 = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    with open(xml_path + ".md5", "w", encoding="utf-8") as f:
        f.write(md5)
    print(f"\nOK : {xml_path} + .md5 ({md5})")


if __name__ == "__main__":
    main()
