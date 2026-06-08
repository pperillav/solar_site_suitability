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

QGIS 3.28 o superior.
- El complemento está diseñado para ejecutarse dentro del entorno Python de QGIS y utiliza herramientas propias de QGIS, así como proveedores de procesamiento incluidos, como GDAL y algoritmos nativos de QGIS.
- Para el flujo de trabajo con ingreso manual de radiación solar, no se requiere conexión externa una vez que las capas de entrada estén disponibles localmente.
- Para el flujo de trabajo con ERA5, el usuario debe contar con:
    - Una cuenta activa en Copernicus Climate Data Store.
    - Las licencias de los conjuntos de datos requeridos aceptadas en el perfil de usuario de Copernicus.
    - Un archivo de credenciales de la API configurado con el nombre .cdsapirc en la carpeta del usuario.
    - El paquete de Python cdsapi instalado en el entorno Python utilizado por QGIS.
- El complemento acepta un Modelo Digital de Elevación —DEM— como insumo principal del terreno y puede utilizar una capa de cobertura del suelo o una capa de restricciones para excluir áreas no aptas, tales como cuerpos de agua, zonas protegidas, bosques densos, áreas urbanas u otras restricciones definidas por el usuario.
- El DEM debe estar correctamente georreferenciado. Para obtener mejores resultados, se recomienda que la resolución del DEM sea coherente con la escala del análisis. DEM de resolución muy gruesa pueden generar polígonos viables pixelados, fragmentados o poco representativos.
- La carpeta de salida debe permitir escritura, ya que el complemento genera archivos intermedios, capas resultado, reportes y, cuando se utiliza ERA5, el archivo de solicitud preparado.

### Pre-Installation
Configuración de Copernicus / ERA5

La opción ERA5 permite que el complemento descargue datos de radiación solar directamente desde Copernicus Climate Data Store y los convierta en un insumo compatible con el modelo de aptitud basado en GHI.

Antes de utilizar esta opción, se debe realizar la siguiente configuración:

- Ingresar al portal de Copernicus Climate Data Store.
- Crear una cuenta de usuario.
- Confirmar la cuenta mediante el correo electrónico de verificación.
- Iniciar sesión y abrir el perfil de usuario.
- Completar la información del perfil, incluyendo país, tipo de uso, institución y actividad temática.
- Abrir la sección de licencias y aceptar los términos y condiciones de los conjuntos de datos requeridos.
- Copiar las credenciales API indicadas en el perfil de Copernicus.
- Crear un archivo llamado .cdsapirc en la carpeta principal del usuario. En Windows, normalmente corresponde a la siguiente ruta: C:\Users\<usuario>\.cdsapirc
-Verificar que el archivo no quede guardado como .txt. El nombre debe conservarse exactamente como .cdsapirc.
- El archivo debe contener la URL de la API y el token personal suministrado por Copernicus.
- Abrir la consola OSGeo4W Shell de QGIS y verificar que Python esté disponible mediante el comando: python --version

- Instalar o actualizar el cliente CDS API dentro del entorno Python de QGIS:
    - python -m pip install --upgrade pip
    - python -m pip install "cdsapi>=0.7.7"

Esta configuración solo es necesaria cuando el usuario selecciona la opción Calcular GHI desde ERA5 SSRD. Si el usuario ya cuenta con un raster de GHI proveniente de otra fuente, puede utilizar el flujo de trabajo de ingreso manual.
## Installation

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
