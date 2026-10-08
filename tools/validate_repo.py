#!/usr/bin/env python3
"""Validation du dépôt Kodi : zips, addons.xml, checksum md5, cohérence des versions."""

import glob
import hashlib
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

ZIPS_DIR = "zips"
DEV_FILES = {
    "CLAUDE.md", "AGENTS.md", "README.md", "readme.md", "readme.en.md",
    "release.sh", ".gitignore",
}
DEV_PARTS = (".claude/", "__pycache__/", ".git/", ".github/")

failed = False


def fail(msg):
    print(f"ERREUR: {msg}")
    global failed
    failed = True


xml_path = os.path.join(ZIPS_DIR, "addons.xml")
md5_path = xml_path + ".md5"
for p in (xml_path, md5_path):
    if not os.path.isfile(p):
        print(f"ERREUR: {p} manquant")
        sys.exit(1)

with open(xml_path, encoding="utf-8") as f:
    addons_xml = f.read()
with open(md5_path, encoding="utf-8") as f:
    expected = f.read().strip()
actual = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
if actual != expected:
    fail(f"addons.xml.md5 ({expected}) != md5 addons.xml ({actual}) — régénérer avec _repo_generator.py")
else:
    print(f"OK: addons.xml.md5 ({actual})")

declared = {}
root = ET.fromstring(addons_xml)
for addon in root.findall("addon"):
    aid, ver = addon.get("id"), addon.get("version")
    if not aid or not ver:
        fail(f"addon sans id/version dans addons.xml: {addon}")
        continue
    if aid in declared:
        fail(f"addon {aid} déclaré plusieurs fois")
    declared[aid] = ver
print(f"OK: {len(declared)} addons déclarés")

on_disk = {}
for z in glob.glob(os.path.join(ZIPS_DIR, "*", "*.zip")):
    addon = os.path.basename(os.path.dirname(z))
    base = os.path.basename(z)
    if base == addon + ".zip":
        continue
    on_disk.setdefault(addon, {})[base[len(addon) + 1:-4]] = z

for aid, ver in declared.items():
    if aid not in on_disk:
        fail(f"{aid} déclaré v{ver} mais aucun zip présent")
        continue
    if ver not in on_disk[aid]:
        fail(f"{aid} déclaré v{ver} mais zip absent de zips/{aid}/")
    print(f"OK: {aid} v{ver} présent")

for z in glob.glob(os.path.join(ZIPS_DIR, "*", "*.zip")):
    addon = os.path.basename(os.path.dirname(z))
    try:
        with zipfile.ZipFile(z) as zf:
            if zf.testzip() is not None:
                fail(f"CRC invalide: {z}")
            roots = {n.split("/")[0] for n in zf.namelist()}
            if roots != {addon}:
                fail(f"racine du zip {z} != {addon}: {sorted(roots)}")
            for n in zf.namelist():
                if n.startswith("/") or ".." in n:
                    fail(f"chemin suspect dans {z}: {n}")
                if os.path.basename(n) in DEV_FILES or any(p in n for p in DEV_PARTS):
                    fail(f"fichier de dev dans {z}: {n}")
    except zipfile.BadZipFile as e:
        fail(f"zip illisible: {z}: {e}")

print()
if failed:
    sys.exit(1)
print("Dépôt valide : zips, addons.xml et md5 cohérents.")
