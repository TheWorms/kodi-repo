**Français** · [English](readme.en.md)

# TheWorms Repository

Dépôt Kodi public regroupant les addons maintenus par **theworms**.
Compatible Kodi 19+ (Matrix / Nexus / Omega), testé sur CoreELEC.

## Addons disponibles

<!-- addons:auto -->
| Addon | ID | Description | Version |
|-------|----|-------------|---------|
| **[ProtonVPN Manager](https://github.com/TheWorms/kodi-addon-protonvpn)** | `service.protonvpn.manager` | Connexions ProtonVPN (OpenVPN + WireGuard) depuis Kodi | 0.6.6 |
| **[SoundCloud](https://github.com/TheWorms/kodi-addon-soundcloud)** | `plugin.audio.soundcloud` | Streaming musical et podcasts SoundCloud | 6.0.7 |
| **[Radio](https://github.com/TheWorms/kodi-addon-radio)** | `plugin.audio.radio` | Flux radio | 1.2.19 |
| **[Météo Concept](https://github.com/TheWorms/kodi-addon-meteo)** | `weather.meteoconcept` | Prévisions météo pour la France (API Météo Concept) | 1.0.11 |
| **[EmbyCon](https://github.com/TheWorms/kodi-addon-emby)** | `plugin.video.embycon` | Client Emby pour Kodi — fork français | 1.21.10 |
| **[Keyboard Battery](https://github.com/TheWorms/kodi-addon-keyboardbattery)** | `service.keyboardbattery` | Surveillance du niveau de batterie du clavier | 1.5.7 |
| **[Wtube](https://github.com/TheWorms/kodi-addon-youtube)** | `plugin.video.wtube` | YouTube sans compte : interface plein écran, SponsorBlock, widgets | 0.6.29 |
| **[Moteur JavaScript](https://github.com/TheWorms/kodi-addon-jsruntime)** | `script.module.jsruntime` | Deno / Node.js pour les addons qui en ont besoin (requis par Wtube) | 1.0.4 |
| **[Worms Disk Info](https://github.com/TheWorms/kodi-addon-diskinfo)** | `service.worms.diskinfo` | Espace disque de la partition de données pour le skin | 1.0.0 |
| **[Arctic: Worms](https://github.com/TheWorms/skin.arctic.worms)** | `skin.arctic.worms` | Skin Arctic: Zephyr - Reloaded adapté aux addons du dépôt | 1.0.0 |
<!-- /addons:auto -->

## Installation

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

**Paquets Python embarqués :** si un addon contient un fichier `vendor.txt` (une dépendance pip
par ligne, ex. Wtube : `yt-dlp`, `yt-dlp-ejs`), le générateur installe ces paquets à neuf dans un
venv jetable et les ajoute au zip sous `resources/lib/vendor/`. Le dossier `vendor/` local n'est
jamais repris tel quel.
