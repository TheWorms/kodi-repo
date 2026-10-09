**Français** · [English](readme.en.md)

# TheWorms Repository

Dépôt Kodi public regroupant les addons maintenus par **theworms**.
Compatible Kodi 19+ (Matrix / Nexus / Omega), testé sur CoreELEC.

## Addons disponibles

<!-- addons:auto -->
| Addon | Description | Version |
|-------|-------------|---------|
| **[ProtonVPN Manager](https://github.com/TheWorms/kodi-addon-protonvpn)** | Connexions ProtonVPN (OpenVPN + WireGuard) depuis Kodi | 0.5.12 |
| **[SoundCloud](https://github.com/TheWorms/kodi-addon-soundcloud)** | Streaming musical et podcasts SoundCloud | 5.9.6027 |
| **[Radio](https://github.com/TheWorms/kodi-addon-radio)** | Flux radio | 1.2.14 |
| **[Météo Concept](https://github.com/TheWorms/kodi-addon-meteo)** | Prévisions météo pour la France (API Météo Concept) | 1.0.7 |
| **[EmbyCon](https://github.com/TheWorms/kodi-addon-emby)** | Client Emby pour Kodi — fork français | 1.14.1 |
| **[Keyboard Battery](https://github.com/TheWorms/kodi-addon-keyboardbattery)** | Surveillance du niveau de batterie du clavier | 1.5.2 |
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
