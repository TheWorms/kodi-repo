#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de repository Kodi.

Zippe chaque addon dans  zips/<id>/<id>-<version>.zip, copie son icône/fanart
à côté du zip, et régénère  zips/addons.xml + zips/addons.xml.md5.
"""

import hashlib
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

ADDON_SOURCES = [
    "repository.theworms",
    "/run/media/theworms/Data/Git/kodi-addon-protonvpn",
    "/run/media/theworms/Data/Git/kodi-addon-soundcloud",
    "/run/media/theworms/Data/Git/kodi-addon-radio/plugin.audio.radio",
]

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

    print(f"  -> {zip_path}")
    return zip_path


def copy_assets(src, addon_id, root):
    """Copie icône/fanart/changelog vers zips/<id>/ en PRÉSERVANT le chemin
    relatif déclaré dans <assets> (Kodi cherche l'icône à ce chemin exact)."""
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

    for src in ADDON_SOURCES:
        if not os.path.isfile(os.path.join(src, "addon.xml")):
            print(f"!! addon.xml introuvable dans {src} — ignoré")
            continue
        addon_id, version, root = addon_meta(src)
        print(f"[{addon_id}] v{version}")
        zip_addon(src, addon_id, version)
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
