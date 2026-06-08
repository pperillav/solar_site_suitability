# Manual de uso - Solar Site Suitability (AHP)

Complemento de QGIS para identificar zonas aptas para parques solares fotovoltaicos
mediante un análisis multicriterio (MCDA) con el Proceso de Jerarquía Analítica
(AHP). Versión 1.0.2. Este documento explica qué hace el plugin, cómo usarlo paso a
paso, qué significa cada campo de la interfaz y qué hace cada función interna.

---

## 1. Qué hace el plugin

A partir de un modelo de elevación, una fuente de radiación solar y una capa de
cobertura del suelo, el plugin:

1. Obtiene la radiación solar de dos maneras a elección: un raster de GHI propio, o
   la descarga automática de ERA5 (SSRD de Copernicus) que el plugin convierte a GHI.
2. Armoniza las capas al mismo sistema de coordenadas y tamaño de píxel.
3. Calcula pendiente y orientación a partir del DEM.
4. Reclasifica cada criterio (radiación, pendiente, orientación) a una escala 1 a 5.
5. Combina los criterios con pesos AHP (que tú defines), validados con la Relación de
   Consistencia (CR < 0.10).
6. Excluye zonas no viables con máscaras booleanas (pendiente excesiva, orientación
   desfavorable según hemisferio, coberturas protegidas o urbanas).
7. Extrae los polígonos contiguos que superan un umbral de aptitud y un área mínima.
8. Genera el mapa de aptitud, la capa de sitios viables y reportes HTML y CSV.

---

## 2. Requisitos e instalación

- QGIS 3.28 o superior. El flujo con GHI manual no necesita paquetes adicionales.
- Para el flujo ERA5: el paquete `cdsapi` en el Python de QGIS y un archivo de
  credenciales `~/.cdsapirc` con una cuenta del Copernicus Climate Data Store. Es una
  dependencia opcional; sin ella, igual puedes usar el GHI manual.
- Instalación: Complementos > Administrar e instalar complementos > Instalar a partir
  de ZIP > selecciona `dist/solar_site_suitability.zip` > Instalar.
- Queda en el menú **Raster > Solar Site Suitability (AHP)**.

---

## 3. Insumos de entrada

| Capa | Qué es | Formato | Fuente típica |
|------|--------|---------|---------------|
| DEM | Modelo de elevación; de él se derivan pendiente y orientación | Raster | ALOS PALSAR 12.5 m |
| Radiación solar | GHI manual, o ERA5 SSRD descargado y convertido a GHI | Raster, o descarga | Propio / Copernicus ERA5 |
| Uso/Cobertura | Clases de cobertura para excluir zonas | Raster o vectorial (polígonos) | MapBiomas u otra |

Novedades de la v1.0.2: la radiación puede venir de ERA5 (no necesitas conseguir el
GHI por tu cuenta) y la cobertura puede ser un raster o una capa vectorial de
polígonos (el plugin la rasteriza automáticamente). Fija el CRS del proyecto en uno
proyectado en metros antes de empezar.

---

## 4. Uso paso a paso

1. Carga el DEM (y el GHI manual y/o la cobertura) en QGIS.
2. Fija el CRS del proyecto: Proyecto > Propiedades > CRS.
3. Abre Raster > Solar Site Suitability (AHP).
4. Elige la **fuente de radiación**: GHI manual o ERA5. Si eliges ERA5, aparecen los
   controles de período, horas, resolución temporal y percentiles.
5. Selecciona las capas de entrada y, si aplica, el campo de la cobertura vectorial.
6. Ajusta los parámetros base y el hemisferio (sección 5).
7. Define la matriz AHP (sección 6).
8. Elige una carpeta de salida vacía.
9. Pulsa **Validar y ejecutar**. El panel **Estado** muestra el avance y el resultado.

---

## 5. Qué significa cada campo de la interfaz

