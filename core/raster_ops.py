import os

import processing
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRasterLayer, QgsVectorLayer


def load_raster(layer_or_path, layer_name=None):
    if isinstance(layer_or_path, QgsRasterLayer):
        return layer_or_path
    layer = QgsRasterLayer(layer_or_path, layer_name or os.path.basename(layer_or_path))
    if not layer.isValid():
        raise ValueError(f"No fue posible cargar el raster: {layer_or_path}")
    return layer


def warp_to_reference(input_layer, output_path, target_crs_authid, pixel_size, extent=None):
    target_crs = QgsCoordinateReferenceSystem(target_crs_authid)
    extent_string = None
    if extent is not None:
        extent_string = (
            f"{extent.xMinimum()},{extent.xMaximum()},"
            f"{extent.yMinimum()},{extent.yMaximum()} [{target_crs.authid()}]"
        )
    params = {
        "INPUT": input_layer,
        "SOURCE_CRS": None,
        "TARGET_CRS": target_crs,
        "RESAMPLING": 0,
        "NODATA": None,
        "TARGET_RESOLUTION": pixel_size,
        "OPTIONS": "",
        "DATA_TYPE": 0,
        "TARGET_EXTENT": extent_string,
        "TARGET_EXTENT_CRS": target_crs,
        "MULTITHREADING": False,
        "EXTRA": "",
        "OUTPUT": output_path,
    }
    result = processing.run("gdal:warpreproject", params)
    return load_raster(result["OUTPUT"], os.path.splitext(os.path.basename(output_path))[0])


def run_gdal_derivative(algorithm_id, input_layer, output_path):
    params = {
        "INPUT": input_layer,
        "BAND": 1,
        "COMPUTE_EDGES": False,
        "ZEVENBERGEN": False,
        "OPTIONS": "",
        "EXTRA": "",
        "OUTPUT": output_path,
    }
    if algorithm_id == "gdal:aspect":
        params.update({"TRIG_ANGLE": False, "ZERO_FLAT": False})
    elif algorithm_id == "gdal:slope":
        params.update({"SCALE": 1.0, "AS_PERCENT": False})
    result = processing.run(algorithm_id, params)
    return load_raster(result["OUTPUT"], os.path.splitext(os.path.basename(output_path))[0])


def rasterize_vector_to_reference(input_layer, field_name, reference_layer, output_path):
    reference = load_raster(reference_layer, "reference")
    vector_layer = input_layer
    temp_vector_path = None
    source_path = input_layer.source()
    if not isinstance(input_layer, QgsVectorLayer):
        raise ValueError("La capa LULC vectorial no es valida para rasterizacion.")
    if input_layer.crs() != reference.crs():
        temp_vector_path = os.path.splitext(output_path)[0] + "_reprojected.gpkg"
        reprojection = processing.run(
            "native:reprojectlayer",
            {
                "INPUT": input_layer,
                "TARGET_CRS": reference.crs(),
                "OUTPUT": temp_vector_path,
            },
        )
        vector_layer = QgsVectorLayer(reprojection["OUTPUT"], os.path.basename(temp_vector_path), "ogr")
        source_path = reprojection["OUTPUT"]
        if not vector_layer.isValid():
            raise ValueError("No fue posible reproyectar la capa LULC vectorial.")

    try:
        from osgeo import gdal, ogr
    except ImportError as exc:
        raise ValueError("No fue posible importar GDAL/OGR para rasterizar la capa LULC vectorial.") from exc

    reference_dataset = gdal.Open(reference.source())
    if reference_dataset is None:
        raise ValueError("No fue posible abrir el raster de referencia para rasterizar LULC.")
    driver = gdal.GetDriverByName("GTiff")
    output_dataset = driver.Create(
        output_path,
        reference.width(),
        reference.height(),
        1,
        gdal.GDT_Int32,
    )
    if output_dataset is None:
        raise ValueError(f"No fue posible crear el raster LULC: {output_path}")
    output_dataset.SetGeoTransform(reference_dataset.GetGeoTransform())
    output_dataset.SetProjection(reference_dataset.GetProjection())
    output_band = output_dataset.GetRasterBand(1)
    output_band.Fill(0)

    vector_dataset = ogr.Open(source_path)
    if vector_dataset is None:
        raise ValueError("No fue posible abrir la capa vectorial para rasterizar LULC.")
    vector_lyr = vector_dataset.GetLayer()
    result_code = gdal.RasterizeLayer(
        output_dataset,
        [1],
        vector_lyr,
        options=[f"ATTRIBUTE={field_name}", "ALL_TOUCHED=TRUE"],
    )
    output_band.FlushCache()
    output_dataset.FlushCache()
    output_dataset = None
    vector_dataset = None
    reference_dataset = None
    if result_code != 0:
        raise ValueError("GDAL no pudo rasterizar la capa LULC vectorial.")
    if temp_vector_path and os.path.exists(temp_vector_path):
        try:
            os.remove(temp_vector_path)
        except OSError:
            pass
    if not os.path.exists(output_path):
        raise ValueError(f"No fue posible generar el raster LULC esperado: {output_path}")
    return load_raster(output_path, os.path.splitext(os.path.basename(output_path))[0])


