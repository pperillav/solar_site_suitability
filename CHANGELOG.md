# Changelog

Formato basado en Keep a Changelog; el proyecto sigue versionado semántico.

## [1.0.3] - 2026

- Corrección de seguridad: se elimina una ruta temporal fija (`/tmp/...`) en una
  prueba unitaria, reemplazada por `tempfile.gettempdir()`, que disparaba el hallazgo
  crítico B108 de Bandit en el escáner de seguridad del repositorio de QGIS.
- Limpieza de los permisos de archivo del paquete distribuido (sin bit de ejecución
  en los `.py`).

## [1.0.2] - 2026

- Descarga ERA5 ajustada para usar la URL de resultados del cliente ECMWF y descarga
  HTTP directa.

## [1.0.1] - 2026

- Correcciones de compatibilidad en la descarga ERA5 con cdsapi.
- Ajustes en la rasterización de cobertura vectorial y en la reclasificación de GHI
  por percentiles para ERA5.

## [1.0.0] - 2026

- Primera versión estable.
- Fuente solar dual: GHI manual o GHI calculado desde ERA5 SSRD (Copernicus).
- Descarga ERA5 a partir de la extensión del DEM, con área automática en EPSG:4326,
  control temporal y cortes de GHI por percentiles.
- Corrección de georreferenciado del producto ERA5 (geotransform desde metadatos GRIB).
- Soporte de cobertura raster o vectorial, con rasterización automática.
- Orientación favorable configurable por hemisferio (uso mundial).
- Máscaras de exclusión, overlay ponderado AHP (CR < 0.10), umbral y filtro de área.
- Interfaz con scroll, resumen del modelo y tooltips; reportes HTML y CSV.

## [0.1.0] - 2026

- Flujo MCDA-AHP base en PyQGIS (Processing: GDAL y algoritmos nativos).
- Reclasificación 1-5, pesos AHP, máscaras y filtro de área mínima.
- Dataset de prueba y pruebas unitarias puras.
