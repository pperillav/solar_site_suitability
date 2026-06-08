# Manual de uso - Solar Site Suitability (AHP)

Complemento de QGIS para la identificacion de zonas aptas para proyectos solares fotovoltaicos mediante un analisis multicriterio basado en AHP.

## Requisitos

- QGIS 3.28 o superior.
- El complemento esta disenado para ejecutarse dentro del entorno Python de QGIS y utiliza herramientas propias de QGIS, asi como proveedores de procesamiento incluidos, como GDAL y algoritmos nativos de QGIS.
- Para el flujo de trabajo con ingreso manual de radiacion solar, no se requiere conexion externa una vez que las capas de entrada esten disponibles localmente.
- Para el flujo de trabajo con ERA5, el usuario debe contar con:
  - Una cuenta activa en Copernicus Climate Data Store.
  - Las licencias de los conjuntos de datos requeridos aceptadas en el perfil de usuario de Copernicus.
  - Un archivo de credenciales de la API configurado con el nombre `.cdsapirc` en la carpeta del usuario.
  - El paquete de Python `cdsapi` instalado en el entorno Python utilizado por QGIS.
- El complemento acepta un Modelo Digital de Elevacion (DEM) como insumo principal del terreno y puede utilizar una capa de cobertura del suelo o una capa de restricciones para excluir areas no aptas, tales como cuerpos de agua, zonas protegidas, bosques densos, areas urbanas u otras restricciones definidas por el usuario.
- El DEM debe estar correctamente georreferenciado. Para obtener mejores resultados, se recomienda que la resolucion del DEM sea coherente con la escala del analisis. DEM de resolucion muy gruesa pueden generar poligonos viables pixelados, fragmentados o poco representativos.
- La carpeta de salida debe permitir escritura, ya que el complemento genera archivos intermedios, capas resultado, reportes y, cuando se utiliza ERA5, el archivo de solicitud preparado.

## Configuracion de Copernicus / ERA5

La opcion ERA5 permite que el complemento descargue datos de radiacion solar directamente desde Copernicus Climate Data Store y los convierta en un insumo compatible con el modelo de aptitud basado en GHI.

Antes de utilizar esta opcion, se debe realizar la siguiente configuracion:

1. Ingresar al portal de Copernicus Climate Data Store.
2. Crear una cuenta de usuario.
3. Confirmar la cuenta mediante el correo electronico de verificacion.
4. Iniciar sesion y abrir el perfil de usuario.
5. Completar la informacion del perfil, incluyendo pais, tipo de uso, institucion y actividad tematica.
6. Abrir la seccion de licencias y aceptar los terminos y condiciones de los conjuntos de datos requeridos.
7. Copiar las credenciales API indicadas en el perfil de Copernicus.

Crear un archivo llamado `.cdsapirc` en la carpeta principal del usuario. En Windows, normalmente corresponde a la siguiente ruta:

```text
C:\Users\<usuario>\.cdsapirc
```

Verificar que el archivo no quede guardado como `.txt`. El nombre debe conservarse exactamente como `.cdsapirc`.

El archivo debe contener la URL de la API y el token personal suministrado por Copernicus.

Abrir la consola OSGeo4W Shell de QGIS y verificar que Python este disponible mediante el comando:

```bash
python --version
```

Instalar o actualizar el cliente CDS API dentro del entorno Python de QGIS:

```bash
python -m pip install --upgrade pip
python -m pip install "cdsapi>=0.7.7"
```

Esta configuracion solo es necesaria cuando el usuario selecciona la opcion `Calcular GHI desde ERA5 SSRD`. Si el usuario ya cuenta con un raster de GHI proveniente de otra fuente, puede utilizar el flujo de trabajo de ingreso manual.

## Instalacion

Una vez publicado en el repositorio oficial de complementos de QGIS:

1. Abrir QGIS.
2. Ir a `Complementos > Administrar e instalar complementos`.
3. Buscar `Solar Site Suitability (AHP)`.
4. Seleccionar `Instalar`.
5. Activar el complemento, en caso de que no quede habilitado automaticamente.
6. Abrirlo desde el menu `Raster` o desde el boton de la barra de herramientas.

Instalacion manual desde este repositorio:

1. Descargar o clonar este repositorio.
2. Localizar la carpeta instalable del complemento: `solar_site_suitability/`.
3. Copiar esta carpeta en el directorio de complementos de QGIS. En Windows, una ruta tipica es:

```text
C:\Users\<usuario>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
```

4. Reiniciar QGIS.
5. Abrir `Complementos > Administrar e instalar complementos`.
6. Activar `Solar Site Suitability (AHP)`.

Si existia una version anterior instalada manualmente o desde un archivo ZIP, se recomienda desinstalarla primero desde el administrador de complementos de QGIS. Si QGIS continua cargando informacion de la version anterior, se debe eliminar manualmente la carpeta `solar_site_suitability/` del directorio de complementos antes de instalar la nueva version. Esto evita conflictos por archivos antiguos o informacion almacenada en cache.