def _calculator_entries(named_layers):
    entries = []
    for ref_name, layer in named_layers.items():
        entry = QgsRasterCalculatorEntry()
        entry.ref = f"{ref_name}@1"
        entry.raster = load_raster(layer, ref_name)
        entry.bandNumber = 1
        entries.append(entry)
    return entries


def calculate_raster(expression, named_layers, reference_layer, output_path):
    reference = load_raster(reference_layer, "reference")
    entries = _calculator_entries(named_layers)
    calculator = QgsRasterCalculator(
        expression,
        output_path,
        "GTiff",
        reference.extent(),
        reference.width(),
        reference.height(),
        entries,
        QgsProject.instance().transformContext(),
    )
    result_code = calculator.processCalculation()
    if result_code != 0:
        raise RuntimeError(f"Fallo el calculo raster con codigo {result_code}: {expression}")
    return load_raster(output_path, os.path.splitext(os.path.basename(output_path))[0])


def raster_percentile_breaks(raster_layer, percentiles):
    try:
        from osgeo import gdal
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("No fue posible importar GDAL/numpy para calcular percentiles del raster GHI.") from exc

    raster = load_raster(raster_layer, "percentile_source")
    dataset = gdal.Open(raster.source())
    if dataset is None:
        raise RuntimeError("No fue posible abrir el raster para calcular percentiles de GHI.")
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray().astype(float)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        array[array == nodata] = np.nan
    valid = array[np.isfinite(array)]
    dataset = None
    if valid.size == 0:
        raise RuntimeError("El raster GHI no contiene valores validos para calcular percentiles.")
    return [float(np.percentile(valid, percentile)) for percentile in percentiles]


def _aspect_sector_expression(code, reference_name):
    if code == "N":
        return f"(({reference_name}@1 >= 337.5 OR {reference_name}@1 < 22.5))"
    if code == "NW":
        return f"(({reference_name}@1 >= 292.5 AND {reference_name}@1 < 337.5))"
    if code == "NE":
        return f"(({reference_name}@1 >= 22.5 AND {reference_name}@1 < 67.5))"
    if code == "E":
        return f"(({reference_name}@1 >= 67.5 AND {reference_name}@1 < 112.5))"
    if code == "SE":
        return f"(({reference_name}@1 >= 112.5 AND {reference_name}@1 < 157.5))"
    if code == "S":
        return f"(({reference_name}@1 >= 157.5 AND {reference_name}@1 < 202.5))"
    if code == "SW":
        return f"(({reference_name}@1 >= 202.5 AND {reference_name}@1 < 247.5))"
    if code == "W":
        return f"(({reference_name}@1 >= 247.5 AND {reference_name}@1 < 292.5))"
    raise ValueError(f"Orientacion no soportada: {code}")


def aspect_reclass_expression(score_table, reference_name="aspect"):
    """Construir la expresion de reclasificacion de orientacion a partir de una
    tabla {direccion: puntuacion}. Las direcciones no presentes quedan en 0
    (y normalmente las excluye la mascara de orientacion)."""
    terms = []
    for code, score in score_table.items():
        sector = _aspect_sector_expression(code, reference_name)
        terms.append(f"({sector} * {int(score)})")
    return " + ".join(terms) if terms else "0"


def slope_reclass_expression(breaks, reference_name="slope"):
    low, medium, high = breaks
    return (
        f"(({reference_name}@1 >= 0 AND {reference_name}@1 < {low}) * 5) + "
        f"(({reference_name}@1 >= {low} AND {reference_name}@1 < {medium}) * 4) + "
        f"(({reference_name}@1 >= {medium} AND {reference_name}@1 <= {high}) * 3)"
    )


def ghi_reclass_expression(breaks, reference_name="ghi"):
    low, medium, high = breaks
    return (
        f"(({reference_name}@1 > {high}) * 5) + "
        f"(({reference_name}@1 > {medium} AND {reference_name}@1 <= {high}) * 4) + "
        f"(({reference_name}@1 >= {low} AND {reference_name}@1 <= {medium}) * 3) + "
        f"(({reference_name}@1 < {low}) * 1)"
    )


def slope_mask_expression(threshold, reference_name="slope"):
    return f"({reference_name}@1 <= {threshold})"


def aspect_mask_expression(excluded_aspects, reference_name="aspect"):
    sectors = [_aspect_sector_expression(code, reference_name) for code in excluded_aspects]
    if not sectors:
        return "1"
    return f"(({' OR '.join(sectors)}) = 0)"


def lulc_mask_expression(excluded_values, reference_name="lulc"):
    if not excluded_values:
        return "1"
    conditions = [f"({reference_name}@1 = {value})" for value in excluded_values]
    return f"(({' OR '.join(conditions)}) = 0)"


def weighted_overlay_expression(weights):
    return (
        f"(({weights['GHI']:.12f} * ghi_reclass@1) + "
        f"({weights['Pendiente']:.12f} * slope_reclass@1) + "
        f"({weights['Orientacion']:.12f} * aspect_reclass@1))"
    )
