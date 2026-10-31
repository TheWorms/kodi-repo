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
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

SOURCES_FILE = os.environ.get("KODI_REPO_SOURCES", "sources.json")
OUTPUT_DIR = "zips"

EXCLUDED_DIRS = (".git", ".github", ".claude", "__pycache__", ".idea", ".vscode")
EXCLUDED_FILES = {
    ".gitignore", ".gitmodules",
    "CLAUDE.md", "AGENTS.md", "CONTEXT.md",
    "README.md", "readme.md", "readme.en.md",
    "release.sh",
    "vendor.txt",
}

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
    return work


def zip_addon(src, addon_id, version, vendor_dir=None):
    out_subdir = os.path.join(OUTPUT_DIR, addon_id)
    os.makedirs(out_subdir, exist_ok=True)
    zip_path = os.path.join(out_subdir, f"{addon_id}-{version}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        local_vendor = os.path.join(src, VENDOR_DEST)
        for base, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS
                       and not (vendor_dir and os.path.join(base, d) == local_vendor)]
            for f in files:
                if f.endswith((".pyc", ".pyo")) or f in EXCLUDED_FILES:
                    continue
                full = os.path.join(base, f)
                rel = os.path.join(addon_id, os.path.relpath(full, src))
                zf.write(full, rel)
        if vendor_dir:
            vroot = os.path.join(vendor_dir, "vendor")
            for base, dirs, files in os.walk(vroot):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for f in files:
                    if f.endswith((".pyc", ".pyo")):
                        continue
                    full = os.path.join(base, f)
                    zf.write(full, os.path.join(addon_id, VENDOR_DEST, os.path.relpath(full, vroot)))

    print(f"  -> {zip_path}")
    return zip_path


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


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    addon_nodes = []

    for src in load_sources():
        if not os.path.isfile(os.path.join(src, "addon.xml")):
            print(f"!! addon.xml introuvable dans {src} — ignoré")
            continue
        addon_id, version, root = addon_meta(src)
        print(f"[{addon_id}] v{version}")
        vendor_dir = build_vendor(src)
        try:
            zpath = zip_addon(src, addon_id, version, vendor_dir)
        finally:
            if vendor_dir:
                shutil.rmtree(vendor_dir, ignore_errors=True)
        if addon_id == "repository.theworms":
            stable = os.path.join(OUTPUT_DIR, addon_id, addon_id + ".zip")
            shutil.copy2(zpath, stable)
            print(f"     alias stable -> {stable}")
        copy_assets(src, addon_id, root)
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
