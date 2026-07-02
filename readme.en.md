[Français](README.md) · **English**

# TheWorms Repository

Public Kodi repository bundling the add-ons maintained by **theworms**.
Compatible with Kodi 19+ (Matrix / Nexus / Omega), tested on CoreELEC.

## Available add-ons

<!-- addons:auto -->
| Add-on | ID | Description | Version |
|--------|----|-------------|---------|
| ProtonVPN Manager | `service.protonvpn.manager` | ProtonVPN connections (OpenVPN + WireGuard) from Kodi | 0.5.9 |
| SoundCloud | `plugin.audio.soundcloud` | SoundCloud music and podcast streaming | 5.9.6022 |
| Radio | `plugin.audio.radio` | Radio streams | 1.0.7 |
| Météo Concept | `weather.meteoconcept` | Weather forecasts for France (Météo Concept API) | 1.0.5 |
| EmbyCon | `plugin.video.embycon` | Emby client for Kodi — French fork | 1.13.26 |
| Keyboard Battery | `service.keyboardbattery` | Keyboard battery level monitor | 1.5.0 |
<!-- /addons:auto -->

## Installation

Download the repository by clicking **[HERE](https://raw.githubusercontent.com/TheWorms/kodi-repo/main/zips/repository.theworms/repository.theworms.zip)**, then in Kodi:

1. **Add-ons** → **Install from zip file** → select the downloaded zip
   *(if Kodi blocks it, enable **Unknown sources** under Settings → Add-ons)*
2. **Install from repository** → **TheWorms Repository** → pick an add-on
3. Updates will then be offered automatically

## Structure

```
zips/                         ← served by raw.githubusercontent.com
├── addons.xml                ← index read by Kodi
├── addons.xml.md5
└── <id>/<id>-<version>.zip   ← each add-on packaged (+ icon/fanart)
```

## Maintenance

Regenerate the index after each add-on update:

```bash
python3 _repo_generator.py     # rezips + rebuilds addons.xml + md5
git add -A && git commit -m "update" && git push
```

Kodi only reads `zips/addons.xml`, never the sources: without regeneration, no update is propagated.
