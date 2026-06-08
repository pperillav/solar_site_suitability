# Publishing to the official QGIS plugin repository

Step-by-step checklist to upload the plugin to https://plugins.qgis.org and get it
approved. The repository and plugin id is `potencial_solar`; the display name is
"Solar Site Suitability (AHP)".

## Before uploading

- [ ] Create a public GitHub repository named `potencial_solar` and push this
      project to it. The repository, tracker and homepage links in
      `potencial_solar/metadata.txt` must point to it and be reachable.
- [ ] If your GitHub username is not `geopedroperilla`, update those three links in
      `metadata.txt` (currently https://github.com/geopedroperilla/potencial_solar).
- [ ] Confirm the repository is public and the source code is visible, not just a
      zip. The committee requires accessible source.
- [ ] Confirm `LICENSE` (GPL-3.0-or-later) is present in the repo and inside the
      plugin folder.
- [ ] Confirm there are no binaries and the zip is under 20 MB (ours is ~52 KB (v1.0.2)).
- [ ] Confirm no `__pycache__`, `.pyc`, `.git` or `__MACOSX` inside the zip.

## Build the installable zip

```bash
python - <<'PY'
import os, zipfile, pathlib
root = pathlib.Path("potencial_solar")
skip = {"__pycache__", ".pytest_cache", ".mypy_cache"}
os.makedirs("dist", exist_ok=True)
with zipfile.ZipFile("dist/potencial_solar.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.rglob("*")):
        if p.is_dir() or p.suffix == ".pyc":
            continue
        if any(part in skip for part in p.parts):
            continue
        z.write(p, p.as_posix())
print("dist/potencial_solar.zip")
PY
```

The zip must contain the `potencial_solar/` folder at its top level, with
`metadata.txt`, `__init__.py` and `icon.png` inside it.

## Local test in QGIS

- [ ] Install the zip via Plugins > Manage and Install Plugins > Install from ZIP.
- [ ] Confirm it loads with no errors and appears under Raster > Solar Site
      Suitability (AHP).
- [ ] Run the workflow with the layers in `sample_data/` (load `dem.asc`, `ghi.asc`
      and `lulc.asc`) and confirm it produces the suitability raster, the
      viable-sites layer and the HTML and CSV reports.

## Upload and request approval

1. Create an OSGeo ID at https://www.osgeo.org/community/getting-started-osgeo/osgeo_userid/
2. Sign in at https://plugins.qgis.org with that OSGeo ID.
3. Go to Share a plugin (https://plugins.qgis.org/plugins/add/) and upload
   `dist/potencial_solar.zip`.
4. The first version of a new plugin is held for review. Approval is usually done
   within a working day (slower on weekends and holidays).
5. If the reviewer requests changes, fix them, bump the version in `metadata.txt`,
   rebuild the zip and upload the new version.

## Notes for a smooth review

- El flujo con GHI manual solo usa el nucleo de QGIS y los proveedores de
  Processing, sin dependencias externas. El flujo ERA5 requiere el paquete opcional
  `cdsapi` y credenciales `~/.cdsapirc`; esto ya esta declarado en el campo `about`
  de `metadata.txt`, como exige el comite para dependencias externas.
- The plugin is region-agnostic; this is stated in the about field, which helps the
  reviewer understand its scope.
- Keep the source in the GitHub repo identical to the uploaded zip contents.