| Campo | Qué controla | Valor por defecto |
|-------|--------------|-------------------|
| Fuente de radiación | GHI manual o ERA5 SSRD (descarga) | ERA5 SSRD |
| DEM / Radiación / Cobertura | Capas de entrada | (selección) |
| Campo de cobertura (vectorial) | Atributo con el código de clase, si la cobertura es vectorial | (vacío) |
| Resolución objetivo | Tamaño de píxel al que se remuestrea todo | 12.5 m |
| Pendiente máxima | Pendiente sobre la cual el terreno se excluye | 15 grados |
| Umbral de aptitud | Aptitud mínima (1 a 5) para considerar un píxel apto | 4 |
| Área mínima | Tamaño mínimo de un polígono contiguo para conservarlo | 10 ha |
| Cortes pendiente | Límites que separan las clases de pendiente | 5, 10, 15 |
| Hemisferio | Orientación favorable (Norte: al sur; Sur: al norte) | Norte |
| Clases LULC excluidas | Códigos de cobertura que se eliminan | 1,2,3,4,5,6,24,33 |
| Carpeta de salida | Dónde se escriben los resultados | (selección) |

Campos específicos del flujo ERA5:

| Campo ERA5 | Qué controla | Valor por defecto |
|------------|--------------|-------------------|
| Buffer (grados) | Margen alrededor del DEM para el área de descarga | 0.10 |
| Fecha inicial / final | Período de ERA5 a descargar | 2020-01-01 a 2020-12-31 |
| Modo de horas | Todas las horas o un rango horario | Todas |
| Resolución temporal de salida | Agregación de los productos (mensual, etc.) | Mensual |
| Percentiles GHI | Percentiles que definen las clases de aptitud del GHI | 25,50,75 |
| Guardar NetCDF / GeoTIFF / CSV / recorte | Qué productos ERA5 conservar | Activados |

Con GHI manual se usan los **cortes GHI** fijos (4.5, 5.0, 5.5); con ERA5, las clases
se definen por **percentiles**, porque el rango de la radiación derivada es variable.

El campo **Hemisferio** hace al plugin utilizable en cualquier parte del mundo: en el
norte las laderas favorables miran al sur y en el sur miran al norte.

---

## 6. La matriz AHP

El AHP convierte tu juicio sobre la importancia de cada criterio en pesos. Llenas
tres comparaciones por pares (entre 1/9 y 9):

- GHI vs Pendiente, GHI vs Orientación, Pendiente vs Orientación. Un valor mayor que
  1 favorece el criterio de la izquierda.

El panel muestra la matriz, los pesos y la Relación de Consistencia (CR). Solo se
acepta si **CR < 0.10**. Ejemplo para relieve andino (pendiente dominante): GHI vs
Pendiente = 0.5, GHI vs Orientación = 2, Pendiente vs Orientación = 4, que da pesos
Pendiente 0.571, GHI 0.286, Orientación 0.143 con CR = 0.000.

---

## 7. Qué hace cada función interna

| Etapa | Función / algoritmo | Qué hace |
|-------|---------------------|----------|
| Validación | `validate_config` | Revisa capas, parámetros, opciones ERA5 y la matriz AHP (CR < 0.10). |
| Pesos AHP | `calculate_ahp` | Calcula pesos por el vector propio y la Relación de Consistencia. |
| Solicitud ERA5 | `build_era5_request_plan` + `write_era5_request` | Arma el área (desde el DEM, en EPSG:4326 con buffer) y el período, y guarda la solicitud. |
| Descarga ERA5 | `download_era5_plan` | Descarga el SSRD desde Copernicus con `cdsapi` y descarga HTTP directa. |
| Proceso ERA5 | `process_era5_ssrd` | Convierte SSRD a GHI, agrega por período y escribe NetCDF, GeoTIFF y CSV. |
| Georreferenciación ERA5 | `_era5_georeferencing` | Reconstruye el geotransform desde los metadatos GRIB y asigna EPSG:4326 (corrección de georreferenciado). |
| Percentiles GHI | `raster_percentile_breaks` | Calcula los cortes de aptitud del GHI por percentiles (flujo ERA5). |
| Rasterización cobertura | `rasterize_vector_to_reference` | Convierte una cobertura vectorial a la rejilla de referencia (reproyecta si hace falta). |
| Alineación DEM/GHI/LULC | `warp_to_reference` (gdal:warpreproject) | Reproyecta y remuestrea las capas a una rejilla común. |
| Pendiente / Orientación | `run_gdal_derivative` (gdal:slope / gdal:aspect) | Deriva pendiente y orientación del DEM. |
| Reclasificaciones | `calculate_raster` + `*_reclass_expression` | Convierte GHI, pendiente y orientación a la escala 1-5. |
| Máscaras | `slope_mask_expression`, `aspect_mask_expression`, `lulc_mask_expression` | Excluyen pendiente excesiva, orientación polar y coberturas no aptas. |
| Overlay ponderado | `weighted_overlay_expression` | Suma los criterios por sus pesos AHP. |
| Umbral y aptitud final | `calculate_raster` | Aplica máscaras y deja en 1 los píxeles que superan el umbral. |
| Vectorización | `polygonize_raster` (gdal:polygonize) | Convierte los píxeles aptos en polígonos. |
| Áreas y filtro | `add_area_fields`, `save_filtered_by_area` (native:extractbyexpression) | Calcula el área y conserva los polígonos mayores o iguales al mínimo. |
| Reportes | `write_summary_report`, `write_summary_csv` | Generan los informes HTML y CSV. |

