# TheWorms Repository

Dépôt Kodi public regroupant les addons maintenus par **theworms**.
Compatible Kodi 19+ (Matrix / Nexus / Omega), testé sur CoreELEC.

## Addons disponibles

| Addon | id | Description |
|-------|----|-------------|
| ProtonVPN Manager | `service.protonvpn.manager` | Connexions ProtonVPN (OpenVPN + WireGuard) depuis Kodi |
| SoundCloud | `plugin.audio.soundcloud` | Streaming musical et podcasts SoundCloud |
| Radio | `plugin.audio.radio` | Flux radio en français |
| Météo Concept | `weather.meteoconcept` | Prévisions météo France (API Météo Concept) |

## Installation via le dépôt TheWorms (recommandé)

Le dépôt gère les mises à jour automatiquement.

1. Télécharge le zip du dépôt : [https://raw.githubusercontent.com/TheWorms/kodi-repo/main/zips/repository.theworms/repository.theworms.zip](https://raw.githubusercontent.com/TheWorms/kodi-repo/main/zips/repository.theworms/repository.theworms.zip)
2. Kodi → **Add-ons** → **Installer depuis un fichier zip** → sélectionne ce zip
   *(si Kodi bloque, active **Sources inconnues** dans Système → Add-ons)*
3. **Installer depuis un dépôt** → **TheWorms Repository** → choisis l'addon
4. Les mises à jour seront ensuite proposées automatiquement

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

Kodi ne lit que `zips/addons.xml` : sans régénération, aucune MAJ n'est propagée aux clients.
