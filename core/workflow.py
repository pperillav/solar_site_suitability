import os

from qgis.core import QgsMapLayer, QgsProject

from ..ahp.calculations import calculate_ahp
from ..core.raster_ops import (
    aspect_mask_expression,
    aspect_reclass_expression,
    calculate_raster,
    ghi_reclass_expression,
    lulc_mask_expression,
    raster_percentile_breaks,
    rasterize_vector_to_reference,
    run_gdal_derivative,
    slope_mask_expression,
    slope_reclass_expression,
    warp_to_reference,
    weighted_overlay_expression,
)
from ..core.era5 import (
    ERA5_DATASET_LABEL,
    ERA5_VARIABLE_LABEL,
    area_summary,
    build_era5_request_plan,
    cleanup_files,
    download_era5_plan,
    process_era5_ssrd,
    write_era5_request,
)
from ..core.vector_ops import add_area_fields, collect_polygon_stats, polygonize_raster, save_filtered_by_area
from ..models.result_bundle import ResultBundle
from ..reporting.summary import write_summary_csv, write_summary_report
from ..validation.inputs import validate_config


def _output_path(config, name, extension):
    return os.path.join(config.output_folder, f"{name}.{extension}")


def _project_layer(layer_id):
    return QgsProject.instance().mapLayer(layer_id)


def _run_stage(log_lines, label, func):
    try:
        result = func()
        log_lines.append(f"OK: {label}.")
        return result
    except Exception as exc:
        raise RuntimeError(f"Fallo en '{label}': {exc}") from exc