## Datos de entrada

El complemento requiere al menos una capa DEM cargada en QGIS. Este DEM se utiliza para derivar variables topograficas como la pendiente y la orientacion del terreno.

El usuario tambien puede cargar capas espaciales complementarias, tales como:

- Rasteres de cobertura del suelo.
- Capas vectoriales poligonales de cobertura del suelo.
- Capas de restricciones ambientales.
- Poligonos de areas protegidas.
- Poligonos de areas urbanas.
- Capas de cuerpos de agua.
- Zonas de amenaza o exclusion.
- Poligonos dibujados por el usuario para representar areas que no deben ser consideradas.

Si la capa de cobertura del suelo es poligonal, el usuario debe seleccionar el campo de atributos donde se almacena el codigo de clase de cobertura. El complemento rasteriza la capa vectorial tomando como referencia la grilla del DEM antes de aplicar las reglas de exclusion.

## Uso del complemento

1. Cargar en QGIS el DEM del area de estudio.
2. Cargar, si aplica, la capa de cobertura del suelo o de restricciones que se utilizara para excluir areas no aptas.
3. Abrir el complemento desde `Raster > Solar Site Suitability (AHP)` o desde el boton de la barra de herramientas.
4. Seleccionar la capa DEM.
5. Elegir uno de los dos modos de entrada de radiacion solar:
   - `Ingresar GHI manualmente`
   - `Calcular GHI desde ERA5 SSRD`
6. Si se selecciona `Ingresar GHI manualmente`, se debe proporcionar el raster local de GHI que sera utilizado en el modelo.
7. Si se selecciona `Calcular GHI desde ERA5 SSRD`, se debe:
   - Verificar que las credenciales de Copernicus esten configuradas.
   - Calcular el area de descarga a partir de la extension del DEM.
   - Definir el periodo de analisis.
   - Seleccionar el rango horario que sera procesado.
   - Preferir unicamente horas diurnas, por ejemplo de `07:00` a `17:00`, para evitar incluir valores nocturnos que no son utiles para la generacion solar fotovoltaica.
   - Seleccionar el modo de procesamiento temporal, como diario, mensual, anual o promedio multianual, segun la duracion y el objetivo del analisis.
8. Definir la resolucion objetivo. Se recomienda utilizar un valor coherente con la resolucion del DEM.
9. Definir el umbral de aptitud. El modelo utiliza una calificacion normalizada de `0` a `5`. Solo las celdas con una calificacion igual o superior al umbral seleccionado se conservan como aptas.
10. Definir el area minima. Este valor controla el tamano minimo de los poligonos viables resultantes. Las celdas aisladas o grupos de celdas muy pequenos que no alcancen esta area minima son excluidos del resultado final.
11. Definir los parametros de pendiente:
   - Pendiente maxima admisible.
   - Valores de corte para clasificar pendientes favorables, aceptables y limite.
12. Seleccionar el hemisferio. Este parametro controla la orientacion favorable del terreno:
   - En el hemisferio norte, las laderas con orientacion hacia el sur suelen ser mas favorables.
   - En el hemisferio sur, las laderas con orientacion hacia el norte suelen ser mas favorables.
13. Seleccionar las clases de cobertura del suelo o restriccion que seran excluidas del analisis.
14. Configurar las comparaciones pareadas del metodo AHP entre los criterios principales:
   - Radiacion solar / GHI.
   - Pendiente.
   - Orientacion del terreno.
15. Revisar los pesos resultantes del AHP y la razon de consistencia.
16. Si la razon de consistencia es demasiado alta, ajustar las comparaciones pareadas hasta obtener una matriz consistente.
17. Hacer clic en `Validar y ejecutar`.
18. Esperar a que finalice el procesamiento. Si se selecciono ERA5, el complemento primero descarga los archivos climaticos requeridos y posteriormente ejecuta el flujo de procesamiento raster.
19. Revisar las capas resultado que se agregan automaticamente al proyecto de QGIS.

## Logica del modelo

El complemento realiza un analisis multicriterio de aptitud mediante un flujo de trabajo basado en raster. Cada celda del DEM es evaluada de acuerdo con tres criterios principales:

- Radiacion solar o GHI.
- Pendiente del terreno.
- Orientacion del terreno o aspecto.

Cada variable es clasificada y convertida en una calificacion de aptitud. Posteriormente, los criterios se combinan utilizando los pesos AHP definidos por el usuario mediante comparaciones pareadas.

La calificacion final varia entre `0` y `5`. El umbral de aptitud determina cuales celdas son aceptadas en el resultado final. Por ejemplo, si el umbral se define en `4`, solamente las celdas con calificaciones entre `4` y `5` seran conservadas como aptas.

Luego se aplica el parametro de area minima para evitar reportar celdas aisladas o areas impracticas. El complemento agrupa las celdas aptas en poligonos y elimina aquellos que sean menores al area minima seleccionada.