Orquestación: `run_analysis` (en `core/workflow.py`) coordina todas las etapas;
`AnalysisConfig` (en `models/config.py`) guarda y valida los parámetros, incluidos
los de ERA5; `classFactory` integra el plugin en QGIS.

---

## 8. Archivos de salida

Flujo común:

- `01_dem_aligned.tif`, `02_ghi_aligned.tif`, `03_lulc_aligned.tif`: insumos armonizados.
- `04_slope.tif`, `05_aspect.tif`: pendiente y orientación.
- `06`–`08` reclasificaciones, `09`–`12` máscaras.
- `13_suitability_raw.tif`, `14_suitability_final.tif`: aptitud (mapa principal).
- `15_optimal_binary.tif`, `16_optimal_polygons.gpkg`.
- `17_viable_sites.gpkg`: sitios finales (capa clave).
- `18_report.html`, `19_report_summary.csv`: reportes.

Adicionales del flujo ERA5:

- `00_era5_request.json`: la solicitud enviada a Copernicus.
- `era5_ssrd_*.nc`: archivos NetCDF descargados.
- producto GHI en GeoTIFF (EPSG:4326) y serie temporal en CSV.
- `02b_era5_product_clipped.tif`: el producto recortado al área de estudio.

---

## 9. Cómo interpretar el resultado

- `14_suitability_final`: mapa de aptitud (4-5 = mejores zonas).
- `17_viable_sites`: polígonos recomendados, con su área en hectáreas.
- El mensaje final y el reporte indican cuántos sitios y cuánta área se obtuvieron.

Si el resultado es 0 polígonos viables, no es un error: no hay zonas contiguas con
baja pendiente, buena orientación y alta radiación por encima del área mínima. Baja
el umbral o el área mínima, o revisa las clases LULC excluidas.

---

## 10. Problemas frecuentes

- "Debe seleccionar una capa...": faltó elegir DEM, radiación o cobertura.
- "No se encontró el paquete 'cdsapi'...": instala cdsapi y configura `~/.cdsapirc`,
  o cambia la fuente a GHI manual.
- "El proyecto de QGIS debe tener un CRS válido": fija un CRS proyectado en metros.
- "La matriz AHP no es consistente (CR >= 0.1)": ajusta las comparaciones.
- 0 polígonos: ver sección 9.

---

## 11. Glosario

- **GHI:** radiación global horizontal, el recurso solar disponible.
- **SSRD:** radiación solar superficial descendente de ERA5, que se convierte a GHI.
- **ERA5:** reanálisis climático global de Copernicus.
- **AHP:** Proceso de Jerarquía Analítica, método para asignar pesos a criterios.
- **CR:** Relación de Consistencia; mide la coherencia de los juicios del AHP.
- **Orientación (aspect):** dirección hacia la que mira una ladera.
