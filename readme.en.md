[Français](README.md) · **English**

# TheWorms Repository

Public Kodi repository bundling the add-ons maintained by **theworms**.
Compatible with Kodi 19+ (Matrix / Nexus / Omega), tested on CoreELEC.

## Available add-ons

<!-- addons:auto -->
| Add-on | ID | Description | Version |
|-------|----|-------------|---------|
| **[ProtonVPN Manager](https://github.com/TheWorms/kodi-addon-protonvpn)** | `service.protonvpn.manager` | ProtonVPN connections (OpenVPN + WireGuard) from Kodi | 0.6.6 |
| **[SoundCloud](https://github.com/TheWorms/kodi-addon-soundcloud)** | `plugin.audio.soundcloud` | SoundCloud music and podcast streaming | 6.0.7 |
| **[Radio](https://github.com/TheWorms/kodi-addon-radio)** | `plugin.audio.radio` | Radio streams | 1.2.19 |
| **[Météo Concept](https://github.com/TheWorms/kodi-addon-meteo)** | `weather.meteoconcept` | Weather forecasts for France (Météo Concept API) | 1.0.11 |
| **[EmbyCon](https://github.com/TheWorms/kodi-addon-emby)** | `plugin.video.embycon` | Emby client for Kodi — French fork | 1.21.10 |
| **[Keyboard Battery](https://github.com/TheWorms/kodi-addon-keyboardbattery)** | `service.keyboardbattery` | Keyboard battery level monitor | 1.5.7 |
| **[Wtube](https://github.com/TheWorms/kodi-addon-youtube)** | `plugin.video.wtube` | YouTube without an account: full-screen interface, SponsorBlock, widgets | 0.6.29 |
| **[JavaScript engine](https://github.com/TheWorms/kodi-addon-jsruntime)** | `script.module.jsruntime` | Deno / Node.js for add-ons that need one (required by Wtube) | 1.0.4 |
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

**Bundled Python packages:** if an add-on contains a `vendor.txt` file (one pip dependency per
line, e.g. Wtube: `yt-dlp`, `yt-dlp-ejs`), the generator installs those packages fresh in a
throwaway venv and adds them to the zip under `resources/lib/vendor/`. The local `vendor/` folder
is never copied as is.
