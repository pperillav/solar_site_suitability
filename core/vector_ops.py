import os

import processing
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsDistanceArea,
    QgsField,
    QgsProject,
    QgsVectorLayer,
    edit,
)
from qgis.PyQt.QtCore import QVariant


def polygonize_raster(input_raster, output_path):
    result = processing.run(
        "gdal:polygonize",
        {
            "INPUT": input_raster,
            "BAND": 1,
            "FIELD": "value",
            "EIGHT_CONNECTEDNESS": False,
            "EXTRA": "",
            "OUTPUT": output_path,
        },
    )
    layer = QgsVectorLayer(result["OUTPUT"], os.path.splitext(os.path.basename(output_path))[0], "ogr")
    if not layer.isValid():
        raise ValueError(f"No fue posible cargar el poligono generado: {output_path}")
    return layer


def add_area_fields(layer, crs_authid):
    measure = QgsDistanceArea()
    measure.setSourceCrs(QgsCoordinateReferenceSystem(crs_authid), QgsProject.instance().transformContext())
    measure.setEllipsoid(QgsProject.instance().ellipsoid())

    provider = layer.dataProvider()
    field_names = [field.name() for field in provider.fields()]
    new_fields = []
    if "area_m2" not in field_names:
        new_fields.append(QgsField("area_m2", QVariant.Double))
    if "area_ha" not in field_names:
        new_fields.append(QgsField("area_ha", QVariant.Double))
    if new_fields:
        provider.addAttributes(new_fields)
        layer.updateFields()

    area_m2_idx = layer.fields().indexOf("area_m2")
    area_ha_idx = layer.fields().indexOf("area_ha")
    value_idx = layer.fields().indexOf("value")

    ids_to_delete = []
    with edit(layer):
        for feature in layer.getFeatures():
            value = feature[value_idx] if value_idx >= 0 else 0
            area_m2 = measure.measureArea(feature.geometry())
            layer.changeAttributeValue(feature.id(), area_m2_idx, float(area_m2))
            layer.changeAttributeValue(feature.id(), area_ha_idx, float(area_m2 / 10000.0))
            if value != 1:
                ids_to_delete.append(feature.id())
        if ids_to_delete:
            layer.deleteFeatures(ids_to_delete)
    return layer


def save_filtered_by_area(input_layer, output_path, min_area_ha):
    expression = f'"area_ha" >= {float(min_area_ha)}'
    result = processing.run(
        "native:extractbyexpression",
        {"INPUT": input_layer, "EXPRESSION": expression, "OUTPUT": output_path},
    )
    layer = QgsVectorLayer(result["OUTPUT"], os.path.splitext(os.path.basename(output_path))[0], "ogr")
    if not layer.isValid():
        raise ValueError(f"No fue posible cargar la salida filtrada: {output_path}")
    return layer


def collect_polygon_stats(layer):
    count = 0
    area_ha_total = 0.0
    area_ha_max = 0.0
    area_ha_min = None
    for feature in layer.getFeatures():
        count += 1
        area_ha = float(feature["area_ha"])
        area_ha_total += area_ha
        area_ha_max = max(area_ha_max, area_ha)
        area_ha_min = area_ha if area_ha_min is None else min(area_ha_min, area_ha)
    return {
        "polygon_count": count,
        "area_ha_total": area_ha_total,
        "area_ha_max": area_ha_max,
        "area_ha_min": area_ha_min or 0.0,
    }
