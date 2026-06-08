# Solar Site Suitability (AHP)

A QGIS 3 plugin that finds suitable areas for utility-scale photovoltaic (PV) solar
farms using spatial Multi-Criteria Decision Analysis with the Analytic Hierarchy
Process (AHP). It is region-agnostic: it works anywhere in the world, not only in
Colombia, because every threshold, weight and land-cover class is configurable.

Plugin folder: `solar_site_suitability` · Display name: "Solar Site Suitability (AHP)" · License: GPL-3.0-or-later

## What it does

From a DEM-driven workflow the plugin builds a suitability map and extracts candidate sites:

- Inputs: a Digital Elevation Model (DEM) and a land-cover/land-use layer, either raster or polygon vector.
- Solar source: the user can choose between manually providing a GHI raster or
  preparing ERA5 hourly SSRD (`surface_solar_radiation_downwards`) from the DEM
  extent transformed to `EPSG:4326`, with a configurable geographic buffer,
  period, hourly filter and output temporal aggregation.
- Derivatives: slope and aspect from the DEM (GDAL).
- Reclassification: GHI, slope and aspect are reclassified to a 1-5 suitability
  scale using user-defined break values.
- AHP weighting: the three criteria are combined with weights from a pairwise
  comparison matrix, validated by the Consistency Ratio (CR < 0.10).
- Exclusion masks (boolean): steep slope, pole-facing aspect and protected, urban
  or water land cover are removed.
- Site extraction: the high-suitability raster is vectorized and filtered by a
  minimum contiguous area, producing the final candidate polygons.
- Outputs: a suitability raster, a viable-sites GeoPackage, and HTML and CSV
  reports with the number of polygons, accumulated area and full traceability.

## Why another solar plugin

There are good solar plugins already, and this one fills a different niche:

- PV Prospector estimates rooftop/parcel PV potential from high-resolution LIDAR
  for residential properties.
- FotovolCAT automates data acquisition and visualization for solar siting in
  Catalonia.

Both are excellent but tied to a region or to building-level data. Solar Site
Suitability (AHP) is a general-purpose, transparent, multi-criteria siting tool: it
takes any DEM + GHI + land cover and applies a documented AHP model. There are no
hard-coded regional datasets, so the same plugin serves Colombia, Chile, Spain,
India or anywhere with the three input layers.

## Worldwide use (hemisphere)

The optimal panel orientation depends on latitude: in the northern hemisphere the
best-facing slopes look south; in the southern hemisphere they look north. The
favourable orientation is a hemisphere selector in the dialog, and the per-direction
aspect scores and the excluded (pole-facing) sectors are set accordingly, so the
model stays physically correct anywhere.

## Requirements

- QGIS 3.28 or later.
- No extra Python packages. The plugin only uses QGIS core and the bundled
  Processing providers (GDAL and native QGIS algorithms).

## Installation

Once published in the official repository: open QGIS, go to Plugins > Manage and
Install Plugins, search for "Solar Site Suitability (AHP)" and install.

Manual install from this repository:

1. Download or clone this repository.
2. Copy the `solar_site_suitability/` folder into your QGIS plugins directory
   (`QGIS3/profiles/default/python/plugins/`).
3. Enable the plugin in Plugins > Manage and Install Plugins.

## Usage

1. Load your DEM and land-cover layers into QGIS.
2. Open Raster > Solar Site Suitability (AHP) (or the toolbar button).
3. Select the DEM and choose one of the two solar input modes:
   `Ingresar GHI manualmente` or `Calcular GHI desde ERA5 SSRD`.
4. If the land-cover layer is polygonal, choose the attribute field that stores the land-cover class code.
5. If you choose ERA5, calculate the download area and define the analysis period.
6. Set the parameters: target resolution, slope threshold, suitability threshold,
   minimum area, break values, hemisphere, excluded land-cover classes, temporal
   processing and the AHP pairwise comparisons. The dialog shows the resulting
   weights and the Consistency Ratio.
7. Run. The suitability raster and the viable-sites layer are added to the map, and
   the HTML and CSV reports are written to the output folder. The plugin also writes
   the prepared ERA5 request (`00_era5_request.json`) derived from the DEM extent.

The plugin package includes unit tests under `tests/`. If you maintain a separate
demo dataset or documentation repository, keep them outside the installable plugin
folder before publishing.

## Default model parameters

| Parameter | Default | Configurable |
|-----------|---------|--------------|
| Target resolution | 12.5 m | yes |
| Slope exclusion | > 15 deg | yes |
| Suitability threshold | >= 4 (of 5) | yes |
| Minimum contiguous area | 10 ha | yes |
| GHI breaks (kWh/m2/day) | 4.5, 5.0, 5.5 | yes |
| Slope breaks (deg) | 5, 10, 15 | yes |
| Excluded land cover | user list | yes |
| Favourable orientation | hemisphere selector | yes |

## Repository layout

```
solar_site_suitability/          installable QGIS plugin
├── __init__.py                  classFactory entry point
├── metadata.txt
├── icon.png
├── main_plugin.py
├── ahp/ core/ models/ ui/ validation/ reporting/
├── tests/                       pure-Python unit tests
└── README.md
```

## Tests

```bash
 python -m unittest solar_site_suitability.tests.test_ahp \
                   solar_site_suitability.tests.test_config \
                   solar_site_suitability.tests.test_reporting
```

## Authors and citation

Fernan Jose Severich Diaz and Pedro Joaquin Perilla Vargas. Developed for the course
Geomatica General. If you use this plugin in academic work, please cite the
repository and the AHP method (Saaty, 1980).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
