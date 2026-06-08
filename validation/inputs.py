import os

from qgis.core import QgsMapLayer, QgsProject, QgsWkbTypes

from ..ahp.calculations import calculate_ahp
from ..core.era5 import cdsapi_available


def _find_layer(layer_id):
    if not layer_id:
        return None
    return QgsProject.instance().mapLayer(layer_id)


def validate_config(config):
    errors = []

    dem_layer = _find_layer(config.dem_layer_id)
    ghi_layer = _find_layer(config.ghi_layer_id)
    lulc_layer = _find_layer(config.lulc_layer_id)

    if dem_layer is None:
        errors.append("Debe seleccionar una capa DEM.")
    elif dem_layer.type() != QgsMapLayer.RasterLayer:
        errors.append("La capa DEM debe ser raster.")
    elif not dem_layer.isValid() or not dem_layer.crs().isValid():
        errors.append("La capa DEM no es valida o no tiene CRS definido.")

    if lulc_layer is None:
        errors.append("Debe seleccionar una capa uso/cobertura del suelo.")
    elif lulc_layer.type() not in {QgsMapLayer.RasterLayer, QgsMapLayer.VectorLayer}:
        errors.append("La capa uso/cobertura del suelo debe ser raster o vectorial.")
    elif not lulc_layer.isValid() or not lulc_layer.crs().isValid():
        errors.append("La capa uso/cobertura del suelo no es valida o no tiene CRS definido.")
    elif lulc_layer.type() == QgsMapLayer.VectorLayer:
        geometry_type = QgsWkbTypes.geometryType(lulc_layer.wkbType())
        if geometry_type != QgsWkbTypes.PolygonGeometry:
            errors.append("La capa vectorial de uso/cobertura debe ser de poligonos.")
        if not config.lulc_field_name:
            errors.append("Debe seleccionar el campo de clases para rasterizar la capa LULC vectorial.")
        elif lulc_layer.fields().indexOf(config.lulc_field_name) < 0:
            errors.append("El campo seleccionado para la capa LULC vectorial no existe.")

    if config.uses_era5_source():
        if not cdsapi_available():
            errors.append(
                "El modo ERA5 requiere el paquete 'cdsapi' en el Python de QGIS y una configuracion valida de '~/.cdsapirc'. "
                "Si no lo tiene instalado, use por ahora la opcion 'Ingresar GHI manualmente'."
            )
        if config.era5_buffer_deg < 0:
            errors.append("El buffer geografico ERA5 debe ser mayor o igual que cero.")
        try:
            if config.analysis_start() > config.analysis_end():
                errors.append("La fecha inicial no puede ser posterior a la fecha final.")
        except ValueError:
            errors.append("Las fechas del periodo de analisis deben usar el formato YYYY-MM-DD.")
        try:
            config.analysis_hours()
        except ValueError as exc:
            errors.append(str(exc))
        try:
            config.era5_ghi_percentile_values()
        except ValueError as exc:
            errors.append(str(exc))
    else:
        if ghi_layer is None:
            errors.append("Debe seleccionar una capa GHI cuando no use ERA5 SSRD.")
        elif ghi_layer.type() != QgsMapLayer.RasterLayer:
            errors.append("La capa GHI debe ser raster.")
        elif not ghi_layer.isValid() or not ghi_layer.crs().isValid():
            errors.append("La capa GHI no es valida o no tiene CRS definido.")

    if config.target_resolution <= 0:
        errors.append("La resolucion objetivo debe ser mayor que cero.")
    if config.slope_threshold_deg <= 0:
        errors.append("La pendiente maxima debe ser mayor que cero.")
    if config.suitability_threshold <= 0:
        errors.append("El umbral de aptitud debe ser mayor que cero.")
    if config.min_area_ha <= 0:
        errors.append("El area minima debe ser mayor que cero.")
    if not config.output_folder:
        errors.append("Debe seleccionar una carpeta de salida.")
    elif not os.path.isdir(config.output_folder):
        errors.append("La carpeta de salida no existe o no es accesible.")
    if not config.target_crs_authid:
        errors.append("El proyecto de QGIS debe tener un CRS valido definido.")

    try:
        config.excluded_lulc_class_values()
    except ValueError:
        errors.append("Las clases LULC excluidas deben ser una lista de enteros separada por comas.")
    if not config.uses_era5_source():
        try:
            config.ghi_break_values()
        except ValueError as exc:
            errors.append(str(exc))
    try:
        slope_breaks = config.slope_break_values()
        if config.slope_threshold_deg < slope_breaks[-1]:
            errors.append("La pendiente maxima debe ser mayor o igual al ultimo corte de pendiente.")
    except ValueError as exc:
        errors.append(str(exc))
    try:
        config.aspect_score_table_values()
    except ValueError as exc:
        errors.append(str(exc))

    if not config.excluded_aspects:
        errors.append("Debe definir al menos una orientacion a excluir.")

    if not config.ahp_matrix:
        errors.append("La matriz AHP no fue definida.")
    else:
        try:
            ahp_result = calculate_ahp(config.ahp_matrix, labels=["GHI", "Pendiente", "Orientacion"])
            if ahp_result["cr"] >= 0.1:
                errors.append(
                    f"La matriz AHP no es consistente: CR={ahp_result['cr']:.4f}. "
                    "Ajuste las comparaciones para lograr CR < 0.1."
                )
        except (ValueError, ZeroDivisionError):
            errors.append("No fue posible calcular la matriz AHP con los valores suministrados.")

    return errors