def run_analysis(config):
    errors = validate_config(config)
    if errors:
        return ResultBundle(success=False, message="Validacion fallida.", validation_errors=errors)

    ahp_result = calculate_ahp(config.ahp_matrix, labels=["GHI", "Pendiente", "Orientacion"])
    log_lines = ["Validacion completada.", f"CR AHP={ahp_result['cr']:.4f}."]

    dem_layer = _project_layer(config.dem_layer_id)
    ghi_layer = _project_layer(config.ghi_layer_id)
    lulc_layer = _project_layer(config.lulc_layer_id)
    slope_breaks = config.slope_break_values()
    aspect_scores = config.aspect_score_table_values()

    output_paths = {}
    era5_outputs = None
    cleanup_after_run = []

    if config.uses_era5_source():
        request_payload = _run_stage(
            log_lines, "preparacion de solicitud ERA5 SSRD",
            lambda: build_era5_request_plan(config, dem_layer),
        )
        request_path = _run_stage(
            log_lines, "guardado de solicitud ERA5",
            lambda: write_era5_request(_output_path(config, "00_era5_request", "json"), request_payload),
        )
        area = area_summary(request_payload["area"])
        log_lines.append(
            "Fuente solar: "
            f"{ERA5_VARIABLE_LABEL} desde {ERA5_DATASET_LABEL}. "
            f"Variable interna={config.era5_variable}."
        )
        log_lines.append(
            "Area ERA5 [N, W, S, E]: "
            f"[{area['north']:.5f}, {area['west']:.5f}, {area['south']:.5f}, {area['east']:.5f}]"
        )
        log_lines.append(
            f"Periodo ERA5: {config.analysis_start_date} a {config.analysis_end_date}; "
            f"horas={len(request_payload['hours'])}; salida={config.output_temporal_resolution}."
        )
        output_paths["era5_request"] = request_path
        era5_downloads = _run_stage(
            log_lines, "descarga ERA5 SSRD",
            lambda: download_era5_plan(request_payload, config.output_folder),
        )
        era5_outputs = _run_stage(
            log_lines, "procesamiento ERA5 SSRD a GHI",
            lambda: process_era5_ssrd(era5_downloads, config, config.output_folder),
        )
        if era5_outputs["series_csv_path"]:
            output_paths["era5_series_csv"] = era5_outputs["series_csv_path"]
        if era5_outputs["product_raster_path"]:
            output_paths["era5_product_wgs84"] = era5_outputs["product_raster_path"]
        if era5_outputs["suitability_raster_path"]:
            output_paths["era5_suitability_wgs84"] = era5_outputs["suitability_raster_path"]
        if not config.save_era5_netcdf:
            cleanup_after_run.extend(item["path"] for item in era5_downloads)
        if not config.save_era5_geotiff:
            cleanup_after_run.append(era5_outputs["suitability_raster_internal_path"])
        if not config.save_era5_geotiff and era5_outputs["product_raster_internal_path"]:
            cleanup_after_run.append(era5_outputs["product_raster_internal_path"])
        if config.save_era5_netcdf:
            log_lines.append("Salida ERA5: se conservaran los NetCDF descargados.")
        else:
            log_lines.append("Salida ERA5: los NetCDF descargados se eliminaran al finalizar.")
        if config.save_era5_geotiff:
            log_lines.append("Salida ERA5: se conservaran los GeoTIFF procesados en WGS84.")
        else:
            log_lines.append("Salida ERA5: no se conservaran los GeoTIFF procesados en WGS84.")
        if config.save_era5_csv:
            log_lines.append("Salida ERA5: se conservara el CSV de serie temporal.")
        else:
            log_lines.append("Salida ERA5: no se generara el CSV de serie temporal.")
        if config.save_era5_clipped_raster:
            log_lines.append("Salida ERA5: se conservara el raster recortado/alineado al DEM.")
        else:
            log_lines.append("Salida ERA5: no se conservara el raster recortado/alineado al DEM.")
        log_lines.append(
            f"GHI aptitud ERA5: media={era5_outputs['stats']['suitability_mean']:.4f} "
            f"{era5_outputs['suitability_units']}."
        )

    aligned_dem = _run_stage(
        log_lines, "alineacion DEM",
        lambda: warp_to_reference(
            dem_layer, _output_path(config, "01_dem_aligned", "tif"),
            config.target_crs_authid, config.target_resolution, None),
    )
    output_paths["dem_aligned"] = aligned_dem.source()

    if config.uses_era5_source():
        ghi_source_layer = era5_outputs["suitability_raster_internal_path"]
    else:
        ghi_source_layer = ghi_layer

    if config.uses_era5_source():
        percentiles = config.era5_ghi_percentile_values()
        ghi_breaks = _run_stage(
            log_lines,
            "calculo automatico de cortes GHI por percentiles",
            lambda: raster_percentile_breaks(era5_outputs["suitability_raster_internal_path"], percentiles),
        )
        log_lines.append(
            "Cortes GHI ERA5 calculados desde percentiles "
            f"{percentiles[0]:.0f}, {percentiles[1]:.0f}, {percentiles[2]:.0f}: "
            f"{ghi_breaks[0]:.3f}, {ghi_breaks[1]:.3f}, {ghi_breaks[2]:.3f} kWh/m2/dia."
        )
    else:
        ghi_breaks = config.ghi_break_values()

    aligned_ghi = _run_stage(
        log_lines, "alineacion GHI",
        lambda: warp_to_reference(
            ghi_source_layer, _output_path(config, "02_ghi_aligned", "tif"),
            config.target_crs_authid, config.target_resolution, aligned_dem.extent()),
    )
    output_paths["ghi_aligned"] = aligned_ghi.source()

    if config.uses_era5_source() and config.save_era5_clipped_raster:
        clipped_product = _run_stage(
            log_lines, "recorte de producto ERA5 al DEM",
            lambda: warp_to_reference(
                era5_outputs["product_raster_internal_path"],
                _output_path(config, "02b_era5_product_clipped", "tif"),
                config.target_crs_authid,
                config.target_resolution,
                aligned_dem.extent(),
            ),
        )
        output_paths["era5_product_clipped"] = clipped_product.source()

    if lulc_layer.type() == QgsMapLayer.RasterLayer:
        aligned_lulc = _run_stage(
            log_lines, "alineacion LULC",
            lambda: warp_to_reference(
                lulc_layer, _output_path(config, "03_lulc_aligned", "tif"),
                config.target_crs_authid, config.target_resolution, aligned_dem.extent()),
        )
    else:
        aligned_lulc = _run_stage(
            log_lines, "rasterizacion LULC vectorial",
            lambda: rasterize_vector_to_reference(
                lulc_layer,
                config.lulc_field_name,
                aligned_dem,
                _output_path(config, "03_lulc_aligned", "tif"),
            ),
        )
        log_lines.append(f"Campo LULC usado para rasterizacion: {config.lulc_field_name}.")
    output_paths["lulc_aligned"] = aligned_lulc.source()

    slope_layer = _run_stage(
        log_lines, "calculo de pendiente",
        lambda: run_gdal_derivative("gdal:slope", aligned_dem, _output_path(config, "04_slope", "tif")),
    )
    aspect_layer = _run_stage(
        log_lines, "calculo de orientacion",
        lambda: run_gdal_derivative("gdal:aspect", aligned_dem, _output_path(config, "05_aspect", "tif")),
    )
    output_paths["slope"] = slope_layer.source()
    output_paths["aspect"] = aspect_layer.source()

    ghi_reclass = _run_stage(
        log_lines, "reclasificacion GHI",
        lambda: calculate_raster(
            ghi_reclass_expression(ghi_breaks), {"ghi": aligned_ghi},
            aligned_dem, _output_path(config, "06_ghi_reclass", "tif")),
    )
    slope_reclass = _run_stage(
        log_lines, "reclasificacion pendiente",
        lambda: calculate_raster(
            slope_reclass_expression(slope_breaks), {"slope": slope_layer},
            aligned_dem, _output_path(config, "07_slope_reclass", "tif")),
    )
    aspect_reclass = _run_stage(
        log_lines, "reclasificacion orientacion",
        lambda: calculate_raster(
            aspect_reclass_expression(aspect_scores), {"aspect": aspect_layer},
            aligned_dem, _output_path(config, "08_aspect_reclass", "tif")),
    )
    output_paths["ghi_reclass"] = ghi_reclass.source()
    output_paths["slope_reclass"] = slope_reclass.source()
    output_paths["aspect_reclass"] = aspect_reclass.source()

    slope_mask = _run_stage(
        log_lines, "mascara de pendiente",
        lambda: calculate_raster(
            slope_mask_expression(config.slope_threshold_deg), {"slope": slope_layer},
            aligned_dem, _output_path(config, "09_slope_mask", "tif")),
    )
    aspect_mask = _run_stage(
        log_lines, "mascara de orientacion",
        lambda: calculate_raster(
            aspect_mask_expression(config.excluded_aspects), {"aspect": aspect_layer},
            aligned_dem, _output_path(config, "10_aspect_mask", "tif")),
    )
    lulc_mask = _run_stage(
        log_lines, "mascara LULC",
        lambda: calculate_raster(
            lulc_mask_expression(config.excluded_lulc_class_values()), {"lulc": aligned_lulc},
            aligned_dem, _output_path(config, "11_lulc_mask", "tif")),
    )
    output_paths["slope_mask"] = slope_mask.source()
    output_paths["aspect_mask"] = aspect_mask.source()
    output_paths["lulc_mask"] = lulc_mask.source()

    combined_mask = _run_stage(
        log_lines, "combinacion de mascaras",
        lambda: calculate_raster(
            "slope_mask@1 * aspect_mask@1 * lulc_mask@1",
            {"slope_mask": slope_mask, "aspect_mask": aspect_mask, "lulc_mask": lulc_mask},
            aligned_dem, _output_path(config, "12_combined_mask", "tif")),
    )
    output_paths["combined_mask"] = combined_mask.source()

    suitability_raw = _run_stage(
        log_lines, "overlay ponderado bruto",
        lambda: calculate_raster(
            weighted_overlay_expression(ahp_result["named_weights"]),
            {"ghi_reclass": ghi_reclass, "slope_reclass": slope_reclass, "aspect_reclass": aspect_reclass},
            aligned_dem, _output_path(config, "13_suitability_raw", "tif")),
    )
    suitability_final = _run_stage(
        log_lines, "aplicacion de mascara final",
        lambda: calculate_raster(
            "suitability_raw@1 * combined_mask@1",
            {"suitability_raw": suitability_raw, "combined_mask": combined_mask},
            aligned_dem, _output_path(config, "14_suitability_final", "tif")),
    )
    output_paths["suitability_raw"] = suitability_raw.source()
    output_paths["suitability_final"] = suitability_final.source()

    optimal_raster = _run_stage(
        log_lines, "umbralizacion de aptitud",
        lambda: calculate_raster(
            f"(suitability_final@1 >= {config.suitability_threshold})",
            {"suitability_final": suitability_final},
            aligned_dem, _output_path(config, "15_optimal_binary", "tif")),
    )
    output_paths["optimal_binary"] = optimal_raster.source()

    polygons = _run_stage(
        log_lines, "polygonizacion",
        lambda: polygonize_raster(optimal_raster, _output_path(config, "16_optimal_polygons", "gpkg")),
    )
    polygons = _run_stage(
        log_lines, "calculo de areas",
        lambda: add_area_fields(polygons, config.target_crs_authid),
    )
    filtered = _run_stage(
        log_lines, "filtro por area minima",
        lambda: save_filtered_by_area(polygons, _output_path(config, "17_viable_sites", "gpkg"), config.min_area_ha),
    )
    output_paths["optimal_polygons"] = polygons.source()
    output_paths["viable_sites"] = filtered.source()

    stats = collect_polygon_stats(filtered)
    report_path = _run_stage(
        log_lines, "reporte HTML",
        lambda: write_summary_report(
            _output_path(config, "18_report", "html"), config, ahp_result, stats, output_paths),
    )
    output_paths["report"] = report_path

    csv_path = _run_stage(
        log_lines, "reporte CSV",
        lambda: write_summary_csv(
            _output_path(config, "19_report_summary", "csv"), config, ahp_result, stats, output_paths),
    )
    output_paths["report_csv"] = csv_path

    message = (
        f"Analisis completado. {stats['polygon_count']} poligonos viables, "
        f"{stats['area_ha_total']:.2f} ha acumuladas. CR={ahp_result['cr']:.4f}."
    )
    cleanup_files(cleanup_after_run)
    return ResultBundle(
        success=True, message=message, validation_errors=[], log_lines=log_lines,
        output_paths=output_paths, stats=stats, ahp_result=ahp_result,
    )
