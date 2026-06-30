[English](README.md) · **Français**

# TheWorms Repository

Dépôt Kodi public regroupant les addons maintenus par **theworms**.
Compatible Kodi 19+ (Matrix / Nexus / Omega), testé sur CoreELEC.

## Addons disponibles

| Addon | id | Description |
|-------|----|-------------|
| ProtonVPN Manager | `service.protonvpn.manager` | Connexions ProtonVPN (OpenVPN + WireGuard) depuis Kodi |
| SoundCloud | `plugin.audio.soundcloud` | Streaming musical et podcasts SoundCloud |
| Radio | `plugin.audio.radio` | Flux radio |
| Météo Concept | `weather.meteoconcept` | Prévisions météo pour la France (API Météo Concept) |

## Installation (recommandé)

Le dépôt gère les mises à jour automatiquement. **Il n'y a pas de Release** à télécharger — tout passe par le dépôt.

Télécharge le dépôt en cliquant **[ICI](https://raw.githubusercontent.com/TheWorms/kodi-repo/main/zips/repository.theworms/repository.theworms.zip)**, puis dans Kodi :

1. **Add-ons** → **Installer depuis un fichier zip** → sélectionne le zip téléchargé
   *(si Kodi bloque, active **Sources inconnues** dans Système → Add-ons)*
2. **Installer depuis un dépôt** → **TheWorms Repository** → choisis un addon
3. Les mises à jour seront ensuite proposées automatiquement

## Structure

```
zips/                         ← servi par raw.githubusercontent.com
├── addons.xml                ← index lu par Kodi
├── addons.xml.md5
└── <id>/<id>-<version>.zip   ← chaque addon empaqueté (+ icon/fanart)
```

## Maintenance

Régénération de l'index après chaque mise à jour d'un addon :

```bash
python3 _repo_generator.py     # rezippe + reconstruit addons.xml + md5
git add -A && git commit -m "maj" && git push
```

Kodi ne lit que `zips/addons.xml`, jamais les sources : sans régénération, aucune MAJ n'est propagée.
