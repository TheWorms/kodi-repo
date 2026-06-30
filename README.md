**English** · [Français](readme.fr.md)

# TheWorms Repository

Public Kodi repository bundling the add-ons maintained by **theworms**.
Compatible with Kodi 19+ (Matrix / Nexus / Omega), tested on CoreELEC.

## Available add-ons

| Add-on | id | Description |
|--------|----|-------------|
| ProtonVPN Manager | `service.protonvpn.manager` | ProtonVPN connections (OpenVPN + WireGuard) from Kodi |
| SoundCloud | `plugin.audio.soundcloud` | SoundCloud music and podcast streaming |
| Radio | `plugin.audio.radio` | Radio streams |
| Météo Concept | `weather.meteoconcept` | Weather forecasts for France (Météo Concept API) |

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
