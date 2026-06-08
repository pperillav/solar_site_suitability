# Protocolo de prueba en QGIS

Verificacion funcional del complemento Solar Site Suitability (AHP) con el dataset
minimo incluido en `sample_data/` (zona de demostracion de 1.5 x 1.5 km = 225 ha,
EPSG:32618, sin binarios). El objetivo es confirmar que el plugin instala, carga y
ejecuta el flujo completo sin tumbar QGIS, y que produce las salidas y los sitios
viables.

Requisitos: QGIS 3.28 o superior (Processing con los proveedores GDAL y "native"
activados, que vienen por defecto).

## 1. Instalar el plugin

1. Usa `dist/solar_site_suitability.zip` (o construyelo con `python scripts/package_plugin.py`).
2. QGIS: Complementos > Administrar e instalar complementos > Instalar a partir de
   ZIP > selecciona el zip > Instalar.
3. Verifica que aparece en Raster > Solar Site Suitability (AHP) y un boton en la
   barra de herramientas. Si carga sin error, el criterio de aprobacion "instala y no
   crashea" se cumple.

## 2. Preparar el proyecto

4. Proyecto nuevo. Proyecto > Propiedades > CRS: fija EPSG:32618 (WGS 84 / UTM 18N).
   El plugin toma el CRS objetivo del proyecto.
5. Carga las tres capas raster de `sample_data/`: `dem.asc`, `ghi.asc`, `lulc.asc`
   (cada una con su `.prj` en EPSG:32618).

## 3. Ejecutar el modelo

6. Abre Raster > Solar Site Suitability (AHP).
7. Fuente de radiación: selecciona **GHI manual** (asi la prueba no requiere
   cdsapi ni credenciales ERA5). Entradas: DEM = dem, GHI = ghi, Uso/Cobertura = lulc.
8. Parametros (los valores por defecto sirven para este dataset):
   - Resolucion objetivo: 12.5 m
   - Pendiente maxima: 15 grados
   - Umbral de aptitud: 4
   - Area minima: 10 ha
   - Cortes GHI: 4.5,5.0,5.5 ; Cortes pendiente: 5,10,15
   - Hemisferio: Norte (favorable: Sur)
   - Clases LULC excluidas: 1,2,3,4,5,6,24,33
9. AHP: deja los valores por defecto (GHI vs Pendiente = 0.5, GHI vs Orientacion = 2,
   Pendiente vs Orientacion = 4). El panel debe mostrar pesos Pendiente 0.571,
   GHI 0.286, Orientacion 0.143 y "Consistencia valida" (CR = 0.000).
10. Selecciona una carpeta de salida vacia.
11. Pulsa "Validar y ejecutar".

## 4. Resultado esperado

12. El panel Estado debe mostrar una linea "OK:" por cada etapa y un mensaje final
    como "Analisis completado. N poligonos viables, X ha acumuladas".
13. Con este dataset y los parametros por defecto deberias obtener **alrededor de 2
    sitios viables (~80 ha en total)**. El numero exacto puede variar un poco porque
    gdal:slope usa el metodo de Horn, ligeramente distinto del calculo de referencia.
    Si quieres mas poligonos, baja el Area minima a 1-2 ha (saldran 3 a 6 sitios) o
    baja el Umbral de aptitud a 3.
14. En el lienzo se cargan las capas de aptitud final y de sitios viables; en la
    carpeta de salida deben existir 19 archivos numerados, de `01_dem_aligned.tif` a
    `17_viable_sites.gpkg`, mas `18_report.html` y `19_report_summary.csv`.
15. Abre `18_report.html`: muestra los parametros, los pesos AHP y la lista de salidas.

> Nota: si pruebas con el dataset anterior u otro muy abrupto, es normal obtener 0
> poligonos viables: significa que no hay zonas contiguas de baja pendiente, buena
> orientacion y alta GHI que superen el area minima. No es un fallo del plugin.

## 5. Que reportar si algo falla

Anota el mensaje exacto del panel Estado o de la Consola de Python. Puntos a vigilar:
errores del Raster Calculator (las mascaras usan la forma compatible `(condicion) = 0`),
nombres de parametros de `processing.run`, y la firma de `QgsRasterCalculator` en
versiones distintas a 3.28+.