## Procesamiento de radiacion solar con ERA5

Cuando se selecciona la opcion ERA5, el complemento calcula un area de descarga a partir de la extension del DEM. Puede aplicarse un buffer para asegurar que los datos climaticos descargados cubran completamente el area de estudio y evitar efectos de borde.

El complemento no descarga informacion ERA5 global. Prepara una solicitud limitada al cuadro envolvente del DEM y al periodo seleccionado por el usuario. La solicitud preparada se guarda como:

```text
00_era5_request.json
```

Los datos ERA5 pueden descargarse en uno o varios archivos, dependiendo del intervalo de tiempo y de la resolucion temporal seleccionada. Para pruebas iniciales se recomienda utilizar periodos cortos, por ejemplo algunos dias. Periodos largos, como varios anos de informacion diaria, pueden tardar considerablemente en descargarse y procesarse.

Debido a que ERA5 tiene una resolucion espacial mas gruesa que muchos DEM, areas de estudio pequenas pueden quedar cubiertas por una sola celda o por muy pocas celdas ERA5. En esos casos, la superficie de radiacion solar puede presentar poca variacion espacial y el resultado dependera con mayor fuerza de la pendiente, la orientacion y las restricciones aplicadas.

## Procesamiento de coberturas y restricciones

El complemento puede utilizar informacion de cobertura del suelo para excluir areas que no deben considerarse tecnica, ambiental o espacialmente aptas.

Algunos ejemplos de areas que pueden excluirse son:

- Cuerpos de agua.
- Bosques densos.
- Areas protegidas.
- Zonas urbanas.
- Zonas de amenaza.
- Areas con uso del suelo incompatible.
- Poligonos de restriccion definidos por el usuario.

Para capas raster de cobertura del suelo, el usuario selecciona los codigos de clase que desea excluir.

Para capas vectoriales poligonales, el complemento solicita el campo de atributo que contiene el codigo de clase, reproyecta la capa si es necesario y la rasteriza para igualarla a la grilla del DEM antes de aplicar la mascara de exclusion.

Los criterios de exclusion deben definirse de acuerdo con el objetivo del estudio. Por ejemplo, un cuerpo de agua normalmente debe excluirse, mientras que un area sin vegetacion puede permanecer como potencialmente apta, dependiendo del tipo de proyecto.

## Salidas del complemento

Despues de la ejecucion, el complemento agrega los resultados principales al lienzo de QGIS y escribe los archivos de salida en la carpeta seleccionada.

Las salidas incluyen:

- Raster de aptitud.
- Capa vectorial de sitios viables.
- Capas raster intermedias utilizadas en el analisis.
- Reporte HTML.
- Reporte CSV.
- Archivo de solicitud ERA5, cuando se utiliza esta opcion.
- Archivos descargados o procesados de ERA5, segun el flujo de trabajo seleccionado.

Al final del proceso, el complemento informa el numero de poligonos viables y el area total apta. Estos poligonos pueden revisarse en QGIS para identificar areas candidatas para la implantacion de proyectos solares fotovoltaicos.

## Interpretacion de resultados

La capa de sitios viables debe interpretarse como una preseleccion tecnica y no como una decision definitiva de diseno o localizacion.

El complemento identifica areas que cumplen los criterios seleccionados, pero la seleccion final de un sitio para un proyecto solar debe considerar tambien:

- Propiedad del terreno.
- Restricciones legales.
- Permisos ambientales.
- Accesos viales.
- Distancia a infraestructura electrica.
- Condiciones constructivas.
- Condiciones geotecnicas.
- Amenazas por inundacion o movimientos en masa.
- Aceptacion comunitaria.
- Verificacion en campo.

Resultados muy fragmentados pueden indicar que el area de estudio es demasiado amplia, que la resolucion del DEM es muy gruesa, que el area minima definida es muy pequena o que los criterios de seleccion son demasiado permisivos. En ese caso, el usuario puede refinar el analisis aumentando el area minima, reduciendo la pendiente maxima admisible, ajustando los pesos AHP o utilizando un DEM de mayor resolucion.

## Notas para pruebas y publicacion

El paquete del complemento incluye pruebas unitarias dentro de la carpeta `tests/`.

Antes de publicar el complemento en el repositorio oficial de QGIS se recomienda:

- Mantener los datos de demostracion por fuera de la carpeta instalable del complemento.
- Mantener archivos grandes de documentacion por fuera del paquete del complemento.
- Documentar claramente las dependencias opcionales asociadas al flujo ERA5.
- Confirmar que el complemento pueda ejecutarse con GHI manual cuando no existan credenciales ERA5.
- Probar el complemento en un perfil limpio de QGIS para evitar conflictos con versiones anteriores.
- Verificar que todos los archivos de salida se escriban correctamente en la carpeta seleccionada.
- Confirmar que la razon de consistencia AHP se muestre adecuadamente y que las comparaciones inconsistentes sean advertidas antes de ejecutar el modelo.
