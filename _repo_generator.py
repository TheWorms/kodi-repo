#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de repository Kodi.

Lit une liste de dossiers-sources d'addons (chacun contient un addon.xml),
zippe chaque addon dans  zips/<id>/<id>-<version>.zip  et régénère
zips/addons.xml + zips/addons.xml.md5.

Usage :
    python3 _repo_generator.py
"""

import hashlib
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# CONFIG — adapte uniquement ces deux listes
# ---------------------------------------------------------------------------

ADDON_SOURCES = [
    "repository.theworms",
    "/run/media/theworms/Data/Git/kodi-addon-protonvpn",
    "/run/media/theworms/Data/Git/kodi-addon-soundcloud",
    "/run/media/theworms/Data/Git/kodi-addon-radio/plugin.audio.radio",
]

EXTRA_FILES = ["icon.png", "fanart.jpg", "changelog.txt"]

OUTPUT_DIR = "zips"

# ---------------------------------------------------------------------------


def addon_meta(src):
    tree = ET.parse(os.path.join(src, "addon.xml"))
    root = tree.getroot()
    return root.get("id"), root.get("version"), root


def zip_addon(src, addon_id, version):
    out_subdir = os.path.join(OUTPUT_DIR, addon_id)
    os.makedirs(out_subdir, exist_ok=True)
    zip_path = os.path.join(out_subdir, f"{addon_id}-{version}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, files in os.walk(src):
            if any(p in base for p in (".git", "__pycache__", ".github")):
                continue
            for f in files:
                if f.endswith((".pyc", ".pyo")) or f == ".gitignore":
                    continue
                full = os.path.join(base, f)
                # racine du zip = ID Kodi (exigé), pas le nom du dossier source
                rel = os.path.join(addon_id, os.path.relpath(full, src))
                zf.write(full, rel)

    for extra in EXTRA_FILES:
        candidate = os.path.join(src, extra)
        if os.path.exists(candidate):
            shutil.copy2(candidate, os.path.join(out_subdir, extra))

    print(f"  -> {zip_path}")
    return zip_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    addon_nodes = []

    for src in ADDON_SOURCES:
        if not os.path.isfile(os.path.join(src, "addon.xml")):
            print(f"!! addon.xml introuvable dans {src} — ignoré")
            continue
        addon_id, version, root = addon_meta(src)
        print(f"[{addon_id}] v{version}")
        zip_addon(src, addon_id, version)
        addon_nodes.append(root)

    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    for node in addon_nodes:
        xml = ET.tostring(node, encoding="unicode").strip()
        lines.append(xml)
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
