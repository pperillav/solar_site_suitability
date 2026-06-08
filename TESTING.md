# Prueba rápida en QGIS

Guía para verificar que el complemento Solar Site Suitability (AHP) funciona, usando
el dataset de demostración incluido en `sample_data/` (1.5 x 1.5 km, 225 ha,
EPSG:32618). El flujo con GHI manual no requiere conexión ni dependencias externas.

Requisitos: QGIS 3.28 o superior (Processing con GDAL y los algoritmos nativos, que
vienen por defecto).

## 1. Instalar el plugin

1. En QGIS: Complementos > Administrar e instalar complementos > Instalar a partir de
   ZIP > selecciona `dist/solar_site_suitability.zip` > Instalar.
2. Aparece en Raster > Solar Site Suitability (AHP) y en la barra de herramientas.

## 2. Preparar el proyecto

3. Proyecto nuevo. Proyecto > Propiedades > CRS: fija EPSG:32618. El plugin toma el
   CRS objetivo del proyecto.
4. Carga las tres capas de `sample_data/`: `dem.asc`, `ghi.asc`, `lulc.asc`.

## 3. Ejecutar el modelo

5. Abre Raster > Solar Site Suitability (AHP).
6. Fuente de radiación: **GHI manual** (no requiere cdsapi). Entradas: DEM = dem,
   GHI = ghi, Uso/Cobertura = lulc.
7. Parámetros (los valores por defecto sirven):
   - Resolución objetivo: 12.5 m
   - Pendiente máxima: 15 grados
   - Umbral de aptitud: 4
   - Área mínima: 10 ha
   - Cortes GHI: 4.5,5.0,5.5 ; Cortes pendiente: 5,10,15
   - Hemisferio: Norte (favorable: Sur)
   - Clases LULC excluidas: escribe los códigos de TU cobertura que quieras excluir.
     Para este dataset de muestra puedes usar `3,24,33` (bosque, urbano, agua).
8. AHP: deja los valores por defecto (GHI vs Pendiente = 0.5, GHI vs Orientación = 2,
   Pendiente vs Orientación = 4). Debe mostrar pesos Pendiente 0.571, GHI 0.286,
   Orientación 0.143 y "Consistencia válida" (CR = 0.000).
9. Selecciona una carpeta de salida vacía y pulsa "Validar y ejecutar".

## 4. Resultado esperado

10. El panel Estado muestra una línea "OK:" por etapa y un mensaje final con el número
    de polígonos viables y el área acumulada.
11. Con este dataset y los valores por defecto deberías obtener alrededor de 2 sitios
    viables (~80 ha). El número exacto puede variar un poco según el cálculo de
    pendiente (gdal:slope usa el método de Horn). Para más polígonos, baja el área
    mínima a 1-2 ha o el umbral de aptitud a 3.
12. Se cargan las capas de aptitud y de sitios viables; en la carpeta de salida quedan
    los archivos numerados de `01_dem_aligned.tif` a `17_viable_sites.gpkg`, más
    `18_report.html` y `19_report_summary.csv`.

> Nota: obtener 0 polígonos no es un fallo. Significa que no hay zonas contiguas con
> baja pendiente, buena orientación y alta radiación por encima del área mínima.

## 5. Si algo falla

Anota el mensaje del panel Estado o de la Consola de Python (Complementos > Consola
de Python) para diagnosticar.
